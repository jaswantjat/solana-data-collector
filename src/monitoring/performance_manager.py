"""Performance monitoring and metrics tracking."""
import os
import time
import asyncio
import psutil
import redis.asyncio as redis
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY

from src.utils.logging import get_logger, LogContext, log_error
from src.api.errors import DatabaseError, ConfigError, ServiceUnavailableError

logger = get_logger(__name__)

@dataclass
class PerformanceMetrics:
    """Data class for performance metrics."""
    response_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    cache_hit_rate: float = 0.0
    request_count: int = 0
    error_count: int = 0
    last_update: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "response_time": self.response_time,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "cache_hit_rate": self.cache_hit_rate,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "last_update": self.last_update.isoformat()
        }

class PerformanceManager:
    """Manages performance monitoring and metrics tracking."""
    
    _instance = None
    _initialized = False
    _lock = asyncio.Lock()

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            # Redis client
            self.redis: Optional[redis.Redis] = None
            
            # Metrics storage
            self.metrics_history: Dict[str, List[float]] = defaultdict(list)
            self.current_metrics = PerformanceMetrics()
            
            # Cache settings
            self.cache_config = self._load_cache_config()
            self.cache: Dict[str, Any] = {}
            self.cache_hits = 0
            self.cache_misses = 0
            
            # Prometheus metrics
            self._init_prometheus_metrics()
            
            # Async event loop
            self.loop = asyncio.get_event_loop()
            
            self._initialized = True

    async def _init_redis(self):
        """Initialize Redis connection."""
        with LogContext(logger, component="redis", action="init"):
            try:
                # Get Redis configuration from environment
                redis_host = os.environ.get('REDIS_HOST', 'localhost')
                redis_port = int(os.environ.get('REDIS_PORT', '6379'))
                redis_password = os.environ.get('REDIS_PASSWORD', '')
                redis_db = int(os.environ.get('REDIS_DB', '0'))
                max_retries = 3
                retry_delay = 5  # seconds

                # Handle Render environment
                if os.environ.get('RENDER') == '1':
                    redis_host = os.environ.get('REDIS_HOST', 'redis')
                    redis_port = int(os.environ.get('REDIS_PORT', '6379'))

                for attempt in range(max_retries):
                    try:
                        # Create Redis client
                        self.redis = redis.Redis(
                            host=redis_host,
                            port=redis_port,
                            password=redis_password,
                            db=redis_db,
                            decode_responses=True,
                            socket_timeout=5,
                            socket_connect_timeout=5
                        )
                        
                        # Test connection
                        await self.redis.ping()
                        logger.info(
                            "Connected to Redis",
                            extra={
                                "host": redis_host,
                                "port": redis_port,
                                "db": redis_db
                            }
                        )
                        return
                        
                    except redis.ConnectionError as e:
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Failed to connect to Redis (attempt {attempt + 1}/{max_retries})",
                                extra={
                                    "host": redis_host,
                                    "port": redis_port,
                                    "error": str(e),
                                    "attempt": attempt + 1,
                                    "max_retries": max_retries
                                }
                            )
                            await asyncio.sleep(retry_delay)
                        else:
                            log_error(
                                logger,
                                e,
                                f"Failed to connect to Redis after {max_retries} attempts",
                                context={
                                    "host": redis_host,
                                    "port": redis_port,
                                    "max_retries": max_retries
                                }
                            )
                            # Continue without Redis
                            self.redis = None
                            
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Error initializing Redis",
                    context={
                        "host": redis_host,
                        "port": redis_port
                    }
                )
                self.redis = None
                raise DatabaseError(
                    message="Failed to initialize Redis connection",
                    details={"error": str(e)}
                )

    def _load_cache_config(self) -> Dict[str, Any]:
        """Load cache configuration from file."""
        with LogContext(logger, component="cache", action="load_config"):
            try:
                config_path = Path("config/cache_config.json")
                if not config_path.exists():
                    default_config = {
                        "max_size": 1000,
                        "ttl": 3600,
                        "cleanup_interval": 300
                    }
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(config_path, "w") as f:
                        json.dump(default_config, f, indent=2)
                    return default_config
                    
                with open(config_path) as f:
                    return json.load(f)
                    
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Failed to load cache config",
                    context={"config_path": str(config_path)}
                )
                raise ConfigError(
                    message="Failed to load cache configuration",
                    details={"error": str(e)}
                )

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        with LogContext(logger, component="prometheus", action="init"):
            try:
                # Clear any existing metrics
                for collector in list(REGISTRY._collector_to_names.keys()):
                    REGISTRY.unregister(collector)
                
                # Request metrics
                self.request_counter = Counter(
                    "api_requests_total",
                    "Total number of API requests",
                    ["endpoint"]
                )
                self.error_counter = Counter(
                    "api_errors_total",
                    "Total number of API errors",
                    ["endpoint", "error_type"]
                )
                
                # Performance metrics
                self.response_time = Histogram(
                    "api_response_time_seconds",
                    "API response time in seconds",
                    ["endpoint"],
                    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
                )
                self.cpu_usage = Gauge(
                    "system_cpu_usage_percent",
                    "System CPU usage percentage"
                )
                self.memory_usage = Gauge(
                    "system_memory_usage_bytes",
                    "System memory usage in bytes"
                )
                
                # Cache metrics
                self.cache_hits = Counter(
                    "cache_hits_total",
                    "Total number of cache hits"
                )
                self.cache_misses = Counter(
                    "cache_misses_total",
                    "Total number of cache misses"
                )
                
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Failed to initialize Prometheus metrics"
                )
                raise ConfigError(
                    message="Failed to initialize Prometheus metrics",
                    details={"error": str(e)}
                )

    async def initialize(self):
        """Initialize the performance manager."""
        with LogContext(logger, component="performance_manager", action="init"):
            try:
                # Initialize Redis
                await self._init_redis()
                
                # Start background tasks
                self.loop.create_task(self._cleanup_cache())
                self.loop.create_task(self._update_system_metrics())
                
                # Start Prometheus server if enabled
                if os.environ.get('ENABLE_PROMETHEUS', 'false').lower() == 'true':
                    prometheus_port = int(os.environ.get('PROMETHEUS_PORT', '9090'))
                    start_http_server(prometheus_port)
                    logger.info(
                        "Started Prometheus server",
                        extra={"port": prometheus_port}
                    )
                
                logger.info("Performance manager initialized successfully")
                
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Failed to initialize performance manager"
                )
                raise ConfigError(
                    message="Performance manager initialization failed",
                    details={"error": str(e)}
                )

    async def _cleanup_cache(self):
        """Periodically clean up expired cache entries."""
        with LogContext(logger, component="cache", action="cleanup"):
            while True:
                try:
                    current_time = time.time()
                    expired_keys = [
                        key for key, (value, timestamp) in self.cache.items()
                        if current_time - timestamp > self.cache_config["ttl"]
                    ]
                    
                    for key in expired_keys:
                        del self.cache[key]
                        
                    # Trim cache if it exceeds max size
                    while len(self.cache) > self.cache_config["max_size"]:
                        # Remove oldest entry
                        oldest_key = min(
                            self.cache.items(),
                            key=lambda x: x[1][1]
                        )[0]
                        del self.cache[oldest_key]
                        
                    await asyncio.sleep(self.cache_config["cleanup_interval"])
                    
                except Exception as e:
                    log_error(
                        logger,
                        e,
                        "Cache cleanup error",
                        context={
                            "cache_size": len(self.cache),
                            "expired_keys": len(expired_keys)
                        }
                    )
                    await asyncio.sleep(60)  # Retry after a minute

    async def _update_system_metrics(self):
        """Periodically update system metrics."""
        with LogContext(logger, component="metrics", action="update"):
            while True:
                try:
                    # Update CPU and memory metrics
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    
                    self.cpu_usage.set(cpu_percent)
                    self.memory_usage.set(memory.used)
                    
                    # Update current metrics
                    self.current_metrics.cpu_usage = cpu_percent
                    self.current_metrics.memory_usage = memory.percent
                    self.current_metrics.last_update = datetime.utcnow()
                    
                    # Store in history
                    self.metrics_history["cpu_usage"].append(cpu_percent)
                    self.metrics_history["memory_usage"].append(memory.percent)
                    
                    # Keep last hour of history
                    max_history = 3600  # 1 hour at 1 second intervals
                    for metric_list in self.metrics_history.values():
                        if len(metric_list) > max_history:
                            metric_list.pop(0)
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    log_error(
                        logger,
                        e,
                        "System metrics update error"
                    )
                    await asyncio.sleep(60)  # Retry after a minute

    async def record_request(
        self,
        endpoint: str,
        response_time: float,
        error: Optional[str] = None
    ):
        """Record API request metrics.
        
        Args:
            endpoint: API endpoint
            response_time: Request response time in seconds
            error: Error message if request failed
        """
        with LogContext(logger, component="metrics", action="record_request", endpoint=endpoint):
            try:
                # Update Prometheus metrics
                self.request_counter.labels(endpoint=endpoint).inc()
                self.response_time.labels(endpoint=endpoint).observe(response_time)
                
                if error:
                    self.error_counter.labels(
                        endpoint=endpoint,
                        error_type=type(error).__name__
                    ).inc()
                    self.current_metrics.error_count += 1
                
                # Update current metrics
                self.current_metrics.request_count += 1
                self.current_metrics.response_time = (
                    (self.current_metrics.response_time * (self.current_metrics.request_count - 1) +
                    response_time) / self.current_metrics.request_count
                )
                
                # Store in Redis if available
                if self.redis:
                    await self.redis.hincrby(f"metrics:{endpoint}", "request_count", 1)
                    await self.redis.hset(
                        f"metrics:{endpoint}",
                        "last_response_time",
                        str(response_time)
                    )
                    if error:
                        await self.redis.hincrby(f"metrics:{endpoint}", "error_count", 1)
                        
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Failed to record request metrics",
                    context={
                        "endpoint": endpoint,
                        "response_time": response_time,
                        "error": error
                    }
                )

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired
        """
        with LogContext(logger, component="cache", action="get", key=key):
            try:
                if key in self.cache:
                    value, timestamp = self.cache[key]
                    if time.time() - timestamp <= self.cache_config["ttl"]:
                        self.cache_hits.inc()
                        return value
                        
                self.cache_misses.inc()
                return None
                
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Cache get error",
                    context={"key": key}
                )
                return None

    async def set_cache(self, key: str, value: Any):
        """Set cache value.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with LogContext(logger, component="cache", action="set", key=key):
            try:
                async with self._lock:
                    self.cache[key] = (value, time.time())
                    
                    # Update cache hit rate
                    total_requests = self.cache_hits._value.get() + self.cache_misses._value.get()
                    if total_requests > 0:
                        self.current_metrics.cache_hit_rate = (
                            self.cache_hits._value.get() / total_requests
                        )
                        
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Cache set error",
                    context={"key": key}
                )

    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.
        
        Returns:
            PerformanceMetrics object with current metrics
        """
        with LogContext(logger, component="metrics", action="get"):
            return self.current_metrics

    async def cleanup(self):
        """Cleanup resources."""
        with LogContext(logger, component="performance_manager", action="cleanup"):
            try:
                if self.redis:
                    await self.redis.close()
                self.cache.clear()
                self.metrics_history.clear()
                logger.info("PerformanceManager cleanup completed")
            except Exception as e:
                log_error(
                    logger,
                    e,
                    "Cleanup error"
                )
                raise ServiceUnavailableError(
                    message="Failed to cleanup performance manager",
                    details={"error": str(e)}
                )
