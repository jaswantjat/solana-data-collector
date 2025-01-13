import logging
import time
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
from collections import defaultdict
import json
import traceback

logger = logging.getLogger(__name__)

@dataclass
class ErrorConfig:
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 300
    error_window: int = 3600

class CircuitBreaker:
    def __init__(self, name: str, config: ErrorConfig):
        self.name = name
        self.config = config
        self.failures = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        self.last_state_change = time.time()
        
    def record_failure(self):
        """Record a failure and potentially open the circuit"""
        current_time = time.time()
        if current_time - self.last_failure_time > self.config.error_window:
            self.failures = 0
            
        self.failures += 1
        self.last_failure_time = current_time
        
        if self.failures >= self.config.circuit_breaker_threshold:
            self.state = "open"
            self.last_state_change = current_time
            logger.warning(f"Circuit breaker {self.name} opened due to {self.failures} failures")
            
    def record_success(self):
        """Record a success and potentially close the circuit"""
        if self.state == "half-open":
            self.state = "closed"
            self.failures = 0
            self.last_state_change = time.time()
            logger.info(f"Circuit breaker {self.name} closed after successful recovery")
            
    def allow_request(self) -> bool:
        """Check if a request should be allowed"""
        current_time = time.time()
        
        if self.state == "open":
            if current_time - self.last_state_change > self.config.circuit_breaker_timeout:
                self.state = "half-open"
                self.last_state_change = current_time
                logger.info(f"Circuit breaker {self.name} entering half-open state")
                return True
            return False
            
        return True

class ErrorManager:
    def __init__(self):
        self.error_configs: Dict[str, ErrorConfig] = defaultdict(ErrorConfig)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_history: List[Dict] = []
        self.fallback_handlers: Dict[str, Callable] = {}
        
    def configure_service(self, service_name: str, config: ErrorConfig):
        """Configure error handling for a service"""
        self.error_configs[service_name] = config
        self.circuit_breakers[service_name] = CircuitBreaker(service_name, config)
        
    def register_fallback(self, service_name: str, handler: Callable):
        """Register a fallback handler for a service"""
        self.fallback_handlers[service_name] = handler
        
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function with fallback and circuit breaker"""
        circuit_breaker = self.circuit_breakers.get(service_name)
        if not circuit_breaker:
            circuit_breaker = CircuitBreaker(service_name, ErrorConfig())
            self.circuit_breakers[service_name] = circuit_breaker
            
        if not circuit_breaker.allow_request():
            logger.warning(f"Circuit breaker preventing request to {service_name}")
            return await self._handle_fallback(service_name, *args, **kwargs)
            
        try:
            result = await primary_func(*args, **kwargs)
            circuit_breaker.record_success()
            return result
            
        except Exception as e:
            circuit_breaker.record_failure()
            self._record_error(service_name, e)
            return await self._handle_fallback(service_name, *args, **kwargs)
            
    async def _handle_fallback(self, service_name: str, *args, **kwargs) -> Any:
        """Handle fallback for a failed service"""
        fallback = self.fallback_handlers.get(service_name)
        if fallback:
            try:
                return await fallback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback handler for {service_name} failed: {str(e)}")
                
        return None
        
    def _record_error(self, service_name: str, error: Exception):
        """Record an error for analysis"""
        self.error_counts[service_name] += 1
        
        error_info = {
            "service": service_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "stacktrace": traceback.format_exc()
        }
        
        self.error_history.append(error_info)
        
        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
            
        logger.error(f"Service {service_name} error: {str(error)}")
        
    async def get_error_stats(self) -> Dict:
        """Get error statistics"""
        return {
            "error_counts": dict(self.error_counts),
            "circuit_breaker_states": {
                name: breaker.state
                for name, breaker in self.circuit_breakers.items()
            },
            "recent_errors": self.error_history[-10:]  # Last 10 errors
        }
        
    async def analyze_errors(self) -> Dict:
        """Analyze error patterns"""
        error_patterns = defaultdict(int)
        service_health = {}
        
        for error in self.error_history:
            error_key = f"{error['service']}:{error['error_type']}"
            error_patterns[error_key] += 1
            
        for service in self.error_counts:
            recent_errors = sum(
                1 for error in self.error_history
                if error['service'] == service
                and datetime.fromisoformat(error['timestamp']) > datetime.utcnow() - timedelta(hours=1)
            )
            
            service_health[service] = {
                "status": "healthy" if recent_errors < 5 else "degraded" if recent_errors < 10 else "unhealthy",
                "error_rate": recent_errors / 3600,  # errors per second in last hour
                "circuit_breaker_status": self.circuit_breakers.get(service, CircuitBreaker(service, ErrorConfig())).state
            }
            
        return {
            "error_patterns": dict(error_patterns),
            "service_health": service_health
        }
        
    async def reset_service(self, service_name: str):
        """Reset error counts and circuit breaker for a service"""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(
                service_name,
                self.error_configs.get(service_name, ErrorConfig())
            )
            
        self.error_counts[service_name] = 0
        
        # Remove service errors from history
        self.error_history = [
            error for error in self.error_history
            if error['service'] != service_name
        ]
        
        logger.info(f"Reset error tracking for service: {service_name}")
