import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
from collections import defaultdict

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI

logger = logging.getLogger(__name__)

class TransactionAnalysis:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.transaction_history_file = self.data_dir / "transaction_history.json"
        self.suspicious_patterns_file = self.data_dir / "suspicious_patterns.json"
        
        self._load_data()
        
    def _load_data(self):
        """Load data from files"""
        try:
            if self.transaction_history_file.exists():
                with open(self.transaction_history_file, 'r') as f:
                    self.transaction_history = json.load(f)
            else:
                self.transaction_history = {}
                self._save_history()

            if self.suspicious_patterns_file.exists():
                with open(self.suspicious_patterns_file, 'r') as f:
                    self.suspicious_patterns = json.load(f)
            else:
                self.suspicious_patterns = {"patterns": [], "detected": {}}
                self._save_patterns()
                
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.transaction_history = {}
            self.suspicious_patterns = {"patterns": [], "detected": {}}

    def _save_history(self):
        with open(self.transaction_history_file, 'w') as f:
            json.dump(self.transaction_history, f, indent=2)

    def _save_patterns(self):
        with open(self.suspicious_patterns_file, 'w') as f:
            json.dump(self.suspicious_patterns, f, indent=2)

    async def initialize(self):
        """Initialize API connections"""
        await self.helius.initialize()
        await self.jupiter.initialize()
        
    async def close(self):
        """Close API connections"""
        await self.helius.close()
        await self.jupiter.close()

    async def analyze_transactions(self, token_address: str, timeframe: str = "1h") -> Dict:
        """Analyze token transactions"""
        try:
            # Get transactions
            transactions = await self.helius.get_token_transactions(token_address)
            if not transactions:
                return {
                    "transaction_count": 0,
                    "buy_sell_ratio": float('inf'),
                    "avg_transaction_size": 0.0,
                    "volume_24h": 0.0,
                    "largest_transaction": 0.0,
                    "unique_wallets": 0,
                    "suspicious_patterns": []
                }

            # Calculate metrics
            buy_volume = 0
            sell_volume = 0
            total_volume = 0
            transaction_sizes = []
            unique_wallets = set()

            for tx in transactions:
                amount = float(tx.get("amount", 0))
                total_volume += amount
                transaction_sizes.append(amount)
                
                if "from_address" in tx:
                    unique_wallets.add(tx["from_address"])
                if "to_address" in tx:
                    unique_wallets.add(tx["to_address"])
                    
                if tx.get("is_buy", False):
                    buy_volume += amount
                else:
                    sell_volume += amount

            # Calculate metrics
            transaction_count = len(transactions)
            avg_transaction_size = sum(transaction_sizes) / max(len(transaction_sizes), 1)
            buy_sell_ratio = buy_volume / max(sell_volume, 1e-10)  # Avoid division by zero
            
            return {
                "transaction_count": transaction_count,
                "buy_sell_ratio": buy_sell_ratio,
                "avg_transaction_size": avg_transaction_size,
                "volume_24h": total_volume,
                "largest_transaction": max(transaction_sizes) if transaction_sizes else 0,
                "unique_wallets": len(unique_wallets),
                "suspicious_patterns": await self._detect_suspicious_patterns(transactions)
            }

        except Exception as e:
            logger.error(f"Error analyzing transactions for {token_address}: {str(e)}")
            raise

    async def _detect_suspicious_patterns(self, transactions: List[Dict]) -> List[Dict]:
        """Detect suspicious transaction patterns"""
        try:
            suspicious = []
            
            # Pattern 1: Wash trading
            wash_trades = self._detect_wash_trades(transactions)
            if wash_trades:
                suspicious.append({
                    "pattern": "Wash Trading",
                    "confidence": wash_trades["confidence"],
                    "details": wash_trades["details"]
                })

            # Pattern 2: Price manipulation
            manipulation = self._detect_price_manipulation(transactions)
            if manipulation:
                suspicious.append({
                    "pattern": "Price Manipulation",
                    "confidence": manipulation["confidence"],
                    "details": manipulation["details"]
                })

            # Pattern 3: Coordinated buying/selling
            coordinated = self._detect_coordinated_trading(transactions)
            if coordinated:
                suspicious.append({
                    "pattern": "Coordinated Trading",
                    "confidence": coordinated["confidence"],
                    "details": coordinated["details"]
                })

            return suspicious

        except Exception as e:
            logger.error(f"Error detecting suspicious patterns: {str(e)}")
            return []

    def _detect_wash_trades(self, transactions: List[Dict]) -> Optional[Dict]:
        """Detect wash trading patterns"""
        try:
            # Group transactions by wallet pairs
            pairs = defaultdict(list)
            for i in range(len(transactions) - 1):
                tx1, tx2 = transactions[i], transactions[i + 1]
                if (tx1.get("from") and tx1.get("to") and
                    tx2.get("from") and tx2.get("to")):
                    pair = tuple(sorted([tx1["from"], tx1["to"]]))
                    pairs[pair].append((tx1, tx2))

            # Analyze patterns
            wash_trades = []
            for pair, txs in pairs.items():
                if len(txs) >= 3:  # Multiple back-and-forth trades
                    amounts = [abs(float(tx[0].get("amount", 0)) - 
                                 float(tx[1].get("amount", 0)))
                             for tx in txs]
                    if all(amt < 0.1 for amt in amounts):  # Similar amounts
                        wash_trades.append({
                            "wallets": list(pair),
                            "trade_count": len(txs),
                            "average_amount": sum(amounts) / len(amounts)
                        })

            if wash_trades:
                return {
                    "confidence": min(1.0, len(wash_trades) * 0.2),
                    "details": wash_trades
                }
            return None

        except Exception as e:
            logger.error(f"Error detecting wash trades: {str(e)}")
            return None

    def _detect_price_manipulation(self, transactions: List[Dict]) -> Optional[Dict]:
        """Detect price manipulation patterns"""
        try:
            manipulations = []
            
            # Look for sudden price movements
            for i in range(len(transactions) - 1):
                tx1, tx2 = transactions[i], transactions[i + 1]
                price1 = float(tx1.get("price", 0))
                price2 = float(tx2.get("price", 0))
                
                if price1 > 0 and price2 > 0:
                    price_change = abs(price2 - price1) / price1
                    if price_change > 0.2:  # 20% price change
                        time1 = datetime.fromisoformat(tx1["timestamp"])
                        time2 = datetime.fromisoformat(tx2["timestamp"])
                        if (time2 - time1).total_seconds() < 60:  # Within 1 minute
                            manipulations.append({
                                "price_change": price_change,
                                "time_diff": (time2 - time1).total_seconds(),
                                "tx1": tx1.get("signature"),
                                "tx2": tx2.get("signature")
                            })

            if manipulations:
                return {
                    "confidence": min(1.0, len(manipulations) * 0.3),
                    "details": manipulations
                }
            return None

        except Exception as e:
            logger.error(f"Error detecting price manipulation: {str(e)}")
            return None

    def _detect_coordinated_trading(self, transactions: List[Dict]) -> Optional[Dict]:
        """Detect coordinated trading patterns"""
        try:
            # Group transactions by time windows
            time_windows = defaultdict(list)
            for tx in transactions:
                if tx.get("timestamp"):
                    minute = datetime.fromisoformat(tx["timestamp"]).strftime("%Y-%m-%d %H:%M")
                    time_windows[minute].append(tx)

            coordinated = []
            for minute, txs in time_windows.items():
                if len(txs) >= 3:  # Multiple transactions in same minute
                    wallets = set()
                    volume = 0
                    for tx in txs:
                        if tx.get("from"):
                            wallets.add(tx["from"])
                        if tx.get("to"):
                            wallets.add(tx["to"])
                        volume += float(tx.get("amount", 0))

                    if len(wallets) >= 3:  # Multiple wallets involved
                        coordinated.append({
                            "timestamp": minute,
                            "wallet_count": len(wallets),
                            "transaction_count": len(txs),
                            "volume": volume
                        })

            if coordinated:
                return {
                    "confidence": min(1.0, len(coordinated) * 0.25),
                    "details": coordinated
                }
            return None

        except Exception as e:
            logger.error(f"Error detecting coordinated trading: {str(e)}")
            return None

    async def _monitor_liquidity(self, token_address: str) -> Dict:
        """Monitor token liquidity"""
        try:
            # Get liquidity data from Jupiter
            liquidity = await self.jupiter.get_token_liquidity(token_address)
            
            # Get historical liquidity from transaction history
            history = self.transaction_history.get(token_address, {})
            historical_liquidity = []
            
            for timestamp, txs in history.items():
                total_volume = sum(float(tx.get("amount", 0)) for tx in txs)
                historical_liquidity.append({
                    "timestamp": timestamp,
                    "volume": total_volume
                })

            return {
                "current_liquidity": liquidity.get("liquidity", 0),
                "liquidity_score": self._calculate_liquidity_score(liquidity),
                "historical_liquidity": historical_liquidity[-24:],  # Last 24 data points
                "risk_level": self._assess_liquidity_risk(liquidity)
            }

        except Exception as e:
            logger.error(f"Error monitoring liquidity: {str(e)}")
            return {}

    def _calculate_liquidity_score(self, liquidity: Dict) -> float:
        """Calculate liquidity score"""
        try:
            score = 0.0
            
            # Factor 1: Total liquidity
            total_liquidity = float(liquidity.get("liquidity", 0))
            if total_liquidity > 1_000_000:  # $1M+
                score += 0.4
            elif total_liquidity > 100_000:  # $100k+
                score += 0.2
                
            # Factor 2: Liquidity depth
            depth = float(liquidity.get("depth", 0))
            if depth > 0.8:
                score += 0.3
            elif depth > 0.5:
                score += 0.2
                
            # Factor 3: Stability
            stability = float(liquidity.get("stability", 0))
            if stability > 0.9:
                score += 0.3
            elif stability > 0.7:
                score += 0.2
                
            return min(1.0, score)

        except Exception as e:
            logger.error(f"Error calculating liquidity score: {str(e)}")
            return 0.0

    def _assess_liquidity_risk(self, liquidity: Dict) -> str:
        """Assess liquidity risk level"""
        try:
            score = self._calculate_liquidity_score(liquidity)
            
            if score >= 0.7:
                return "Low"
            elif score >= 0.4:
                return "Medium"
            else:
                return "High"

        except Exception as e:
            logger.error(f"Error assessing liquidity risk: {str(e)}")
            return "Unknown"

    async def _analyze_price_impact(self, token_address: str) -> Dict:
        """Analyze price impact of trades"""
        try:
            # Get recent trades
            trades = await self.helius.get_token_transactions(token_address)
            if not trades:
                return {}

            impacts = []
            for trade in trades:
                amount = float(trade.get("amount", 0))
                price_before = float(trade.get("price_before", 0))
                price_after = float(trade.get("price_after", 0))
                
                if price_before > 0:
                    impact = abs(price_after - price_before) / price_before
                    impacts.append({
                        "amount": amount,
                        "impact": impact,
                        "timestamp": trade.get("timestamp")
                    })

            if not impacts:
                return {}

            # Calculate average impact per size bracket
            size_brackets = {
                "small": [],   # < $1000
                "medium": [],  # $1000-$10000
                "large": []    # > $10000
            }

            for impact in impacts:
                if impact["amount"] < 1000:
                    size_brackets["small"].append(impact["impact"])
                elif impact["amount"] < 10000:
                    size_brackets["medium"].append(impact["impact"])
                else:
                    size_brackets["large"].append(impact["impact"])

            avg_impacts = {}
            for size, impacts in size_brackets.items():
                if impacts:
                    avg_impacts[size] = sum(impacts) / len(impacts)
                else:
                    avg_impacts[size] = 0

            return {
                "average_impact": avg_impacts,
                "max_impact": max(i["impact"] for i in impacts),
                "impact_by_size": size_brackets,
                "risk_level": self._assess_impact_risk(avg_impacts)
            }

        except Exception as e:
            logger.error(f"Error analyzing price impact: {str(e)}")
            return {}

    def _assess_impact_risk(self, avg_impacts: Dict) -> str:
        """Assess price impact risk level"""
        try:
            # Weight the impacts by size
            weighted_impact = (
                avg_impacts.get("small", 0) * 0.2 +
                avg_impacts.get("medium", 0) * 0.3 +
                avg_impacts.get("large", 0) * 0.5
            )
            
            if weighted_impact < 0.02:  # Less than 2% impact
                return "Low"
            elif weighted_impact < 0.05:  # Less than 5% impact
                return "Medium"
            else:
                return "High"

        except Exception as e:
            logger.error(f"Error assessing impact risk: {str(e)}")
            return "Unknown"

    def _create_empty_analysis(self, token_address: str) -> Dict:
        """Create empty analysis result"""
        return {
            "token_address": token_address,
            "timeframe": "1h",
            "buy_sell_ratio": {},
            "volume_analysis": {},
            "suspicious_patterns": [],
            "liquidity": {},
            "price_impact": {},
            "timestamp": datetime.now().isoformat()
        }
