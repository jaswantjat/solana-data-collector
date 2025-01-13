import os
import logging
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BitqueryAPI:
    def __init__(self):
        self.api_key = os.getenv("BITQUERY_API_KEY")
        self.base_url = "https://graphql.bitquery.io"
        
    async def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute GraphQL query"""
        try:
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json={"query": query, "variables": variables},
                    headers=headers
                ) as response:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error executing Bitquery: {str(e)}")
            return {}
            
    async def get_token_transfers(self, token_address: str, limit: int = 100) -> List[Dict]:
        """Get token transfer history"""
        query = """
        query ($token: String!, $limit: Int!) {
          solana {
            transfers(
              options: {limit: $limit}
              token: {address: {is: $token}}
            ) {
              amount
              block {
                timestamp {
                  time
                }
              }
              sender {
                address
              }
              receiver {
                address
              }
            }
          }
        }
        """
        
        variables = {
            "token": token_address,
            "limit": limit
        }
        
        result = await self.execute_query(query, variables)
        return result.get("data", {}).get("solana", {}).get("transfers", [])
        
    async def get_token_holders(self, token_address: str, min_balance: float = 0) -> List[Dict]:
        """Get current token holders"""
        query = """
        query ($token: String!, $min_balance: Float!) {
          solana {
            addresses(
              options: {desc: "balance"}
              token: {address: {is: $token}}
              balance: {greater: $min_balance}
            ) {
              address
              balance
            }
          }
        }
        """
        
        variables = {
            "token": token_address,
            "min_balance": min_balance
        }
        
        result = await self.execute_query(query, variables)
        return result.get("data", {}).get("solana", {}).get("addresses", [])
        
    async def get_token_price_history(self, token_address: str, days: int = 30) -> List[Dict]:
        """Get token price history"""
        query = """
        query ($token: String!, $since: ISO8601DateTime!) {
          solana {
            dexTrades(
              options: {asc: "block.timestamp.time"}
              token: {address: {is: $token}}
              time: {since: $since}
            ) {
              price
              block {
                timestamp {
                  time
                }
              }
            }
          }
        }
        """
        
        variables = {
            "token": token_address,
            "since": (datetime.now() - timedelta(days=days)).isoformat()
        }
        
        result = await self.execute_query(query, variables)
        return result.get("data", {}).get("solana", {}).get("dexTrades", [])
