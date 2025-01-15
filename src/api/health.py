"""Health check endpoints for the API."""
from fastapi import APIRouter
from typing import Dict
import psutil
import logging
from ..monitoring.performance_manager import PerformanceManager

router = APIRouter()
logger = logging.getLogger(__name__)
perf_manager = PerformanceManager()

@router.get("/health")
async def health_check() -> Dict:
    """Basic health check endpoint."""
    try:
        metrics = perf_manager.get_performance_metrics()
        return {
            "status": "healthy",
            "metrics": {
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "cache_hit_rate": metrics.cache_hit_rate
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/health/detailed")
async def detailed_health() -> Dict:
    """Detailed health check with system metrics."""
    try:
        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Get memory info
        memory = psutil.virtual_memory()
        
        # Get disk info
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy",
            "system": {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "core_count": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        }
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
