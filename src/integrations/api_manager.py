import asyncio
import logging
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from aiohttp import ClientSession, ClientTimeout
from asyncio import Lock, Queue
import backoff

from ..error_handling.error_manager import ErrorManager, ErrorConfig
from .base_api import APIConfig, BaseAPI
import os

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    requests_per_second: float
    requests_per_minute: int
    requests_per_hour: int
    retry_after: int = 60
    max_retries: int = 3

class APIRateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.request_times: Queue = Queue()
        self.lock = Lock()
        self._last_request_time = 0
        self._minute_requests = 0
        self._hour_requests = 0
        self._minute_start = time.time()
        self._hour_start = time.time()
        
    async def _cleanup_old_requests(self):
        """Clean up old request timestamps"""
        current_time = time.time()
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        # Clean up minute requests
        while not self.request_times.empty():
            timestamp = await self.request_times.get()
            if timestamp > minute_ago:
                await self.request_times.put(timestamp)
                break
                
        # Reset counters if needed
        if current_time - self._minute_start >= 60:
            self._minute_requests = 0
            self._minute_start = current_time
            
        if current_time - self._hour_start >= 3600:
            self._hour_requests = 0
            self._hour_start = current_time
            
    async def acquire(self):
        """Acquire rate limit permission"""
        async with self.lock:
            await self._cleanup_old_requests()
            
            current_time = time.time()
            
            # Check second rate limit
            if current_time - self._last_request_time < 1 / self.config.requests_per_second:
                await asyncio.sleep(1 / self.config.requests_per_second)
                
            # Check minute rate limit
            if self._minute_requests >= self.config.requests_per_minute:
                wait_time = 60 - (current_time - self._minute_start)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self._minute_requests = 0
                self._minute_start = time.time()
                
            # Check hour rate limit
            if self._hour_requests >= self.config.requests_per_hour:
                wait_time = 3600 - (current_time - self._hour_start)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self._hour_requests = 0
                self._hour_start = time.time()
                
            # Record request
            self._last_request_time = time.time()
            self._minute_requests += 1
            self._hour_requests += 1
            await self.request_times.put(time.time())

