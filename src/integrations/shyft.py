import aiohttp
import logging
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ShyftAPI:
    def __init__(self):
        self.api_key = os.getenv("SHYFT_API_KEY")
        self.base_url = "https://api.shyft.to/sol/v1"
        
    async def get_wallet_portfolio(self, address: str) -> Dict:
        """Get wallet portfolio and transaction history"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/wallet/portfolio",
                    params={"network": "mainnet-beta", "wallet": address},
                    headers={"x-api-key": self.api_key}
                ) as response:
                    data = await response.json()
                    return self._process_portfolio_data(data)
        except Exception as e:
            logger.error(f"Error fetching wallet portfolio: {str(e)}")
            return {}
            
    async def get_token_holders(self, token_address: str) -> List[Dict]:
        """Get token holders with their balances"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/token/holders",
                    params={
                        "network": "mainnet-beta",
                        "token_address": token_address
                    },
                    headers={"x-api-key": self.api_key}
                ) as response:
                    data = await response.json()
                    return self._process_holder_data(data)
        except Exception as e:
            logger.error(f"Error fetching token holders: {str(e)}")
            return []
            
    async def get_wallet_transactions(self, address: str) -> List[Dict]:
        """Get wallet transaction history"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/wallet/transactions",
                    params={
                        "network": "mainnet-beta",
                        "wallet": address,
                        "from_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                    },
                    headers={"x-api-key": self.api_key}
                ) as response:
                    data = await response.json()
                    return self._process_transaction_data(data)
        except Exception as e:
            logger.error(f"Error fetching wallet transactions: {str(e)}")
            return []
            
    def _process_portfolio_data(self, data: Dict) -> Dict:
        """Process portfolio data from SHYFT"""
        try:
            result = {
                "tokens": [],
                "total_value_usd": 0
            }
            
            for token in data.get("result", {}).get("tokens", []):
                result["tokens"].append({
                    "address": token.get("address"),
                    "symbol": token.get("symbol"),
                    "balance": float(token.get("balance", 0)),
                    "value_usd": float(token.get("value_usd", 0))
                })
                result["total_value_usd"] += float(token.get("value_usd", 0))
                
            return result
        except Exception as e:
            logger.error(f"Error processing portfolio data: {str(e)}")
            return {}
            
    def _process_holder_data(self, data: Dict) -> List[Dict]:
        """Process holder data from SHYFT"""
        try:
            holders = []
            for holder in data.get("result", []):
                holders.append({
                    "address": holder.get("owner"),
                    "balance": float(holder.get("amount", 0)),
                    "percent": float(holder.get("percent", 0))
                })
            return sorted(holders, key=lambda x: x["balance"], reverse=True)
        except Exception as e:
            logger.error(f"Error processing holder data: {str(e)}")
            return []
            
    def _process_transaction_data(self, data: Dict) -> List[Dict]:
        """Process transaction data from SHYFT"""
        try:
            transactions = []
            for tx in data.get("result", []):
                transactions.append({
                    "signature": tx.get("signature"),
                    "timestamp": tx.get("timestamp"),
                    "success": tx.get("status") == "Success",
                    "fee": float(tx.get("fee", 0)),
                    "type": tx.get("type"),
                    "token_transfers": tx.get("token_transfers", [])
                })
            return transactions
        except Exception as e:
            logger.error(f"Error processing transaction data: {str(e)}")
            return []
