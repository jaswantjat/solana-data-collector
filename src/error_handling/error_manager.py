import logging
import time
from typing import Dict, Optional, List, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
from collections import defaultdict
import json
import traceback

from ..events.event_manager import event_manager

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
        
    async def record_failure(self):
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
            
            # Emit circuit breaker event
            await event_manager.emit(
                "circuit_breaker",
                {
                    "service": self.name,
                    "state": "open",
                    "failures": self.failures
                }
            )
            
    async def record_success(self):
        """Record a success and potentially close the circuit"""
        if self.state == "half-open":
            self.state = "closed"
            self.failures = 0
            self.last_state_change = time.time()
            logger.info(f"Circuit breaker {self.name} closed after successful recovery")
            
            # Emit circuit breaker event
            await event_manager.emit(
                "circuit_breaker",
                {
                    "service": self.name,
                    "state": "closed",
                    "failures": self.failures
                }
            )
            
    def should_allow_request(self) -> bool:
        """Check if a request should be allowed"""
        if self.state == "closed":
            return True
            
        current_time = time.time()
        if self.state == "open":
            if current_time - self.last_state_change >= self.config.circuit_breaker_timeout:
                self.state = "half-open"
                self.last_state_change = current_time
                return True
            return False
            
        # Half-open state
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
        breaker = self.circuit_breakers.get(service_name)
        if breaker and not breaker.should_allow_request():
            logger.warning(f"Circuit breaker preventing request to {service_name}")
            return await self._handle_fallback(service_name, *args, **kwargs)
            
        try:
            result = await primary_func(*args, **kwargs)
            if breaker:
                await breaker.record_success()
            return result
            
        except Exception as e:
            logger.error(f"Error in {service_name}: {str(e)}")
            await self._record_error(service_name, e)
            
            if breaker:
                await breaker.record_failure()
                
            return await self._handle_fallback(service_name, *args, **kwargs)
            
    async def _handle_fallback(self, service_name: str, *args, **kwargs) -> Any:
        """Handle fallback for a failed service"""
        handler = self.fallback_handlers.get(service_name)
        if not handler:
            logger.warning(f"No fallback handler for {service_name}")
            return None
            
        try:
            result = await handler(*args, **kwargs)
            await event_manager.emit(
                "fallback_success",
                {
                    "service": service_name,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
            )
            return result
            
        except Exception as e:
            logger.error(f"Error in fallback for {service_name}: {str(e)}")
            await event_manager.emit(
                "fallback_failure",
                {
                    "service": service_name,
                    "error": str(e)
                }
            )
            return None
            
    async def _record_error(self, service_name: str, error: Exception):
        """Record an error for analysis"""
        current_time = time.time()
        error_data = {
            "service": service_name,
            "error": str(error),
            "type": type(error).__name__,
            "traceback": traceback.format_exc(),
            "timestamp": current_time
        }
        
        self.error_counts[service_name] += 1
        self.error_history.append(error_data)
        
        # Trim error history
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
            
        # Emit error event
        await event_manager.emit(
            "service_error",
            error_data,
            source=service_name
        )
        
    async def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        stats = {
            "total_errors": sum(self.error_counts.values()),
            "errors_by_service": dict(self.error_counts),
            "circuit_breaker_states": {
                name: breaker.state
                for name, breaker in self.circuit_breakers.items()
            }
        }
        
        # Emit stats event
        await event_manager.emit("error_stats", stats)
        
        return stats
        
    async def analyze_errors(self) -> Dict[str, Any]:
        """Analyze error patterns"""
        current_time = time.time()
        window_start = current_time - 3600  # Last hour
        
        recent_errors = [
            e for e in self.error_history
            if e["timestamp"] >= window_start
        ]
        
        analysis = {
            "error_rate": len(recent_errors) / 3600,
            "errors_by_type": defaultdict(int),
            "errors_by_service": defaultdict(int)
        }
        
        for error in recent_errors:
            analysis["errors_by_type"][error["type"]] += 1
            analysis["errors_by_service"][error["service"]] += 1
            
        # Emit analysis event
        await event_manager.emit("error_analysis", analysis)
        
        return analysis
        
    async def reset_service(self, service_name: str):
        """Reset error counts and circuit breaker for a service"""
        self.error_counts[service_name] = 0
        if service_name in self.circuit_breakers:
            breaker = self.circuit_breakers[service_name]
            breaker.failures = 0
            breaker.state = "closed"
            breaker.last_state_change = time.time()
            
            # Emit reset event
            await event_manager.emit(
                "service_reset",
                {"service": service_name}
            )
