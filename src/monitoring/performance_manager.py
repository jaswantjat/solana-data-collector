import os
import logging
import time
import asyncio
import psutil
import aioredis
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    response_time: float
    cpu_usage: float
    memory_usage: float
    active_connections: int
    cache_hit_rate: float
    error_rate: float

class PerformanceManager:
    def __init__(self):
        self.redis = None
        self._init_metrics()
        self.metrics_history = defaultdict(list)
        self.cache = {}
        self.cache_config = self._load_cache_config()
        
        # Initialize Prometheus metrics
        self.response_time_histogram = Histogram(
            'response_time_seconds',
            'Request response time in seconds',
            ['endpoint']
        )
        self.active_connections_gauge = Gauge(
            'active_connections',
            'Number of active connections'
        )
        self.cache_hit_rate_gauge = Gauge(
            'cache_hit_rate',
            'Cache hit rate percentage'
        )
        self.error_counter = Counter(
            'error_count',
            'Number of errors',
            ['type']
        )
        
        # Start Prometheus metrics server
        start_http_server(8000)
        
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
            
    def _init_metrics(self):
        """Initialize performance metrics"""
        self.metrics = {
            "response_times": [],
            "cpu_usage": [],
            "memory_usage": [],
            "active_connections": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": defaultdict(int)
        }
        
    def _load_cache_config(self) -> Dict:
        """Load cache configuration"""
        try:
            config_path = Path(__file__).parent.parent / "config" / "cache_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            return {
                "max_size": 1000,
                "ttl": 3600,
                "cleanup_interval": 300
            }
        except Exception as e:
            logger.error(f"Error loading cache config: {str(e)}")
            return {
                "max_size": 1000,
                "ttl": 3600,
                "cleanup_interval": 300
            }
            
    async def monitor_system_health(self):
        """Monitor system health metrics"""
        while True:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Update Prometheus metrics
                Gauge('cpu_usage_percent', 'CPU usage percentage').set(cpu_percent)
                Gauge('memory_usage_percent', 'Memory usage percentage').set(memory.percent)
                Gauge('disk_usage_percent', 'Disk usage percentage').set(disk.percent)
                
                # Store metrics history
                timestamp = datetime.now().isoformat()
                self.metrics_history["cpu"].append((timestamp, cpu_percent))
                self.metrics_history["memory"].append((timestamp, memory.percent))
                self.metrics_history["disk"].append((timestamp, disk.percent))
                
                # Cleanup old metrics
                self._cleanup_metrics_history()
                
                # Check for system alerts
                await self._check_system_alerts({
                    "cpu": cpu_percent,
                    "memory": memory.percent,
                    "disk": disk.percent
                })
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error monitoring system health: {str(e)}")
                await asyncio.sleep(60)
                
    def _cleanup_metrics_history(self):
        """Cleanup old metrics history"""
        try:
            cutoff = datetime.now() - timedelta(days=7)
            for metric_type in self.metrics_history:
                self.metrics_history[metric_type] = [
                    (ts, val) for ts, val in self.metrics_history[metric_type]
                    if datetime.fromisoformat(ts) > cutoff
                ]
        except Exception as e:
            logger.error(f"Error cleaning up metrics history: {str(e)}")
            
    async def _check_system_alerts(self, metrics: Dict):
        """Check system metrics for alert conditions"""
        try:
            alerts = []
            
            if metrics["cpu"] > 80:
                alerts.append(("HIGH_CPU", f"CPU usage at {metrics['cpu']}%"))
                
            if metrics["memory"] > 80:
                alerts.append(("HIGH_MEMORY", f"Memory usage at {metrics['memory']}%"))
                
            if metrics["disk"] > 80:
                alerts.append(("HIGH_DISK", f"Disk usage at {metrics['disk']}%"))
                
            # Send alerts if any
            if alerts:
                await self._send_system_alerts(alerts)
                
        except Exception as e:
            logger.error(f"Error checking system alerts: {str(e)}")
            
    async def _send_system_alerts(self, alerts: List[tuple]):
        """Send system alerts"""
        try:
            # Implement your alert sending mechanism here
            for alert_type, message in alerts:
                logger.warning(f"System Alert - {alert_type}: {message}")
                
        except Exception as e:
            logger.error(f"Error sending system alerts: {str(e)}")
            
    async def record_response_time(self, endpoint: str, response_time: float):
        """Record API endpoint response time"""
        try:
            self.response_time_histogram.labels(endpoint).observe(response_time)
            self.metrics["response_times"].append((endpoint, response_time))
            
            # Calculate and store average response time
            avg_time = np.mean([t for _, t in self.metrics["response_times"]])
            Gauge('average_response_time_seconds', 'Average response time in seconds').set(avg_time)
            
        except Exception as e:
            logger.error(f"Error recording response time: {str(e)}")
            
    def update_connection_count(self, delta: int):
        """Update active connection count"""
        try:
            self.metrics["active_connections"] += delta
            self.active_connections_gauge.set(self.metrics["active_connections"])
        except Exception as e:
            logger.error(f"Error updating connection count: {str(e)}")
            
    async def get_cached_data(self, key: str) -> Optional[Dict]:
        """Get data from cache"""
        try:
            if key in self.cache:
                data, expiry = self.cache[key]
                if expiry > time.time():
                    self.metrics["cache_hits"] += 1
                    self._update_cache_metrics()
                    return data
                    
            self.metrics["cache_misses"] += 1
            self._update_cache_metrics()
            return None
            
        except Exception as e:
            logger.error(f"Error accessing cache: {str(e)}")
            return None
            
    async def set_cached_data(self, key: str, data: Dict, ttl: Optional[int] = None):
        """Set data in cache"""
        try:
            if ttl is None:
                ttl = self.cache_config["ttl"]
                
            self.cache[key] = (data, time.time() + ttl)
            
            # Cleanup if cache size exceeds limit
            if len(self.cache) > self.cache_config["max_size"]:
                await self._cleanup_cache()
                
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            
    async def _cleanup_cache(self):
        """Cleanup expired cache entries"""
        try:
            current_time = time.time()
            expired_keys = [
                k for k, (_, exp) in self.cache.items()
                if exp <= current_time
            ]
            
            for k in expired_keys:
                del self.cache[k]
                
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")
            
    def _update_cache_metrics(self):
        """Update cache hit rate metrics"""
        try:
            total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
            if total_requests > 0:
                hit_rate = (self.metrics["cache_hits"] / total_requests) * 100
                self.cache_hit_rate_gauge.set(hit_rate)
        except Exception as e:
            logger.error(f"Error updating cache metrics: {str(e)}")
            
    def record_error(self, error_type: str):
        """Record error occurrence"""
        try:
            self.metrics["errors"][error_type] += 1
            self.error_counter.labels(type=error_type).inc()
        except Exception as e:
            logger.error(f"Error recording error: {str(e)}")
            
    async def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics"""
        try:
            # Calculate metrics
            avg_response_time = np.mean([t for _, t in self.metrics["response_times"]]) if self.metrics["response_times"] else 0
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
            cache_hit_rate = (self.metrics["cache_hits"] / total_requests * 100) if total_requests > 0 else 0
            total_errors = sum(self.metrics["errors"].values())
            
            return PerformanceMetrics(
                response_time=avg_response_time,
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                active_connections=self.metrics["active_connections"],
                cache_hit_rate=cache_hit_rate,
                error_rate=total_errors
            )
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return None
            
    async def get_metrics_history(self, metric_type: str, duration_hours: int = 24) -> List[tuple]:
        """Get historical metrics"""
        try:
            cutoff = datetime.now() - timedelta(hours=duration_hours)
            return [
                (ts, val) for ts, val in self.metrics_history[metric_type]
                if datetime.fromisoformat(ts) > cutoff
            ]
        except Exception as e:
            logger.error(f"Error getting metrics history: {str(e)}")
            return []
