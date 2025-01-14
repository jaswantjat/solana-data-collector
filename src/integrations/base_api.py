"""Base API integration class"""
import aiohttp
import logging
import os
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import asyncio
import time
from ..error_handling.api_errors import APIError, APIKeyError, handle_api_error
from ..config import (
    API_RATE_LIMIT,
    API_RATE_LIMIT_WINDOW,
    API_TIMEOUT,
    API_MAX_RETRIES,
    API_RETRY_DELAY
)

logger = logging.getLogger(__name__)

@dataclass
class APIConfig:
    """Configuration for API clients"""
    api_key: str
    base_url: str
    max_retries: int = API_MAX_RETRIES
    retry_delay: float = API_RETRY_DELAY
    timeout: Dict[str, float] = field(default_factory=lambda: dict(total=API_TIMEOUT))
    rate_limit: Dict[str, float] = field(default_factory=lambda: dict(default=API_RATE_LIMIT))
    rate_limit_window: float = API_RATE_LIMIT_WINDOW

class BaseAPI:
    """Base class for API integrations"""
    
    def __init__(self, service_name: str, config: APIConfig):
        """Initialize base API"""
        self.service_name = service_name
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_times = []
        self._rate_limit_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize API session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.config.api_key}"},
                timeout=aiohttp.ClientTimeout(
                    total=self.config.timeout["total"],
                    connect=self.config.timeout.get("connect", 0),
                    sock_read=self.config.timeout.get("read", 0),
                    sock_connect=self.config.timeout.get("write", 0)
                )
            )
            
    async def close(self):
        """Close API session"""
        if self.session:
            await self.session.close()
            self.session = None
            
    async def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        async with self._rate_limit_lock:
            current_time = time.time()
            # Remove old requests outside the window
            self._request_times = [t for t in self._request_times 
                                 if current_time - t < self.config.rate_limit_window]
            
            service_limit = self.config.rate_limit.get(self.service_name, 
                                                     self.config.rate_limit["default"])
            
            if len(self._request_times) >= service_limit:
                # Wait until oldest request expires
                sleep_time = self._request_times[0] + self.config.rate_limit_window - current_time
                if sleep_time > 0:
                    logger.debug(f"Rate limit reached, waiting {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    
            self._request_times.append(current_time)
            
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Make API request with retries and rate limiting"""
        if not self.session:
            await self.initialize()
            
        await self._enforce_rate_limit()
        
        url = f"{self.config.base_url}{endpoint}"
        retries = 0
        
        while retries < self.config.max_retries:
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:  # Rate limit exceeded
                        retry_after = int(response.headers.get('Retry-After', self.config.retry_delay))
                        logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        retries += 1
                        continue
                        
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                if retries < self.config.max_retries - 1 and await handle_api_error(e):
                    await asyncio.sleep(self.config.retry_delay * (2 ** retries))
                    retries += 1
                    continue
                raise APIError(f"Request failed: {str(e)}")
                
        raise APIError(f"Max retries ({self.config.max_retries}) exceeded")
        
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request"""
        return await self._make_request("GET", endpoint, params=params)
        
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make POST request"""
        return await self._make_request("POST", endpoint, json=data)
        
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, json=data)
        
    async def delete(self, endpoint: str) -> Dict:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint)
