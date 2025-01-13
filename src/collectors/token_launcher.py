import aiohttp
import asyncio
from datetime import datetime
import json
from ..config import BITQUERY_API_KEY, BITQUERY_ENDPOINT, PUMP_FUN_PROGRAM_ID

class TokenLaunchCollector:
    def __init__(self):
        self.headers = {
            "X-API-KEY": BITQUERY_API_KEY,
            "Content-Type": "application/json"
        }

    async def get_new_token_launches(self):
        """
        Query Bitquery for new token launches on pump.fun
        """
        query = """
        {
          solana {
            smartContractCalls(
              options: {limit: 100}
              date: {since: "2024-01-12"}
              smartContractAddress: {is: "%s"}
            ) {
              block {
                timestamp
                height
              }
              signature
              caller
              success
              innerInstructions {
                index
                parentIndex
                program
                programId
              }
            }
          }
        }
        """ % PUMP_FUN_PROGRAM_ID

        async with aiohttp.ClientSession() as session:
            async with session.post(
                BITQUERY_ENDPOINT,
                headers=self.headers,
                json={"query": query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', {}).get('solana', {}).get('smartContractCalls', [])
                else:
                    print(f"Error fetching token launches: {response.status}")
                    return []

    async def monitor_new_launches(self, callback=None):
        """
        Continuously monitor for new token launches
        """
        while True:
            try:
                launches = await self.get_new_token_launches()
                if callback and launches:
                    await callback(launches)
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
            except Exception as e:
                print(f"Error in monitoring launches: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
