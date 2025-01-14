import aiohttp
import logging
from typing import Dict, Optional
import os
import json

from ..error_handling.api_errors import (
    APIError,
    APIKeyError,
    handle_api_error,
    should_retry
)

logger = logging.getLogger(__name__)

class BirdeyeAPI:
    def __init__(self):
        self.api_key = os.getenv("BIRDEYE_API_KEY")
        if not self.api_key:
            raise APIKeyError("Birdeye")
            
        self.base_url = "https://public-api.birdeye.so/public"
        self.session = None
        self.max_retries = 3
        
    async def initialize(self):
        """Initialize Birdeye API session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Close Birdeye API session"""
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
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(
                url,
                params=params,
                headers={"X-API-KEY": self.api_key}
            ) as response:
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited by Birdeye API, retry after {retry_after}s")
                    return {"success": False, "error": "rate_limit", "retry_after": retry_after}
                    
                # Handle authentication errors
                if response.status == 401:
                    logger.error("Invalid Birdeye API key")
                    return {"success": False, "error": "invalid_api_key"}
                    
                try:
                    data = await response.json()
                except Exception as e:
                    logger.error(f"Error parsing Birdeye response: {str(e)}")
                    return {"success": False, "error": "invalid_response"}
                    
                # Handle 404 errors with specific token not found message
                if response.status == 404:
                    logger.warning(f"Token not found in Birdeye: {params.get('address')}")
                    return {
                        "success": False,
                        "error": "token_not_found",
                        "token": params.get("address")
                    }
                    
                if response.status != 200:
                    error = handle_api_error(
                        Exception(str(data.get("message", "Unknown error"))),
                        "Birdeye",
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
                
        except Exception as e:
            error = handle_api_error(e, "Birdeye", endpoint)
            if should_retry(error, retry_count, self.max_retries):
                return await self._make_request(
                    endpoint,
                    params,
                    retry_count + 1
                )
            return {"success": False, "error": str(error)}
            
    async def get_token_price(self, token_address: str) -> Dict:
        """Get token price information"""
        try:
            # Validate token address format
            if not token_address or len(token_address) < 32:
                return {
                    "price": 0,
                    "price_change_24h": 0,
                    "volume_24h": 0,
                    "error": "invalid_token_address"
                }
                
            result = await self._make_request(
                "price",
                {"address": token_address}
            )
            
            if not result.get("success"):
                error = result.get("error", "unknown_error")
                logger.error(f"Error fetching price from Birdeye: {error}")
                
                # If token not found, try alternative price sources
                if error == "token_not_found":
                    logger.info(f"Token {token_address} not found in Birdeye, trying alternative sources")
                    return await self._get_alternative_price(token_address)
                    
                return {
                    "price": 0,
                    "price_change_24h": 0,
                    "volume_24h": 0,
                    "error": error
                }
                
            data = result["data"]
            return {
                "price": float(data.get("value", 0)),
                "price_change_24h": float(data.get("priceChange24h", 0)),
                "volume_24h": float(data.get("volume24h", 0)),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error in get_token_price: {str(e)}")
            return {
                "price": 0,
                "price_change_24h": 0,
                "volume_24h": 0,
                "error": str(e)
            }
            
    async def _get_alternative_price(self, token_address: str) -> Dict:
        """Get price from alternative sources when Birdeye fails"""
        try:
            # Try getting price from DEX pools
            result = await self._make_request(
                "dex_price",
                {"address": token_address}
            )
            
            if result.get("success"):
                data = result["data"]
                return {
                    "price": float(data.get("value", 0)),
                    "price_change_24h": float(data.get("priceChange24h", 0)),
                    "volume_24h": float(data.get("volume24h", 0)),
                    "error": None
                }
                
            return {
                "price": 0,
                "price_change_24h": 0,
                "volume_24h": 0,
                "error": "price_not_available"
            }
            
        except Exception as e:
            logger.error(f"Error in _get_alternative_price: {str(e)}")
            return {
                "price": 0,
                "price_change_24h": 0,
                "volume_24h": 0,
                "error": "alternative_price_error"
            }
