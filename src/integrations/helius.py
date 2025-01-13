import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from .api_manager import APIManager

logger = logging.getLogger(__name__)

class HeliusAPI:
    def __init__(self):
        self.api_key = os.getenv("HELIUS_API_KEY")
        if not self.api_key:
            raise ValueError("HELIUS_API_KEY environment variable not set")
            
        self.base_url = "https://api.helius.xyz/v0"
        self.api_manager = APIManager()
        
    async def initialize(self):
        """Initialize the API client"""
        await self.api_manager.initialize()
        
    async def close(self):
        """Close the API client"""
        await self.api_manager.close()
        
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Any:
        """Make an API request with rate limiting and retries"""
        url = f"{self.base_url}/{endpoint}"
        if "params" not in kwargs:
            kwargs["params"] = {}
        kwargs["params"]["api-key"] = self.api_key
        
        return await self.api_manager.request("helius", method, url, **kwargs)
        
    async def get_token_metadata(self, address: str) -> Dict:
        """Get token metadata"""
        try:
            response = await self._make_request(
                "GET",
                f"token-metadata/{address}"
            )
            return response
        except Exception as e:
            logger.error(f"Error getting token metadata: {str(e)}")
            raise
            
    async def get_token_holders(self, address: str) -> List[Dict]:
        """Get token holders"""
        try:
            response = await self._make_request(
                "GET",
                f"token-holders/{address}"
            )
            return response.get("holders", [])
        except Exception as e:
            logger.error(f"Error getting token holders: {str(e)}")
            raise
            
    async def get_token_transfers(
        self,
        address: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get token transfers"""
        try:
            params = {}
            if start_time:
                params["startTime"] = int(start_time.timestamp())
            if end_time:
                params["endTime"] = int(end_time.timestamp())
                
            response = await self._make_request(
                "GET",
                f"token-transfers/{address}",
                params=params
            )
            return response.get("transfers", [])
        except Exception as e:
            logger.error(f"Error getting token transfers: {str(e)}")
            raise
            
    async def get_token_events(
        self,
        address: str,
        event_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get token events"""
        try:
            params = {}
            if event_types:
                params["eventTypes"] = event_types
                
            response = await self._make_request(
                "GET",
                f"token-events/{address}",
                params=params
            )
            return response.get("events", [])
        except Exception as e:
            logger.error(f"Error getting token events: {str(e)}")
            raise
            
    async def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return await self.api_manager.get_rate_limit_status("helius")
