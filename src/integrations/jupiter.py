import aiohttp
import logging
from typing import Dict, Optional
import os
import json
from urllib.parse import urljoin

from ..error_handling.api_errors import (
    APIError,
    APIKeyError,
    handle_api_error,
    should_retry
)

logger = logging.getLogger(__name__)

class JupiterAPI:
    def __init__(self):
        self.api_key = os.getenv("JUPITER_API_KEY")
        if not self.api_key:
            raise APIKeyError("Jupiter")
            
        self.base_url = "https://price.jup.ag/v4"
        self.session = None
        self.max_retries = 3
        self.timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds timeout
        
    async def initialize(self):
        """Initialize Jupiter API session"""
        if not self.session:
            # Use a DNS resolver that doesn't rely on the system's DNS
            connector = aiohttp.TCPConnector(
                ttl_dns_cache=300,  # Cache DNS results for 5 minutes
                use_dns_cache=True,
                ssl=False  # Disable SSL verification if needed
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout
            )
            
    async def close(self):
        """Close Jupiter API session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict:
        """Make an API request with retries and error handling"""
        if not self.session:
            await self.initialize()
            
        url = urljoin(self.base_url, endpoint)
        
        try:
            async with self.session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                try:
                    data = await response.json()
                except Exception as e:
                    logger.error(f"Error parsing Jupiter response: {str(e)}")
                    return {"success": False, "error": "invalid_response"}
                    
                if response.status != 200:
                    error = handle_api_error(
                        Exception(str(data.get("message", "Unknown error"))),
                        "Jupiter",
                        endpoint,
                        response.status,
                        data
                    )
                    
                    if should_retry(error, retry_count, self.max_retries):
                        return await self._make_request(
                            endpoint,
                            params,
                            retry_count + 1
                        )
                    return {"success": False, "error": str(error)}
                    
                return {"success": True, "data": data}
                
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Connection error to Jupiter API: {str(e)}")
            if retry_count < self.max_retries:
                logger.info(f"Retrying Jupiter API connection ({retry_count + 1}/{self.max_retries})")
                return await self._make_request(endpoint, params, retry_count + 1)
            return {"success": False, "error": "connection_error"}
            
        except Exception as e:
            error = handle_api_error(e, "Jupiter", endpoint)
            if should_retry(error, retry_count, self.max_retries):
                return await self._make_request(
                    endpoint,
                    params,
                    retry_count + 1
                )
            return {"success": False, "error": str(error)}
            
    async def get_token_price(self, token_address: str) -> Dict:
        """Get token price information from Jupiter"""
        try:
            # Validate token address format
            if not token_address or len(token_address) < 32:
                return {
                    "price": 0,
                    "price_change_24h": 0,
                    "error": "invalid_token_address"
                }
                
            # Try getting price from Jupiter
            result = await self._make_request(
                f"price/{token_address}/USDC",
                {"vsToken": "USDC"}
            )
            
            if not result.get("success"):
                error = result.get("error", "unknown_error")
                logger.error(f"Error fetching price from Jupiter: {error}")
                
                # If connection error, try alternative endpoint
                if error == "connection_error":
                    return await self._get_alternative_price(token_address)
                    
                return {
                    "price": 0,
                    "price_change_24h": 0,
                    "error": error
                }
                
            data = result["data"]
            return {
                "price": float(data.get("price", 0)),
                "price_change_24h": float(data.get("priceChange24h", 0)),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error in get_token_price: {str(e)}")
            return {
                "price": 0,
                "price_change_24h": 0,
                "error": str(e)
            }
            
    async def _get_alternative_price(self, token_address: str) -> Dict:
        """Get price from alternative Jupiter endpoint"""
        try:
            # Try getting price from alternative endpoint
            result = await self._make_request(
                "quote",
                {
                    "inputMint": token_address,
                    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "amount": "1000000"  # 1 token
                }
            )
            
            if result.get("success"):
                data = result["data"]
                return {
                    "price": float(data.get("price", 0)),
                    "price_change_24h": 0,  # Not available from quote endpoint
                    "error": None
                }
                
            return {
                "price": 0,
                "price_change_24h": 0,
                "error": "price_not_available"
            }
            
        except Exception as e:
            logger.error(f"Error in _get_alternative_price: {str(e)}")
            return {
                "price": 0,
                "price_change_24h": 0,
                "error": "alternative_price_error"
            }
