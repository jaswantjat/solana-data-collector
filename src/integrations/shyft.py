import aiohttp
import logging
from typing import Dict, List, Optional, Any
import os
from datetime import datetime, timedelta
import json

from ..error_handling.api_errors import (
    APIError,
    APIKeyError,
    handle_api_error,
    should_retry
)

logger = logging.getLogger(__name__)

class ShyftAPI:
    def __init__(self):
        self.api_key = os.getenv("SHYFT_API_KEY")
        if not self.api_key:
            raise APIKeyError("Shyft")
            
        self.base_url = "https://api.shyft.to/sol/v1"
        self.session = None
        self.max_retries = 3
        
    async def initialize(self):
        """Initialize Shyft API"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
    async def close(self):
        """Close Shyft API"""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _sanitize_params(self, params: Dict) -> Dict:
        """Sanitize parameters to ensure they can be serialized"""
        sanitized = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, (list, dict)):
                sanitized[key] = json.dumps(value)
            else:
                sanitized[key] = str(value)
        return sanitized
            
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict:
        """Make an API request with retries and error handling"""
        if not self.session:
            await self.initialize()
            
        url = f"{self.base_url}/{endpoint}"
        sanitized_params = self._sanitize_params(params or {})
        
        try:
            async with self.session.request(
                method,
                url,
                params=sanitized_params,
                headers={"x-api-key": self.api_key}
            ) as response:
                data = await response.json()
                
                if response.status != 200:
                    error = handle_api_error(
                        Exception(data.get("message", "Unknown error")),
                        "Shyft",
                        endpoint,
                        response.status,
                        data
                    )
                    
                    if should_retry(error, retry_count, self.max_retries):
                        return await self._make_request(
                            method,
                            endpoint,
                            params,
                            retry_count + 1
                        )
                    raise error
                    
                return data
                
        except Exception as e:
            error = handle_api_error(e, "Shyft", endpoint)
            if should_retry(error, retry_count, self.max_retries):
                return await self._make_request(
                    method,
                    endpoint,
                    params,
                    retry_count + 1
                )
            raise error
            
    async def get_token_supply(self, token_address: str) -> Dict:
        """Get token supply information"""
        try:
            data = await self._make_request(
                "GET",
                "token/supply",
                {
                    "network": "mainnet-beta",
                    "token_address": token_address
                }
            )
            
            if not data.get("success"):
                logger.error(f"Error from Shyft API: {data.get('message')}")
                return {
                    "total_supply": 0,
                    "circulating_supply": 0
                }
                
            result = data.get("result", {})
            return {
                "total_supply": float(result.get("total_supply", 0)),
                "circulating_supply": float(result.get("circulating_supply", result.get("total_supply", 0)))
            }
            
        except APIError as e:
            logger.error(f"API error fetching token supply: {str(e)}")
            return {
                "total_supply": 0,
                "circulating_supply": 0
            }
        except Exception as e:
            logger.error(f"Error fetching token supply: {str(e)}")
            return {
                "total_supply": 0,
                "circulating_supply": 0
            }
            
    async def get_token_holders(self, token_address: str) -> List[Dict]:
        """Get token holders with their balances"""
        try:
            data = await self._make_request(
                "GET",
                "token/holders",
                {
                    "network": "mainnet-beta",
                    "token_address": token_address
                }
            )
            
            return self._process_holder_data(data)
            
        except APIError as e:
            logger.error(f"API error fetching token holders: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching token holders: {str(e)}")
            return []
            
    def _process_holder_data(self, data: Dict) -> List[Dict]:
        """Process holder data from SHYFT"""
        try:
            if not data.get("success"):
                return []
                
            holders = data.get("result", [])
            return [
                {
                    "address": holder.get("owner"),
                    "balance": float(holder.get("amount", 0)),
                    "percentage": float(holder.get("percentage", 0))
                }
                for holder in holders
                if holder.get("owner") and holder.get("amount")
            ]
            
        except Exception as e:
            logger.error(f"Error processing holder data: {str(e)}")
            return []
            
    async def get_wallet_portfolio(self, address: str) -> Dict:
        """Get wallet portfolio and transaction history"""
        try:
            data = await self._make_request(
                "GET",
                "wallet/portfolio",
                {
                    "network": "mainnet-beta",
                    "wallet": address
                }
            )
            
            return self._process_portfolio_data(data)
            
        except APIError as e:
            logger.error(f"API error fetching wallet portfolio: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching wallet portfolio: {str(e)}")
            return {}
            
    def _process_portfolio_data(self, data: Dict) -> Dict:
        """Process portfolio data from SHYFT"""
        try:
            if not data.get("success"):
                return {}
                
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
            
    async def get_wallet_transactions(self, address: str) -> List[Dict]:
        """Get wallet transaction history"""
        try:
            data = await self._make_request(
                "GET",
                "wallet/transactions",
                {
                    "network": "mainnet-beta",
                    "wallet": address,
                    "from_date": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                }
            )
            
            return self._process_transaction_data(data)
            
        except APIError as e:
            logger.error(f"API error fetching wallet transactions: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error fetching wallet transactions: {str(e)}")
            return []
            
    def _process_transaction_data(self, data: Dict) -> List[Dict]:
        """Process transaction data from SHYFT"""
        try:
            if not data.get("success"):
                return []
                
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
            
    async def get_token_info(self, token_address: str) -> Dict:
        """Get token information including supply, holders, and metadata"""
        try:
            data = await self._make_request(
                "GET",
                "token/get_info",
                {
                    "network": "mainnet-beta",
                    "token_address": token_address
                }
            )
            
            if response.status != 200:
                logger.error(f"Error fetching token info: {await response.text()}")
                return {}
                
            result = data.get("result", {})
            
            return {
                "address": token_address,
                "name": result.get("name", "Unknown"),
                "symbol": result.get("symbol", "Unknown"),
                "decimals": int(result.get("decimals", 0)),
                "total_supply": float(result.get("total_supply", 0)),
                "holder_count": int(result.get("holder_count", 0)),
                "current_supply": float(result.get("current_supply", 0)),
                "market_cap": float(result.get("market_cap", 0)),
                "price_usd": float(result.get("price_usd", 0))
            }
            
        except APIError as e:
            logger.error(f"API error fetching token info: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching token info: {str(e)}")
            return {}
