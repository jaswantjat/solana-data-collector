import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
from collections import defaultdict

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI

logger = logging.getLogger(__name__)

class PortfolioAnalysis:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.portfolio_history_file = self.data_dir / "portfolio_history.json"
        self.wallet_patterns_file = self.data_dir / "wallet_patterns.json"
        
        self._load_data()
        
    def _load_data(self):
        """Load data from files"""
        try:
            if self.portfolio_history_file.exists():
                with open(self.portfolio_history_file, 'r') as f:
                    self.portfolio_history = json.load(f)
            else:
                self.portfolio_history = {}
                self._save_history()

            if self.wallet_patterns_file.exists():
                with open(self.wallet_patterns_file, 'r') as f:
                    self.wallet_patterns = json.load(f)
            else:
                self.wallet_patterns = {"patterns": [], "wallets": {}}
                self._save_patterns()
                
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.portfolio_history = {}
            self.wallet_patterns = {"patterns": [], "wallets": {}}

    def _save_history(self):
        with open(self.portfolio_history_file, 'w') as f:
            json.dump(self.portfolio_history, f, indent=2)

    def _save_patterns(self):
        with open(self.wallet_patterns_file, 'w') as f:
            json.dump(self.wallet_patterns, f, indent=2)

    async def analyze_portfolio(self, token_address: str) -> Dict:
        """Analyze token portfolio metrics"""
        try:
            # Get top holders
            holders = await self._track_top_holders(token_address)
            
            # Analyze historical performance
            performance = await self._analyze_performance(token_address)
            
            # Calculate win rate
            win_rate = await self._calculate_win_rate(token_address)
            
            # Track PNL
            pnl = await self._track_pnl(token_address)
            
            # Analyze wallet patterns
            patterns = await self._analyze_wallet_patterns(token_address, holders)
            
            # Update portfolio history
            current_time = datetime.now().isoformat()
            if token_address not in self.portfolio_history:
                self.portfolio_history[token_address] = []
                
            self.portfolio_history[token_address].append({
                "timestamp": current_time,
                "top_holders": len(holders),
                "win_rate": win_rate["14d_rate"],
                "pnl_30d": pnl["30d_pnl"]
            })
            
            self._save_history()
            
            return {
                "token_address": token_address,
                "top_holders": holders,
                "historical_performance": performance,
                "win_rate": win_rate,
                "pnl_tracking": pnl,
                "wallet_patterns": patterns,
                "timestamp": current_time
            }

        except Exception as e:
            logger.error(f"Error analyzing portfolio for {token_address}: {str(e)}")
            return self._create_empty_analysis(token_address)

    async def _track_top_holders(self, token_address: str) -> List[Dict]:
        """Track top 30 token holders"""
        try:
            # Get current holders
            holders = await self.helius.get_token_holders(token_address)
            if not holders:
                return []

            # Sort holders by amount
            sorted_holders = sorted(
                [(addr, float(amt)) for addr, amt in holders.items()],
                key=lambda x: x[1],
                reverse=True
            )[:30]  # Top 30 holders

            # Get additional holder data
            top_holders = []
            total_supply = sum(float(amount) for amount in holders.values())
            
            for addr, amount in sorted_holders:
                # Get holder's transaction history
                transactions = await self.helius.get_wallet_transactions(addr)
                
                # Calculate holding period
                if transactions:
                    first_tx = min(tx["timestamp"] for tx in transactions if tx.get("timestamp"))
                    holding_period = (datetime.now() - datetime.fromisoformat(first_tx)).days
                else:
                    holding_period = 0

                holder_data = {
                    "address": addr,
                    "amount": amount,
                    "percentage": (amount / total_supply * 100) if total_supply > 0 else 0,
                    "holding_period_days": holding_period,
                    "transaction_count": len(transactions) if transactions else 0
                }
                
                top_holders.append(holder_data)

            return top_holders

        except Exception as e:
            logger.error(f"Error tracking top holders: {str(e)}")
            return []

    async def _analyze_performance(self, token_address: str) -> Dict:
        """Analyze historical token performance"""
        try:
            # Get price history
            prices = await self.jupiter.get_price_history(token_address)
            if not prices:
                return {}

            # Calculate performance metrics
            returns = []
            volatility = []
            
            for i in range(1, len(prices)):
                price_change = (prices[i]["price"] - prices[i-1]["price"]) / prices[i-1]["price"]
                returns.append(price_change)
                volatility.append(price_change ** 2)

            if not returns:
                return {}

            avg_return = sum(returns) / len(returns)
            avg_volatility = (sum(volatility) / len(volatility)) ** 0.5

            # Calculate drawdown
            max_drawdown = 0
            peak = prices[0]["price"]
            
            for price_data in prices[1:]:
                price = price_data["price"]
                if price > peak:
                    peak = price
                drawdown = (peak - price) / peak
                max_drawdown = max(max_drawdown, drawdown)

            return {
                "average_return": avg_return,
                "volatility": avg_volatility,
                "max_drawdown": max_drawdown,
                "price_history": prices
            }

        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")
            return {}

    async def _calculate_win_rate(self, token_address: str) -> Dict:
        """Calculate 14-day win rate"""
        try:
            # Get price history
            prices = await self.jupiter.get_price_history(token_address)
            if not prices:
                return {}

            # Filter last 14 days
            cutoff = datetime.now() - timedelta(days=14)
            recent_prices = [p for p in prices 
                           if datetime.fromisoformat(p["timestamp"]) >= cutoff]

            if len(recent_prices) < 2:
                return {"14d_rate": 0, "winning_days": 0, "total_days": 0}

            # Calculate daily returns
            winning_days = 0
            total_days = len(recent_prices) - 1

            for i in range(1, len(recent_prices)):
                if recent_prices[i]["price"] > recent_prices[i-1]["price"]:
                    winning_days += 1

            win_rate = winning_days / total_days if total_days > 0 else 0

            return {
                "14d_rate": win_rate,
                "winning_days": winning_days,
                "total_days": total_days
            }

        except Exception as e:
            logger.error(f"Error calculating win rate: {str(e)}")
            return {"14d_rate": 0, "winning_days": 0, "total_days": 0}

    async def _track_pnl(self, token_address: str) -> Dict:
        """Track 30-day PNL"""
        try:
            # Get price history
            prices = await self.jupiter.get_price_history(token_address)
            if not prices:
                return {}

            # Filter last 30 days
            cutoff = datetime.now() - timedelta(days=30)
            recent_prices = [p for p in prices 
                           if datetime.fromisoformat(p["timestamp"]) >= cutoff]

            if len(recent_prices) < 2:
                return {"30d_pnl": 0, "daily_pnl": []}

            # Calculate daily PNL
            daily_pnl = []
            total_pnl = 0

            for i in range(1, len(recent_prices)):
                day_pnl = (recent_prices[i]["price"] - recent_prices[i-1]["price"]) / recent_prices[i-1]["price"]
                total_pnl += day_pnl
                
                daily_pnl.append({
                    "date": recent_prices[i]["timestamp"],
                    "pnl": day_pnl
                })

            return {
                "30d_pnl": total_pnl,
                "daily_pnl": daily_pnl,
                "best_day": max(daily_pnl, key=lambda x: x["pnl"]) if daily_pnl else None,
                "worst_day": min(daily_pnl, key=lambda x: x["pnl"]) if daily_pnl else None
            }

        except Exception as e:
            logger.error(f"Error tracking PNL: {str(e)}")
            return {"30d_pnl": 0, "daily_pnl": []}

    async def _analyze_wallet_patterns(self, token_address: str, holders: List[Dict]) -> Dict:
        """Analyze wallet behavior patterns"""
        try:
            patterns = defaultdict(int)
            wallet_behaviors = {}

            for holder in holders:
                address = holder["address"]
                
                # Get wallet transactions
                transactions = await self.helius.get_wallet_transactions(address)
                if not transactions:
                    continue

                # Analyze trading patterns
                behavior = self._identify_wallet_behavior(transactions)
                patterns[behavior["type"]] += 1
                wallet_behaviors[address] = behavior

                # Update wallet patterns database
                if address not in self.wallet_patterns["wallets"]:
                    self.wallet_patterns["wallets"][address] = []
                self.wallet_patterns["wallets"][address].append({
                    "token": token_address,
                    "behavior": behavior,
                    "timestamp": datetime.now().isoformat()
                })

            self._save_patterns()

            return {
                "pattern_distribution": dict(patterns),
                "wallet_behaviors": wallet_behaviors,
                "common_pattern": max(patterns.items(), key=lambda x: x[1])[0] if patterns else None
            }

        except Exception as e:
            logger.error(f"Error analyzing wallet patterns: {str(e)}")
            return {}

    def _identify_wallet_behavior(self, transactions: List[Dict]) -> Dict:
        """Identify wallet trading behavior pattern"""
        try:
            if not transactions:
                return {"type": "unknown", "confidence": 0}

            # Calculate metrics
            buy_count = sum(1 for tx in transactions if tx.get("type") == "buy")
            sell_count = sum(1 for tx in transactions if tx.get("type") == "sell")
            hold_time = 0
            
            if len(transactions) >= 2:
                first_tx = min(datetime.fromisoformat(tx["timestamp"]) 
                             for tx in transactions if tx.get("timestamp"))
                last_tx = max(datetime.fromisoformat(tx["timestamp"]) 
                            for tx in transactions if tx.get("timestamp"))
                hold_time = (last_tx - first_tx).days

            # Identify pattern
            if buy_count == 0 and sell_count == 0:
                pattern = "inactive"
                confidence = 1.0
            elif buy_count > sell_count * 2:
                pattern = "accumulator"
                confidence = min(1.0, buy_count / (buy_count + sell_count))
            elif sell_count > buy_count * 2:
                pattern = "distributor"
                confidence = min(1.0, sell_count / (buy_count + sell_count))
            elif hold_time > 30 and sell_count < buy_count:
                pattern = "hodler"
                confidence = min(1.0, hold_time / 365)
            elif buy_count > 0 and sell_count > 0 and abs(buy_count - sell_count) <= 2:
                pattern = "trader"
                confidence = min(1.0, (buy_count + sell_count) / 100)
            else:
                pattern = "mixed"
                confidence = 0.5

            return {
                "type": pattern,
                "confidence": confidence,
                "metrics": {
                    "buy_count": buy_count,
                    "sell_count": sell_count,
                    "hold_time_days": hold_time,
                    "total_transactions": len(transactions)
                }
            }

        except Exception as e:
            logger.error(f"Error identifying wallet behavior: {str(e)}")
            return {"type": "unknown", "confidence": 0}

    def _create_empty_analysis(self, token_address: str) -> Dict:
        """Create empty analysis result"""
        return {
            "token_address": token_address,
            "top_holders": [],
            "historical_performance": {},
            "win_rate": {"14d_rate": 0, "winning_days": 0, "total_days": 0},
            "pnl_tracking": {"30d_pnl": 0, "daily_pnl": []},
            "wallet_patterns": {},
            "timestamp": datetime.now().isoformat()
        }
