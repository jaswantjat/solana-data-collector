import os
import logging
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

class ShyftAPI:
    def __init__(self):
        self.api_key = os.getenv("SHYFT_API_KEY")
        self.base_url = "https://api.shyft.to/sol/v1"
        
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "Accept": "application/json"
            }
            
            url = f"{self.base_url}/{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error making SHYFT request: {str(e)}")
            return {}
            
    async def get_token_info(self, token_address: str) -> Dict:
        """Get token information"""
        try:
            endpoint = "token/get_info"
            params = {"network": "mainnet-beta", "token_address": token_address}
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return {}
            
    async def get_token_holders(self, token_address: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get token holders"""
        try:
            endpoint = "token/holders"
            params = {
                "network": "mainnet-beta",
                "token_address": token_address,
                "limit": limit,
                "offset": offset
            }
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting token holders: {str(e)}")
            return []
            
    async def get_wallet_tokens(self, wallet_address: str) -> List[Dict]:
        """Get wallet token holdings"""
        try:
            endpoint = "wallet/tokens"
            params = {
                "network": "mainnet-beta",
                "wallet": wallet_address
            }
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting wallet tokens: {str(e)}")
            return []
            
    async def get_wallet_transactions(self, wallet_address: str, limit: int = 100) -> List[Dict]:
        """Get wallet transactions"""
        try:
            endpoint = "transaction/history"
            params = {
                "network": "mainnet-beta",
                "wallet": wallet_address,
                "limit": limit
            }
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting wallet transactions: {str(e)}")
            return []
            
    async def get_token_transfers(self, token_address: str, limit: int = 100) -> List[Dict]:
        """Get token transfers"""
        try:
            endpoint = "token/transfers"
            params = {
                "network": "mainnet-beta",
                "token_address": token_address,
                "limit": limit
            }
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting token transfers: {str(e)}")
            return []
            
    async def get_token_price(self, token_address: str) -> Dict:
        """Get token price"""
        try:
            endpoint = "token/price"
            params = {
                "network": "mainnet-beta",
                "token_address": token_address
            }
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return {}
