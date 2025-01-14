"""System recovery and resilience utilities"""
import logging
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from functools import wraps
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class SystemRecoveryManager:
    """Manages system recovery procedures and health checks"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = backup_dir
        self.health_checks = {}
        self.recovery_procedures = {}
        self.last_backup = None
        self._ensure_backup_dir()
        
    def _ensure_backup_dir(self):
        """Ensure backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
    async def backup_data(self, data: Dict, name: str):
        """Backup data to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        filepath = os.path.join(self.backup_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f)
            self.last_backup = filepath
            logger.info(f"Backup created: {filepath}")
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            raise
            
    async def restore_from_backup(self, name: str) -> Optional[Dict]:
        """Restore data from most recent backup"""
        try:
            backups = [f for f in os.listdir(self.backup_dir) if f.startswith(name)]
            if not backups:
                logger.warning(f"No backups found for {name}")
                return None
                
            latest = max(backups)
            filepath = os.path.join(self.backup_dir, latest)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            logger.info(f"Restored from backup: {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            raise
            
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
        logger.info(f"Registered health check: {name}")
        
    def register_recovery_procedure(self, name: str, recovery_func: Callable):
        """Register a recovery procedure"""
        self.recovery_procedures[name] = recovery_func
        logger.info(f"Registered recovery procedure: {name}")
        
    async def run_health_checks(self) -> Dict[str, bool]:
        """Run all registered health checks"""
        results = {}
        for name, check in self.health_checks.items():
            try:
                result = await check()
                results[name] = result
                if not result:
                    logger.warning(f"Health check failed: {name}")
            except Exception as e:
                logger.error(f"Health check error - {name}: {str(e)}")
                results[name] = False
        return results
        
    async def attempt_recovery(self, system: str) -> bool:
        """Attempt to recover a failed system"""
        if system not in self.recovery_procedures:
            logger.error(f"No recovery procedure for: {system}")
            return False
            
        try:
            await self.recovery_procedures[system]()
            logger.info(f"Recovery successful: {system}")
            return True
        except Exception as e:
            logger.error(f"Recovery failed - {system}: {str(e)}")
            return False

def with_retry(max_attempts: int = 3, backoff_factor: float = 1.5):
    """Decorator for retrying operations with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt == max_attempts:
                        logger.error(f"Max retry attempts reached for {func.__name__}")
                        raise
                    wait_time = backoff_factor ** attempt
                    logger.warning(f"Retry attempt {attempt} for {func.__name__} after {wait_time}s")
                    await asyncio.sleep(wait_time)
            return None
        return wrapper
    return decorator

class APIHealthMonitor:
    """Monitors API health and handles failures"""
    
    def __init__(self, endpoints: Dict[str, str]):
        self.endpoints = endpoints
        self.status = {name: True for name in endpoints}
        self.last_check = {name: None for name in endpoints}
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def check_endpoint(self, name: str, url: str) -> bool:
        """Check if an endpoint is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    healthy = response.status == 200
                    self.status[name] = healthy
                    self.last_check[name] = datetime.now()
                    return healthy
        except Exception as e:
            logger.error(f"API health check failed - {name}: {str(e)}")
            self.status[name] = False
            raise
            
    async def check_all_endpoints(self) -> Dict[str, bool]:
        """Check health of all endpoints"""
        results = {}
        for name, url in self.endpoints.items():
            try:
                results[name] = await self.check_endpoint(name, url)
            except Exception:
                results[name] = False
        return results

class DatabaseRecoveryManager:
    """Manages database connection recovery"""
    
    def __init__(self, db_url: str, max_retries: int = 3):
        self.db_url = db_url
        self.max_retries = max_retries
        self.connected = False
        self.last_connection_attempt = None
        self._connection = None
        self._retry_count = 0
        
    async def connect(self) -> bool:
        """Attempt to connect to database"""
        try:
            # Implement your database connection logic here
            # This is a mock implementation
            self._connection = True  # In real code, this would be the actual connection
            self.connected = True
            self.last_connection_attempt = datetime.now()
            self._retry_count = 0  # Reset on successful connection
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            self.connected = False
            self._connection = None
            raise
            
    async def ensure_connection(self) -> bool:
        """Ensure database connection is active"""
        if not self.connected or self._connection is None:
            if self._retry_count >= self.max_retries:
                raise Exception(f"Max retries ({self.max_retries}) exceeded")
            self._retry_count += 1
            return await self.connect()
        return True
        
    async def backup_database(self, backup_path: str):
        """Create database backup"""
        if not self.connected:
            raise RuntimeError("Database not connected")
            
        try:
            # Implement your database backup logic here
            # This is a mock implementation
            with open(backup_path, 'w') as f:
                f.write("Mock database backup")
            logger.info(f"Database backup created: {backup_path}")
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            raise
            
    async def restore_database(self, backup_path: str):
        """Restore database from backup"""
        if not self.connected:
            raise RuntimeError("Database not connected")
            
        try:
            # Implement your database restore logic here
            # This is a mock implementation
            with open(backup_path, 'r') as f:
                backup_data = f.read()
            logger.info(f"Database restored from: {backup_path}")
        except Exception as e:
            logger.error(f"Database restore failed: {str(e)}")
            raise

# Global recovery manager instance
recovery_manager = SystemRecoveryManager()