class APIManager:
    def __init__(self):
        # Initialize rate limiters
        self.rate_limiters: Dict[str, APIRateLimiter] = {
            "helius": APIRateLimiter(RateLimitConfig(
                requests_per_second=10,
                requests_per_minute=300,
                requests_per_hour=5000
            )),
            "solscan": APIRateLimiter(RateLimitConfig(
                requests_per_second=5,
                requests_per_minute=150,
                requests_per_hour=2000
            )),
            "shyft": APIRateLimiter(RateLimitConfig(
                requests_per_second=8,
                requests_per_minute=200,
                requests_per_hour=3000
            )),
            "bitquery": APIRateLimiter(RateLimitConfig(
                requests_per_second=3,
                requests_per_minute=100,
                requests_per_hour=1000
            )),
            "birdeye": APIRateLimiter(RateLimitConfig(
                requests_per_second=5,
                requests_per_minute=150,
                requests_per_hour=2000
            )),
            "jupiter": APIRateLimiter(RateLimitConfig(
                requests_per_second=10,
                requests_per_minute=300,
                requests_per_hour=5000
            )),
            "coingecko": APIRateLimiter(RateLimitConfig(
                requests_per_second=1,
                requests_per_minute=30,
                requests_per_hour=500
            ))
        }
        
        # Initialize API configs
        self.api_configs: Dict[str, APIConfig] = {
            "helius": APIConfig(
                api_key=os.getenv("HELIUS_API_KEY", ""),
                base_url="https://api.helius.xyz/v0",
                rate_limit=10
            ),
            "solscan": APIConfig(
                api_key=os.getenv("SOLSCAN_API_KEY", ""),
                base_url="https://public-api.solscan.io",
                rate_limit=5
            ),
            "shyft": APIConfig(
                api_key=os.getenv("SHYFT_API_KEY", ""),
                base_url="https://api.shyft.to/sol/v1",
                rate_limit=8
            ),
            "bitquery": APIConfig(
                api_key=os.getenv("BITQUERY_API_KEY", ""),
                base_url="https://graphql.bitquery.io",
                rate_limit=3
            ),
            "birdeye": APIConfig(
                api_key=os.getenv("BIRDEYE_API_KEY", ""),
                base_url="https://public-api.birdeye.so",
                rate_limit=5
            ),
            "jupiter": APIConfig(
                api_key=os.getenv("JUPITER_API_KEY", ""),
                base_url="https://price.jup.ag/v4",
                rate_limit=10
            ),
            "coingecko": APIConfig(
                api_key=os.getenv("COINGECKO_API_KEY", ""),
                base_url="https://api.coingecko.com/api/v3",
                rate_limit=1
            )
        }
        
        # Initialize API instances
        self.apis: Dict[str, BaseAPI] = {}
        self.error_manager = ErrorManager()
        
        # Configure error handling for each service
        for service in self.rate_limiters:
            self.error_manager.configure_service(
                service,
                ErrorConfig(
                    max_retries=3,
                    retry_delay=1.0,
                    circuit_breaker_threshold=5,
                    circuit_breaker_timeout=300,
                    error_window=3600
                )
            )
            
    async def initialize(self):
        """Initialize API manager"""
        # Initialize API instances
        for service_name, config in self.api_configs.items():
            self.apis[service_name] = BaseAPI(service_name, config)
            await self.apis[service_name].initialize()
            
        self._register_fallbacks()
        
    async def close(self):
        """Close API manager"""
        for api in self.apis.values():
            await api.close()
            
    def _register_fallbacks(self):
        """Register fallback handlers for services"""
        self.error_manager.register_fallback("helius", self.solscan_fallback)
        self.error_manager.register_fallback("solscan", self.helius_fallback)
        self.error_manager.register_fallback("shyft", self.solscan_fallback)
        
    async def helius_fallback(self, *args, **kwargs):
        """Fallback to Helius API"""
        return await self.request("helius", *args, **kwargs)
        
    async def solscan_fallback(self, *args, **kwargs):
        """Fallback to Solscan API"""
        return await self.request("solscan", *args, **kwargs)
        
    async def shyft_fallback(self, *args, **kwargs):
        """Fallback to Shyft API"""
        return await self.request("shyft", *args, **kwargs)
        
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30
    )
    async def request(
        self,
        api_name: str,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict:
        """Make an API request with rate limiting, retries, and circuit breaker"""
        if api_name not in self.apis:
            raise ValueError(f"Unknown API: {api_name}")
            
        # Check circuit breaker
        breaker = self.error_manager.circuit_breakers.get(api_name)
        if breaker and breaker.state == "open":
            logger.warning(f"Circuit breaker open for {api_name}, using fallback")
            return await self.error_manager._handle_fallback(api_name, method, endpoint, **kwargs)
            
        try:
            # Acquire rate limit
            await self.rate_limiters[api_name].acquire()
            
            # Make request
            api = self.apis[api_name]
            response = await api._make_request(method, endpoint, **kwargs)
            
            # Record success
            if breaker:
                breaker.record_success()
                
            return response
            
        except Exception as e:
            logger.error(f"Error in {api_name} request: {str(e)}")
            self.error_manager._record_error(api_name, e)
            
            if breaker:
                breaker.record_failure()
                
            # Try fallback
            return await self.error_manager._handle_fallback(api_name, method, endpoint, **kwargs)
            
    async def get_rate_limit_status(self, api_name: str) -> Dict[str, Any]:
        """Get current rate limit status"""
        if api_name not in self.rate_limiters:
            raise ValueError(f"Unknown API: {api_name}")
            
        limiter = self.rate_limiters[api_name]
        return {
            "minute_requests": limiter._minute_requests,
            "hour_requests": limiter._hour_requests,
            "minute_limit": limiter.config.requests_per_minute,
            "hour_limit": limiter.config.requests_per_hour
        }
