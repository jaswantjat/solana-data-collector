import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import json
from pathlib import Path
import asyncio
from collections import defaultdict

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI

logger = logging.getLogger(__name__)

class HolderAnalysis:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.known_snipers_file = self.data_dir / "known_snipers.json"
        self.insider_patterns_file = self.data_dir / "insider_patterns.json"
        self.holder_history_file = self.data_dir / "holder_history.json"
        
        self._load_data()
        
    def _load_data(self):
        """Load data from files"""
        try:
            if self.known_snipers_file.exists():
                with open(self.known_snipers_file, 'r') as f:
                    self.known_snipers = json.load(f)
            else:
                self.known_snipers = {"wallets": [], "patterns": []}
                self._save_snipers()

            if self.insider_patterns_file.exists():
                with open(self.insider_patterns_file, 'r') as f:
                    self.insider_patterns = json.load(f)
            else:
                self.insider_patterns = {"patterns": [], "suspicious_wallets": []}
                self._save_patterns()

            if self.holder_history_file.exists():
                with open(self.holder_history_file, 'r') as f:
                    self.holder_history = json.load(f)
            else:
                self.holder_history = {}
                self._save_history()
                
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.known_snipers = {"wallets": [], "patterns": []}
            self.insider_patterns = {"patterns": [], "suspicious_wallets": []}
            self.holder_history = {}

    def _save_snipers(self):
        with open(self.known_snipers_file, 'w') as f:
            json.dump(self.known_snipers, f, indent=2)

    def _save_patterns(self):
        with open(self.insider_patterns_file, 'w') as f:
            json.dump(self.insider_patterns, f, indent=2)

    def _save_history(self):
        with open(self.holder_history_file, 'w') as f:
            json.dump(self.holder_history, f, indent=2)

    async def analyze_holders(self, token_address: str) -> Dict:
        """Analyze token holders and their behavior"""
        try:
            # Get current holders
            holders = await self.helius.get_token_holders(token_address)
            if not holders:
                return self._create_empty_analysis(token_address)

            # Get historical holder data
            history = self.holder_history.get(token_address, {})
            
            # Update holder history
            current_time = datetime.now().isoformat()
            if token_address not in self.holder_history:
                self.holder_history[token_address] = {}
            self.holder_history[token_address][current_time] = holders
            self._save_history()

            # Analyze holder concentration
            concentration = await self._analyze_concentration(holders)
            
            # Detect snipers
            snipers = await self._detect_snipers(token_address, holders)
            
            # Monitor developer wallets
            dev_movements = await self._monitor_developer_wallets(token_address, holders)
            
            # Detect insider trading
            insider_trading = await self._detect_insider_trading(token_address, holders)
            
            # Calculate supply distribution
            distribution = await self._calculate_supply_distribution(holders)
            
            return {
                "token_address": token_address,
                "total_holders": len(holders),
                "concentration": concentration,
                "snipers": snipers,
                "developer_movements": dev_movements,
                "insider_trading": insider_trading,
                "supply_distribution": distribution,
                "timestamp": current_time
            }

        except Exception as e:
            logger.error(f"Error analyzing holders for {token_address}: {str(e)}")
            return self._create_empty_analysis(token_address)

    async def _analyze_concentration(self, holders: Dict) -> Dict:
        """Analyze holder concentration metrics"""
        try:
            total_supply = sum(float(amount) for amount in holders.values())
            if total_supply == 0:
                return {"risk_level": "High", "gini_coefficient": 1.0}

            # Sort holders by amount
            sorted_holders = sorted(
                [(addr, float(amt)) for addr, amt in holders.items()],
                key=lambda x: x[1], reverse=True
            )

            # Calculate top holder percentages
            top_10_percent = sum(amt for _, amt in sorted_holders[:len(sorted_holders)//10]) / total_supply
            top_20_percent = sum(amt for _, amt in sorted_holders[:len(sorted_holders)//5]) / total_supply
            
            # Calculate Gini coefficient
            n = len(holders)
            gini = sum((2 * i - n - 1) * amt 
                      for i, (_, amt) in enumerate(sorted_holders)) / (n * total_supply)

            # Determine risk level
            risk_level = "Low"
            if gini > 0.8 or top_10_percent > 0.6:
                risk_level = "High"
            elif gini > 0.6 or top_20_percent > 0.8:
                risk_level = "Medium"

            return {
                "risk_level": risk_level,
                "gini_coefficient": gini,
                "top_10_percent_holdings": top_10_percent,
                "top_20_percent_holdings": top_20_percent
            }

        except Exception as e:
            logger.error(f"Error analyzing concentration: {str(e)}")
            return {"risk_level": "Unknown", "gini_coefficient": 0.0}

    async def _detect_snipers(self, token_address: str, holders: Dict) -> List[Dict]:
        """Detect sniper wallets based on behavior patterns"""
        try:
            snipers = []
            
            # Get transaction history
            transactions = await self.helius.get_token_transactions(token_address)
            if not transactions:
                return []

            # Analyze transaction patterns
            for wallet, amount in holders.items():
                wallet_txs = [tx for tx in transactions if tx.get("from") == wallet or tx.get("to") == wallet]
                
                # Check for sniper patterns
                if self._matches_sniper_pattern(wallet_txs):
                    snipers.append({
                        "wallet": wallet,
                        "amount": amount,
                        "confidence": self._calculate_sniper_confidence(wallet_txs)
                    })
                    
                    # Add to known snipers if high confidence
                    if wallet not in self.known_snipers["wallets"]:
                        self.known_snipers["wallets"].append(wallet)
                        self._save_snipers()

            return snipers

        except Exception as e:
            logger.error(f"Error detecting snipers: {str(e)}")
            return []

    def _matches_sniper_pattern(self, transactions: List[Dict]) -> bool:
        """Check if transactions match known sniper patterns"""
        if not transactions:
            return False
            
        try:
            # Pattern 1: Quick large buys after launch
            first_tx = transactions[0]
            if first_tx.get("timestamp"):
                tx_time = datetime.fromisoformat(first_tx["timestamp"])
                if (datetime.now() - tx_time).total_seconds() < 300:  # Within 5 minutes
                    return True
                    
            # Pattern 2: Multiple quick buys and sells
            buy_sell_pairs = 0
            for i in range(len(transactions) - 1):
                if transactions[i].get("type") == "buy" and transactions[i+1].get("type") == "sell":
                    buy_sell_pairs += 1
            if buy_sell_pairs >= 3:
                return True
                
            return False

        except Exception as e:
            logger.error(f"Error matching sniper pattern: {str(e)}")
            return False

    def _calculate_sniper_confidence(self, transactions: List[Dict]) -> float:
        """Calculate confidence score for sniper detection"""
        try:
            score = 0.0
            
            # Factor 1: Speed of first buy
            first_tx = transactions[0]
            if first_tx.get("timestamp"):
                tx_time = datetime.fromisoformat(first_tx["timestamp"])
                time_diff = (datetime.now() - tx_time).total_seconds()
                if time_diff < 60:  # Within 1 minute
                    score += 0.4
                elif time_diff < 300:  # Within 5 minutes
                    score += 0.2
                    
            # Factor 2: Buy/sell pattern
            buy_sell_pairs = 0
            for i in range(len(transactions) - 1):
                if transactions[i].get("type") == "buy" and transactions[i+1].get("type") == "sell":
                    buy_sell_pairs += 1
            score += min(0.3, buy_sell_pairs * 0.1)
            
            # Factor 3: Transaction sizes
            avg_size = sum(float(tx.get("amount", 0)) for tx in transactions) / len(transactions)
            if avg_size > 1000:  # Large transactions
                score += 0.3
                
            return min(1.0, score)

        except Exception as e:
            logger.error(f"Error calculating sniper confidence: {str(e)}")
            return 0.0

    async def _monitor_developer_wallets(self, token_address: str, holders: Dict) -> List[Dict]:
        """Monitor movements of developer wallets"""
        try:
            dev_wallets = await self.helius.get_token_deployer_wallets(token_address)
            if not dev_wallets:
                return []

            movements = []
            for wallet in dev_wallets:
                transactions = await self.helius.get_wallet_transactions(wallet)
                if not transactions:
                    continue

                # Analyze wallet movements
                total_sold = sum(float(tx.get("amount", 0)) 
                               for tx in transactions 
                               if tx.get("type") == "sell")
                               
                total_transferred = sum(float(tx.get("amount", 0)) 
                                     for tx in transactions 
                                     if tx.get("type") == "transfer")

                movements.append({
                    "wallet": wallet,
                    "current_balance": float(holders.get(wallet, 0)),
                    "total_sold": total_sold,
                    "total_transferred": total_transferred,
                    "risk_level": "High" if total_sold > 0 else "Low"
                })

            return movements

        except Exception as e:
            logger.error(f"Error monitoring developer wallets: {str(e)}")
            return []

    async def _detect_insider_trading(self, token_address: str, holders: Dict) -> List[Dict]:
        """Detect potential insider trading patterns"""
        try:
            suspicious_activities = []
            transactions = await self.helius.get_token_transactions(token_address)
            if not transactions:
                return []

            # Group transactions by wallet
            wallet_txs = defaultdict(list)
            for tx in transactions:
                if tx.get("from"):
                    wallet_txs[tx["from"]].append(tx)
                if tx.get("to"):
                    wallet_txs[tx["to"]].append(tx)

            # Analyze each wallet's behavior
            for wallet, txs in wallet_txs.items():
                if self._matches_insider_pattern(txs):
                    suspicious_activities.append({
                        "wallet": wallet,
                        "pattern": "Suspicious trading pattern",
                        "confidence": self._calculate_insider_confidence(txs),
                        "current_holdings": float(holders.get(wallet, 0))
                    })
                    
                    # Add to suspicious wallets list
                    if wallet not in self.insider_patterns["suspicious_wallets"]:
                        self.insider_patterns["suspicious_wallets"].append(wallet)
                        self._save_patterns()

            return suspicious_activities

        except Exception as e:
            logger.error(f"Error detecting insider trading: {str(e)}")
            return []

    def _matches_insider_pattern(self, transactions: List[Dict]) -> bool:
        """Check if transactions match insider trading patterns"""
        try:
            if not transactions:
                return False

            # Pattern 1: Large buys before price increases
            for i in range(len(transactions) - 1):
                if (transactions[i].get("type") == "buy" and
                    float(transactions[i].get("amount", 0)) > 1000 and
                    float(transactions[i+1].get("price_change", 0)) > 0.2):
                    return True

            # Pattern 2: Coordinated trading with other wallets
            tx_times = [datetime.fromisoformat(tx["timestamp"]) 
                       for tx in transactions 
                       if tx.get("timestamp")]
            if len(tx_times) >= 2:
                time_diffs = [(tx_times[i+1] - tx_times[i]).total_seconds() 
                             for i in range(len(tx_times)-1)]
                if any(diff < 10 for diff in time_diffs):  # Within 10 seconds
                    return True

            return False

        except Exception as e:
            logger.error(f"Error matching insider pattern: {str(e)}")
            return False

    def _calculate_insider_confidence(self, transactions: List[Dict]) -> float:
        """Calculate confidence score for insider trading detection"""
        try:
            score = 0.0
            
            # Factor 1: Trading before price movements
            for i in range(len(transactions) - 1):
                if (transactions[i].get("type") == "buy" and
                    float(transactions[i+1].get("price_change", 0)) > 0.2):
                    score += 0.3
                    
            # Factor 2: Transaction timing
            tx_times = [datetime.fromisoformat(tx["timestamp"]) 
                       for tx in transactions 
                       if tx.get("timestamp")]
            if len(tx_times) >= 2:
                time_diffs = [(tx_times[i+1] - tx_times[i]).total_seconds() 
                             for i in range(len(tx_times)-1)]
                if any(diff < 10 for diff in time_diffs):
                    score += 0.3
                    
            # Factor 3: Transaction sizes
            avg_size = sum(float(tx.get("amount", 0)) for tx in transactions) / len(transactions)
            if avg_size > 1000:
                score += 0.4
                
            return min(1.0, score)

        except Exception as e:
            logger.error(f"Error calculating insider confidence: {str(e)}")
            return 0.0

    async def _calculate_supply_distribution(self, holders: Dict) -> Dict:
        """Calculate and visualize supply distribution"""
        try:
            total_supply = sum(float(amount) for amount in holders.values())
            if total_supply == 0:
                return {}

            # Calculate distribution brackets
            brackets = {
                "0-0.1%": 0,
                "0.1-1%": 0,
                "1-5%": 0,
                "5-10%": 0,
                "10%+": 0
            }

            for amount in holders.values():
                percentage = float(amount) / total_supply * 100
                if percentage <= 0.1:
                    brackets["0-0.1%"] += 1
                elif percentage <= 1:
                    brackets["0.1-1%"] += 1
                elif percentage <= 5:
                    brackets["1-5%"] += 1
                elif percentage <= 10:
                    brackets["5-10%"] += 1
                else:
                    brackets["10%+"] += 1

            return {
                "total_supply": total_supply,
                "distribution": brackets,
                "holder_count": len(holders)
            }

        except Exception as e:
            logger.error(f"Error calculating supply distribution: {str(e)}")
            return {}

    def _create_empty_analysis(self, token_address: str) -> Dict:
        """Create empty analysis result"""
        return {
            "token_address": token_address,
            "total_holders": 0,
            "concentration": {"risk_level": "Unknown", "gini_coefficient": 0.0},
            "snipers": [],
            "developer_movements": [],
            "insider_trading": [],
            "supply_distribution": {},
            "timestamp": datetime.now().isoformat()
        }
