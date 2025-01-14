import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.integrations.bitquery import BitqueryAPI
from src.integrations.helius import HeliusAPI

logger = logging.getLogger(__name__)

class TransactionMonitor:
    def __init__(self):
        self.bitquery = BitqueryAPI()
        self.helius = HeliusAPI()
        
    async def get_token_transactions(self, token_address: str, start_time: datetime, end_time: datetime) -> Dict:
        """Get transaction data for a specific token in the given time range"""
        try:
            # Get trades from BitQuery
            trades = await self.bitquery.fetch_token_trades(token_address)
            
            # Filter by time range
            filtered_trades = [
                trade for trade in trades
                if start_time <= datetime.fromisoformat(trade["block"]["timestamp"]) <= end_time
            ]
            
            # Calculate metrics
            buy_trades = [trade for trade in filtered_trades if self._is_buy_trade(trade)]
            sell_trades = [trade for trade in filtered_trades if not self._is_buy_trade(trade)]
            
            total_volume = sum(
                float(trade.get("amount", 0)) * float(trade.get("price", {}).get("usd", 0))
                for trade in filtered_trades
            )
            
            return {
                "token_address": token_address,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "total_transactions": len(filtered_trades),
                "buy_count": len(buy_trades),
                "sell_count": len(sell_trades),
                "buy_sell_ratio": len(buy_trades) / len(sell_trades) if sell_trades else float('inf'),
                "total_volume": total_volume,
                "avg_tx_size": total_volume / len(filtered_trades) if filtered_trades else 0,
                "unique_traders": len(set(
                    trade["sender"]["address"] for trade in filtered_trades
                ).union(set(
                    trade["receiver"]["address"] for trade in filtered_trades
                ))),
                "largest_trade": max(
                    (float(trade.get("amount", 0)) * float(trade.get("price", {}).get("usd", 0))
                    for trade in filtered_trades),
                    default=0
                ),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting token transactions for {token_address}: {str(e)}")
            return {"token_address": token_address, "error": str(e)}
    
    def _is_buy_trade(self, trade: Dict) -> bool:
        """Determine if a trade is a buy or sell"""
        try:
            # This is a simplified logic - you might want to enhance it based on your needs
            return float(trade.get("amount", 0)) > 0
        except Exception:
            return False
            
    async def monitor_wallet_transactions(self, wallet_address: str, lookback_hours: int = 24) -> Dict:
        """Monitor transactions for a specific wallet"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)
            
            # Get transactions from Helius
            transactions = await self.helius.get_wallet_transactions(wallet_address)
            
            # Filter and analyze transactions
            filtered_txs = [
                tx for tx in transactions
                if start_time <= datetime.fromisoformat(tx["timestamp"]) <= end_time
            ]
            
            return {
                "wallet_address": wallet_address,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "total_transactions": len(filtered_txs),
                "transaction_types": self._categorize_transactions(filtered_txs),
                "total_volume": sum(
                    float(tx.get("amount", 0)) * float(tx.get("price", {}).get("usd", 0))
                    for tx in filtered_txs
                ),
                "unique_tokens": len(set(
                    tx.get("token_address") for tx in filtered_txs
                    if tx.get("token_address")
                )),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error monitoring wallet transactions for {wallet_address}: {str(e)}")
            return {"wallet_address": wallet_address, "error": str(e)}
    
    def _categorize_transactions(self, transactions: List[Dict]) -> Dict:
        """Categorize transactions by type"""
        try:
            categories = {
                "swap": 0,
                "transfer": 0,
                "mint": 0,
                "burn": 0,
                "other": 0
            }
            
            for tx in transactions:
                tx_type = tx.get("type", "other").lower()
                if tx_type in categories:
                    categories[tx_type] += 1
                else:
                    categories["other"] += 1
                    
            return categories
        except Exception as e:
            logger.error(f"Error categorizing transactions: {str(e)}")
            return {}
