"""Module for collecting DEX trade data"""
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ..config import BITQUERY_API_KEY, BITQUERY_ENDPOINT

class DexTradeCollector:
    def __init__(self):
        self.headers = {
            "X-API-KEY": BITQUERY_API_KEY,
            "Content-Type": "application/json"
        }

    async def collect_trade_data(self, token_address: str, days: int = 7) -> Dict:
        """
        Collect DEX trade data for a specific token
        
        Args:
            token_address (str): The token address to collect data for
            days (int): Number of days of historical data to collect
            
        Returns:
            Dict: Collected trade data including volume, price, and trades
        """
        try:
            since_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Query DEX trades from Bitquery
            query = """
            {
              solana {
                dexTrades(
                  options: {limit: 100, desc: "block.timestamp"}
                  date: {since: "%s"}
                  baseCurrency: {is: "%s"}
                ) {
                  block {
                    timestamp
                    height
                  }
                  transaction {
                    hash
                  }
                  tradeAmount
                  price
                  quoteCurrency {
                    symbol
                    name
                  }
                  baseCurrency {
                    symbol
                    name
                  }
                  exchange {
                    fullName
                  }
                }
              }
            }
            """ % (since_date, token_address)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    BITQUERY_ENDPOINT,
                    headers=self.headers,
                    json={"query": query}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        trades = data.get('data', {}).get('solana', {}).get('dexTrades', [])
                    else:
                        print(f"Error fetching DEX trades: {response.status}")
                        trades = []

            # Process trade data
            if trades:
                # Calculate volume and price metrics
                total_volume = sum(float(trade['tradeAmount']) for trade in trades)
                avg_price = sum(float(trade['price']) for trade in trades) / len(trades)
                latest_price = float(trades[0]['price']) if trades else 0
                
                # Get unique exchanges
                exchanges = list(set(trade['exchange']['fullName'] for trade in trades))
                
                return {
                    "token_address": token_address,
                    "period_days": days,
                    "total_volume": total_volume,
                    "average_price": avg_price,
                    "latest_price": latest_price,
                    "trade_count": len(trades),
                    "exchanges": exchanges,
                    "trades": trades,
                    "collected_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "token_address": token_address,
                    "period_days": days,
                    "total_volume": 0,
                    "average_price": 0,
                    "latest_price": 0,
                    "trade_count": 0,
                    "exchanges": [],
                    "trades": [],
                    "collected_at": datetime.utcnow().isoformat()
                }

        except Exception as e:
            print(f"Error collecting DEX trade data: {str(e)}")
            return {
                "token_address": token_address,
                "error": str(e),
                "collected_at": datetime.utcnow().isoformat()
            }

    async def monitor_trades(self, token_address: str, callback=None):
        """
        Continuously monitor trades for a specific token
        
        Args:
            token_address (str): The token address to monitor
            callback (Optional[Callable]): Callback function to handle new trades
        """
        while True:
            try:
                trade_data = await self.collect_trade_data(token_address, days=1)
                if callback and trade_data:
                    await callback(trade_data)
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Error monitoring trades: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
