import aiohttp
import asyncio
from datetime import datetime
from ..config import BITQUERY_API_KEY, BITQUERY_ENDPOINT

class DexTradeCollector:
    def __init__(self):
        self.headers = {
            "X-API-KEY": BITQUERY_API_KEY,
            "Content-Type": "application/json"
        }

    async def get_dex_trades(self, token_address):
        """
        Query Bitquery for DEX trades of a specific token
        """
        query = """
        {
          solana {
            dexTrades(
              options: {limit: 100}
              date: {since: "2024-01-12"}
              baseCurrency: {is: "%s"}
            ) {
              block {
                timestamp
                height
              }
              transaction {
                signature
              }
              tradeAmount
              price
              side
              exchange {
                fullName
              }
            }
          }
        }
        """ % token_address

        async with aiohttp.ClientSession() as session:
            async with session.post(
                BITQUERY_ENDPOINT,
                headers=self.headers,
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('solana', {}).get('dexTrades', [])
                else:
                    print(f"Error fetching DEX trades: {response.status}")
                    return []

    async def monitor_token_trades(self, token_address, callback=None):
        """
        Continuously monitor DEX trades for a specific token
        """
        while True:
            try:
                trades = await self.get_dex_trades(token_address)
                if callback and trades:
                    await callback(trades)
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
            except Exception as e:
                print(f"Error in monitoring trades: {str(e)}")
                await asyncio.sleep(30)  # Wait before retrying
