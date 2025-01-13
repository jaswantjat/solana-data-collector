import logging
import os
from typing import Optional, Any, Dict, List
import json
from datetime import datetime, timedelta
import aioredis
import asyncio
import backoff
from functools import wraps

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        """Initialize Redis connection with Redis Labs configuration"""
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_password = os.getenv("REDIS_PASSWORD")
        
        if not self.redis_url or not self.redis_password:
            raise ValueError("REDIS_URL and REDIS_PASSWORD must be set")
            
        # Parse Redis Labs URL for SSL configuration
        self.use_ssl = "redislabs.com" in self.redis_url
        
        # Configure connection pool
        self.pool_size = int(os.getenv("REDIS_POOL_SIZE", "10"))
        self.timeout = int(os.getenv("REDIS_TIMEOUT", "5"))
        
        # Initialize statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "last_error": None,
            "created_at": datetime.now()
        }
        
        # Initialize connection
        self.redis = None
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                password=self.redis_password,
                ssl=self.use_ssl,
                max_connections=self.pool_size,
                timeout=self.timeout,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis.ping()
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            raise
            
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30
    )
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with retry logic"""
        try:
            if not self.redis:
                return None
                
            value = await self.redis.get(key)
            
            if value:
                self.stats["hits"] += 1
                return json.loads(value)
            else:
                self.stats["misses"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            return None
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Set value in cache"""
        try:
            if not self.redis:
                return False
                
            # Serialize value
            serialized = json.dumps(value)
            
            if nx:
                # Only set if key doesn't exist
                success = await self.redis.set(
                    key,
                    serialized,
                    ex=ttl,
                    nx=True
                )
            else:
                # Set or update key
                success = await self.redis.set(
                    key,
                    serialized,
                    ex=ttl
                )
                
            return bool(success)
            
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if not self.redis:
                return False
                
            return bool(await self.redis.delete(key))
            
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            return False
            
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if not self.redis:
                return False
                
            return bool(await self.redis.exists(key))
            
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            return False
            
    async def ttl(self, key: str) -> Optional[int]:
        """Get TTL for key"""
        try:
            if not self.redis:
                return None
                
            ttl = await self.redis.ttl(key)
            return ttl if ttl > -1 else None
            
        except Exception as e:
            logger.error(f"Cache TTL error: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            return None
            
    async def clear(self, pattern: str = "*") -> int:
        """Clear cache keys matching pattern"""
        try:
            if not self.redis:
                return 0
                
            # Get keys matching pattern
            keys = []
            async for key in self.redis.scan_iter(pattern):
                keys.append(key)
                
            if keys:
                return await self.redis.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            self.stats["errors"] += 1
            self.stats["last_error"] = str(e)
            return 0
            
    def cached(self, ttl: Optional[int] = None):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # Try to get from cache
                cached_value = await self.get(key)
                if cached_value is not None:
                    return cached_value
                    
                # Get fresh value
                value = await func(*args, **kwargs)
                
                # Cache the value
                if value is not None:
                    await self.set(key, value, ttl)
                    
                return value
                
            return wrapper
        return decorator
        
    async def get_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            if not self.redis:
                return self.stats
                
            # Get Redis info
            info = await self.redis.info()
            
            # Calculate hit rate
            total_ops = self.stats["hits"] + self.stats["misses"]
            hit_rate = self.stats["hits"] / total_ops if total_ops > 0 else 0
            
            return {
                **self.stats,
                "uptime": str(datetime.now() - self.stats["created_at"]),
                "hit_rate": hit_rate,
                "memory_usage": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_connections_received": info.get("total_connections_received")
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return self.stats
            
    async def health_check(self) -> Dict:
        """Perform health check"""
        try:
            if not self.redis:
                return {
                    "status": "not_initialized",
                    "timestamp": datetime.now().isoformat()
                }
                
            start_time = datetime.now()
            await self.redis.ping()
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "stats": await self.get_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": await self.get_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
    async def cleanup(self):
        """Cleanup Redis connection"""
        if self.redis:
            await self.redis.close()
            await self.redis.wait_closed()
            self.redis = None
