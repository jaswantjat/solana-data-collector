import asyncio
import logging
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from aiohttp import ClientSession, ClientTimeout
from asyncio import Lock, Queue
import backoff
from src.error_handling.error_manager import ErrorManager, ErrorConfig

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
        """Acquire permission to make a request"""
        async with self.lock:
            await self._cleanup_old_requests()
            
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            # Check rate limits
            if (self._minute_requests >= self.config.requests_per_minute or
                self._hour_requests >= self.config.requests_per_hour or
                time_since_last < 1/self.config.requests_per_second):
                
                wait_time = max(
                    1/self.config.requests_per_second - time_since_last,
                    0 if self._minute_requests < self.config.requests_per_minute else self.config.retry_after,
                    0 if self._hour_requests < self.config.requests_per_hour else 3600
                )
                
                if wait_time > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    
            # Update counters
            self._last_request_time = time.time()
            self._minute_requests += 1
            self._hour_requests += 1
            await self.request_times.put(self._last_request_time)

class APIManager:
    def __init__(self):
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
            ))
        }
        
        self.session: Optional[ClientSession] = None
        self.retry_codes = {408, 429, 500, 502, 503, 504}
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
        if not self.session:
            timeout = ClientTimeout(total=30)
            self.session = ClientSession(timeout=timeout)
            
        # Register fallback handlers
        self._register_fallbacks()
            
    async def close(self):
        """Close API manager"""
        if self.session:
            await self.session.close()
            self.session = None
            
    def _register_fallbacks(self):
        """Register fallback handlers for services"""
        # Helius fallback
        async def helius_fallback(*args, **kwargs):
            logger.info("Using Helius fallback: Solscan API")
            return await self.request("solscan", *args, **kwargs)
        self.error_manager.register_fallback("helius", helius_fallback)
        
        # Solscan fallback
        async def solscan_fallback(*args, **kwargs):
            logger.info("Using Solscan fallback: SHYFT API")
            return await self.request("shyft", *args, **kwargs)
        self.error_manager.register_fallback("solscan", solscan_fallback)
        
        # SHYFT fallback
        async def shyft_fallback(*args, **kwargs):
            logger.info("Using SHYFT fallback: cached data")
            # Return cached data or None
            return None
        self.error_manager.register_fallback("shyft", shyft_fallback)
            
    async def request(
        self,
        api_name: str,
        method: str,
        url: str,
        **kwargs
    ) -> Any:
        """Make an API request with rate limiting, retries, and circuit breaker"""
        if not self.session:
            await self.initialize()
            
        rate_limiter = self.rate_limiters.get(api_name)
        if not rate_limiter:
            raise ValueError(f"Unknown API: {api_name}")
            
        async def make_request():
            await rate_limiter.acquire()
            
            async with self.session.request(method, url, **kwargs) as response:
                if response.status in self.retry_codes:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        await asyncio.sleep(int(retry_after))
                    raise Exception(f"Retryable error: {response.status}")
                    
                response.raise_for_status()
                return await response.json()
                
        return await self.error_manager.execute_with_fallback(
            api_name,
            make_request
        )
            
    async def get_rate_limit_status(self, api_name: str) -> Dict:
        """Get current rate limit status"""
        rate_limiter = self.rate_limiters.get(api_name)
        if not rate_limiter:
            raise ValueError(f"Unknown API: {api_name}")
            
        # Get both rate limit and error stats
        rate_stats = {
            "minute_requests": rate_limiter._minute_requests,
            "hour_requests": rate_limiter._hour_requests,
            "time_since_last": time.time() - rate_limiter._last_request_time
        }
        
        error_stats = await self.error_manager.get_error_stats()
        service_stats = await self.error_manager.analyze_errors()
        
        return {
            "rate_limits": rate_stats,
            "errors": error_stats,
            "service_health": service_stats
        }
