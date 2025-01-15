"""Security manager for handling encryption, rate limiting, and API key validation"""
import os
import logging
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import hashlib
import hmac
import base64
from dataclasses import dataclass
from fastapi import Request, HTTPException
from functools import wraps

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing cryptography with detailed error handling
FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
    logger.info("Successfully imported cryptography.fernet")
except ImportError as e:
    logger.error(f"Failed to import cryptography: {str(e)}")
    logger.error("Please ensure cryptography is installed: pip install cryptography==41.0.7")
except Exception as e:
    logger.error(f"Unexpected error importing cryptography: {str(e)}")

# Try importing Redis with error handling
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
    logger.info("Redis module successfully loaded")
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis package not available. Rate limiting will use in-memory storage.")

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests: int
    window: int
    block_time: int

class SecurityManager:
    """Manages security features including encryption, rate limiting, and API key validation"""
    
    def __init__(self):
        """Initialize security manager"""
        # Initialize encryption
        self.encryption_key = os.getenv("ENCRYPTION_KEY")
        self.fernet = None
        
        if FERNET_AVAILABLE and self.encryption_key:
            try:
                if isinstance(self.encryption_key, str):
                    self.encryption_key = self.encryption_key.encode()
                self.fernet = Fernet(self.encryption_key)
                logger.info("Fernet encryption initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Fernet: {str(e)}")
                logger.error("Encryption will be disabled")
        else:
            logger.warning("Encryption disabled: cryptography module not available or no encryption key")
            
        # Initialize rate limiting
        redis_url = os.getenv("REDIS_URL", "redis://localhost")
        self.redis = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(redis_url)
                logger.info("Redis connection initialized")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {str(e)}")
        
        # Rate limit configurations
        self.rate_limits = {
            "default": RateLimitConfig(100, 60, 300),  # 100 requests per minute, 5 min block
            "high_priority": RateLimitConfig(1000, 60, 300),  # 1000 requests per minute
            "low_priority": RateLimitConfig(50, 60, 300)  # 50 requests per minute
        }
        
        # In-memory storage for rate limiting when Redis is not available
        self.in_memory_limits = {}
        
        # Load API keys
        self.api_keys = self._load_api_keys()
        
    def _generate_encryption_key(self) -> bytes:
        """Generate new encryption key"""
        if not FERNET_AVAILABLE:
            logger.warning("Cannot generate encryption key: cryptography module not available")
            return os.urandom(32)
        return Fernet.generate_key()
        
    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load API keys from environment or config"""
        # For now, just return an empty dict
        return {}
        
    def encrypt_data(self, data: str) -> Optional[str]:
        """Encrypt sensitive data"""
        if not self.fernet:
            logger.warning("Encryption attempted but Fernet not available")
            return data
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            return None

    def decrypt_data(self, encrypted_data: str) -> Optional[str]:
        """Decrypt sensitive data"""
        if not self.fernet:
            logger.warning("Decryption attempted but Fernet not available")
            return encrypted_data
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            return None

    async def check_rate_limit(self, key: str, limit_type: str = "default") -> bool:
        """Check if request is within rate limits"""
        config = self.rate_limits.get(limit_type, self.rate_limits["default"])
        
        if self.redis:
            # Use Redis for rate limiting
            try:
                async with self.redis.pipeline() as pipe:
                    now = int(time.time())
                    pipeline = pipe.zremrangebyscore(
                        key, 0, now - config.window
                    ).zadd(key, {str(now): now}).zcard(key).expire(key, config.window)
                    results = await pipeline.execute()
                    return results[2] <= config.requests
            except Exception as e:
                logger.error(f"Redis rate limiting failed: {str(e)}")
                return self._check_in_memory_rate_limit(key, config)
        else:
            # Use in-memory rate limiting
            return self._check_in_memory_rate_limit(key, config)
            
    def _check_in_memory_rate_limit(self, key: str, config: RateLimitConfig) -> bool:
        """Check rate limit using in-memory storage"""
        now = int(time.time())
        if key not in self.in_memory_limits:
            self.in_memory_limits[key] = []
            
        # Remove old timestamps
        self.in_memory_limits[key] = [
            ts for ts in self.in_memory_limits[key]
            if ts > now - config.window
        ]
        
        # Check limit
        if len(self.in_memory_limits[key]) >= config.requests:
            return False
            
        # Add new timestamp
        self.in_memory_limits[key].append(now)
        return True
        
    def validate_request(self, request: Request) -> bool:
        """Validate incoming request"""
        # Add request validation logic here
        return True

def rate_limit(limit_type: str = "default"):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                        
            if not request:
                logger.warning("No request object found for rate limiting")
                return await func(*args, **kwargs)
                
            client_ip = request.client.host
            key = f"rate_limit:{limit_type}:{client_ip}"
            
            security_manager = SecurityManager()
            if not await security_manager.check_rate_limit(key, limit_type):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests"
                )
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator
