import logging
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..events.event_manager import event_manager
from ..error_handling.error_manager import ErrorManager

logger = logging.getLogger(__name__)

@dataclass
class RecoveryConfig:
    """Configuration for service recovery"""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    health_check_interval: float = 30.0

class RecoveryManager:
    """Manages service recovery attempts"""
    
    def __init__(self, error_manager: ErrorManager):
        """Initialize recovery manager"""
        self.error_manager = error_manager
        self.recovery_configs: Dict[str, RecoveryConfig] = {}
        self.health_checks: Dict[str, Callable] = {}
        self.recovery_attempts: Dict[str, int] = {}
        self.last_recovery: Dict[str, float] = {}
        
    def configure_service(self, service_name: str, config: RecoveryConfig):
        """Configure recovery for a service"""
        self.recovery_configs[service_name] = config
        
    def register_health_check(self, service_name: str, check: Callable):
        """Register a health check for a service"""
        self.health_checks[service_name] = check
        
    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        check = self.health_checks.get(service_name)
        if not check:
            logger.warning(f"No health check registered for {service_name}")
            return False
            
        try:
            is_healthy = await check()
            
            # Emit health check event
            await event_manager.emit(
                "health_check",
                {
                    "service": service_name,
                    "healthy": is_healthy,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {service_name}: {str(e)}")
            return False
            
    async def attempt_recovery(self, service_name: str) -> bool:
        """Attempt to recover a service"""
        config = self.recovery_configs.get(service_name, RecoveryConfig())
        attempts = self.recovery_attempts.get(service_name, 0)
        
        if attempts >= config.max_attempts:
            logger.error(f"Max recovery attempts reached for {service_name}")
            return False
            
        # Calculate backoff delay
        delay = min(
            config.initial_delay * (config.backoff_factor ** attempts),
            config.max_delay
        )
        
        # Record attempt
        self.recovery_attempts[service_name] = attempts + 1
        self.last_recovery[service_name] = datetime.now().timestamp()
        
        # Emit recovery attempt event
        await event_manager.emit(
            "recovery_attempt",
            {
                "service": service_name,
                "attempt": attempts + 1,
                "delay": delay
            }
        )
        
        # Wait before attempting recovery
        await asyncio.sleep(delay)
        
        try:
            # Reset service in error manager
            await self.error_manager.reset_service(service_name)
            
            # Check if service is now healthy
            is_healthy = await self.check_service_health(service_name)
            
            if is_healthy:
                # Reset recovery attempts on success
                self.recovery_attempts[service_name] = 0
                
                # Emit recovery success event
                await event_manager.emit(
                    "recovery_success",
                    {
                        "service": service_name,
                        "attempts": attempts + 1
                    }
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Recovery attempt failed for {service_name}: {str(e)}")
            
            # Emit recovery failure event
            await event_manager.emit(
                "recovery_failure",
                {
                    "service": service_name,
                    "error": str(e),
                    "attempt": attempts + 1
                }
            )
            
        return False
        
    async def monitor_services(self):
        """Monitor services and attempt recovery when needed"""
        while True:
            for service_name, config in self.recovery_configs.items():
                try:
                    # Skip if recent recovery attempt
                    last_attempt = self.last_recovery.get(service_name, 0)
                    if datetime.now().timestamp() - last_attempt < config.health_check_interval:
                        continue
                        
                    # Check service health
                    is_healthy = await self.check_service_health(service_name)
                    
                    if not is_healthy:
                        logger.warning(f"Service {service_name} unhealthy, attempting recovery")
                        await self.attempt_recovery(service_name)
                        
                except Exception as e:
                    logger.error(f"Error monitoring {service_name}: {str(e)}")
                    
            await asyncio.sleep(30)  # Check every 30 seconds
            
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get current status of a service"""
        return {
            "attempts": self.recovery_attempts.get(service_name, 0),
            "last_recovery": self.last_recovery.get(service_name, 0),
            "config": self.recovery_configs.get(service_name, RecoveryConfig()).__dict__
        }
        
# Global recovery manager instance
recovery_manager = RecoveryManager(error_manager=ErrorManager())
