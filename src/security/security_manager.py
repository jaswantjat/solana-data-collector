import os
import logging
import json
import time
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from cryptography.fernet import Fernet
import hashlib
import hmac
import base64
from dataclasses import dataclass
from fastapi import Request, HTTPException
import aioredis
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    requests: int
    window: int  # in seconds
    block_duration: int  # in seconds

class SecurityManager:
    def __init__(self):
        # Initialize encryption key
        self.encryption_key = os.getenv("ENCRYPTION_KEY") or self._generate_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Initialize Redis for rate limiting
        self.redis = None
        self._init_redis()
        
        # Rate limit configurations
        self.rate_limits = {
            "default": RateLimitConfig(100, 60, 300),  # 100 requests per minute, 5 min block
            "high_priority": RateLimitConfig(1000, 60, 300),  # 1000 requests per minute
            "low_priority": RateLimitConfig(50, 60, 300)  # 50 requests per minute
        }
        
        # Load API keys
        self.api_keys = self._load_api_keys()
        
        # Initialize audit log
        self.audit_logger = self._setup_audit_logger()
        
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost"),
                encoding="utf-8",
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            
    def _generate_encryption_key(self) -> bytes:
        """Generate new encryption key"""
        key = Fernet.generate_key()
        
        # Save key securely
        key_path = Path(__file__).parent.parent.parent / "config" / "encryption_key"
        key_path.parent.mkdir(exist_ok=True)
        
        with open(key_path, 'wb') as f:
            f.write(key)
            
        return key
        
    def _load_api_keys(self) -> Dict:
        """Load API keys from secure storage"""
        try:
            keys_path = Path(__file__).parent.parent.parent / "config" / "api_keys.json"
            if keys_path.exists():
                with open(keys_path, 'r') as f:
                    encrypted_data = f.read()
                    decrypted_data = self.decrypt_data(encrypted_data)
                    return json.loads(decrypted_data)
            return {}
        except Exception as e:
            logger.error(f"Error loading API keys: {str(e)}")
            return {}
            
    def _setup_audit_logger(self) -> logging.Logger:
        """Setup audit logging"""
        audit_logger = logging.getLogger("audit")
        audit_logger.setLevel(logging.INFO)
        
        # Create audit log directory
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Setup file handler
        handler = logging.FileHandler(log_dir / "audit.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        
        return audit_logger
        
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise
            
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise
            
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key"""
        try:
            return api_key in self.api_keys
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return False
            
    async def check_rate_limit(self, key: str, limit_type: str = "default") -> bool:
        """Check if request is within rate limits"""
        try:
            if not self.redis:
                return True
                
            config = self.rate_limits.get(limit_type, self.rate_limits["default"])
            current_time = int(time.time())
            window_key = f"rate_limit:{key}:{current_time // config.window}"
            
            # Check if key is blocked
            block_key = f"rate_limit_block:{key}"
            if await self.redis.exists(block_key):
                return False
                
            # Increment request count
            count = await self.redis.incr(window_key)
            if count == 1:
                await self.redis.expire(window_key, config.window)
                
            # Check if limit exceeded
            if count > config.requests:
                await self.redis.setex(block_key, config.block_duration, 1)
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check error: {str(e)}")
            return True  # Allow request on error
            
    def audit_log(self, event_type: str, details: Dict):
        """Log audit event"""
        try:
            self.audit_logger.info(
                json.dumps({
                    "timestamp": datetime.now().isoformat(),
                    "event_type": event_type,
                    "details": details
                })
            )
        except Exception as e:
            logger.error(f"Audit logging error: {str(e)}")
            
    async def validate_request(self, request: Request) -> bool:
        """Validate incoming request"""
        try:
            # Check API key
            api_key = request.headers.get("X-API-Key")
            if not api_key or not self.validate_api_key(api_key):
                raise HTTPException(status_code=401, detail="Invalid API key")
                
            # Check rate limit
            client_ip = request.client.host
            if not await self.check_rate_limit(f"{api_key}:{client_ip}"):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
            # Validate request body if present
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.json()
                if not self._validate_request_body(body):
                    raise HTTPException(status_code=400, detail="Invalid request body")
                    
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Request validation error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
            
    def _validate_request_body(self, body: Dict) -> bool:
        """Validate request body structure and content"""
        try:
            # Add your validation logic here
            return True
        except Exception as e:
            logger.error(f"Request body validation error: {str(e)}")
            return False
            
    def backup_data(self, data: Dict, backup_type: str):
        """Backup system data"""
        try:
            backup_dir = Path(__file__).parent.parent.parent / "backups" / backup_type
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"{backup_type}_{timestamp}.json"
            
            # Encrypt sensitive data before backup
            encrypted_data = self.encrypt_data(json.dumps(data))
            
            with open(backup_file, 'w') as f:
                f.write(encrypted_data)
                
            # Cleanup old backups
            self._cleanup_old_backups(backup_dir)
            
            self.audit_log("backup_created", {
                "type": backup_type,
                "file": str(backup_file)
            })
            
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            raise
            
    def _cleanup_old_backups(self, backup_dir: Path, max_backups: int = 10):
        """Clean up old backup files"""
        try:
            backups = sorted(backup_dir.glob("*.json"), key=lambda x: x.stat().st_mtime)
            while len(backups) > max_backups:
                backups[0].unlink()
                backups = backups[1:]
        except Exception as e:
            logger.error(f"Backup cleanup error: {str(e)}")
            
    async def restore_from_backup(self, backup_file: Path) -> Dict:
        """Restore data from backup"""
        try:
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_file}")
                
            with open(backup_file, 'r') as f:
                encrypted_data = f.read()
                
            decrypted_data = self.decrypt_data(encrypted_data)
            restored_data = json.loads(decrypted_data)
            
            self.audit_log("backup_restored", {
                "file": str(backup_file)
            })
            
            return restored_data
            
        except Exception as e:
            logger.error(f"Restore error: {str(e)}")
            raise
            
def rate_limit(limit_type: str = "default"):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if not request:
                return await func(*args, **kwargs)
                
            security_manager = request.app.state.security_manager
            client_ip = request.client.host
            api_key = request.headers.get("X-API-Key", "anonymous")
            
            if not await security_manager.check_rate_limit(f"{api_key}:{client_ip}", limit_type):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator
