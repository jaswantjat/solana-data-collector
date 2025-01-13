import os
import logging
from typing import Dict, List, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

class SolscanAPI:
    def __init__(self):
        self.api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3MzY3NzkzMDAxNDQsImVtYWlsIjoiamFzd2FudDQwNDFAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzM2Nzc5MzAwfQ.--qIlxMFxlr3kTgeD1QaOmp_DTskBAHgVrP8ud9kOa8"
        self.base_url = "https://public-api.solscan.io"
        
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request"""
        try:
            headers = {
                "token": self.api_key,
                "Accept": "application/json"
            }
            
            url = f"{self.base_url}/{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"Error making Solscan request: {str(e)}")
            return {}
            
    async def get_token_info(self, token_address: str) -> Dict:
        """Get token information"""
        try:
            endpoint = f"token/meta/{token_address}"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Error getting token info: {str(e)}")
            return {}
            
    async def get_token_holders(self, token_address: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get token holders"""
        try:
            endpoint = f"token/holders/{token_address}"
            params = {
                "limit": limit,
                "offset": offset
            }
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting token holders: {str(e)}")
            return []
            
    async def get_token_market(self, token_address: str) -> Dict:
        """Get token market data"""
        try:
            endpoint = f"token/market/{token_address}"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Error getting token market: {str(e)}")
            return {}
            
    async def get_account_tokens(self, wallet_address: str) -> List[Dict]:
        """Get account token holdings"""
        try:
            endpoint = f"account/tokens/{wallet_address}"
            return await self._make_request(endpoint)
        except Exception as e:
            logger.error(f"Error getting account tokens: {str(e)}")
            return []
            
    async def get_account_transactions(self, wallet_address: str, limit: int = 100, before: Optional[str] = None) -> List[Dict]:
        """Get account transactions"""
        try:
            endpoint = f"account/transactions/{wallet_address}"
            params = {
                "limit": limit
            }
            if before:
                params["before"] = before
                
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting account transactions: {str(e)}")
            return []
            
    async def get_token_transactions(self, token_address: str, limit: int = 100, before: Optional[str] = None) -> List[Dict]:
        """Get token transactions"""
        try:
            endpoint = f"token/transactions/{token_address}"
            params = {
                "limit": limit
            }
            if before:
                params["before"] = before
                
            return await self._make_request(endpoint, params)
        except Exception as e:
            logger.error(f"Error getting token transactions: {str(e)}")
            return []
