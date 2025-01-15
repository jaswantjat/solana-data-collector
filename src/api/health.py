"""Health check endpoints for the API."""
from datetime import datetime
from typing import Dict

import psutil
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.database.connection import db_manager
from src.monitoring.performance_manager import PerformanceManager
from src.utils.logging import get_logger

# Initialize router and logger
router = APIRouter(tags=["Health"])
logger = get_logger(__name__)
perf_manager = PerformanceManager()

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    error: str = None

class DetailedHealthResponse(HealthResponse):
    """Detailed health check response model."""
    database: Dict
    system: Dict
    performance: Dict
    uptime: float

@router.get("/health", response_model=HealthResponse)
async def health_check() -> Dict:
    """Basic health check endpoint.
    
    Returns:
        Dict containing basic health status
    """
    try:
        # Check database connection
        db_healthy = db_manager.check_connection()
        
        if not db_healthy:
            return HealthResponse(
                status="unhealthy",
                timestamp=datetime.utcnow(),
                error="Database connection failed"
            )
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            error=str(e)
        )

@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health() -> Dict:
    """Detailed health check with system metrics.
    
    Returns:
        Dict containing detailed system health information
    """
    try:
        # Get performance metrics
        metrics = perf_manager.get_performance_metrics()
        
        # Get CPU info
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Get memory info
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Get disk info
        disk = psutil.disk_usage('/')
        
        # Get network info
        net_io = psutil.net_io_counters()
        
        # Check database
        db_healthy = db_manager.check_connection()
        
        return DetailedHealthResponse(
            status="healthy" if db_healthy else "degraded",
            timestamp=datetime.utcnow(),
            database={
                "status": "connected" if db_healthy else "disconnected",
                "pool_size": db_manager.engine.pool.size() if db_manager.engine else 0,
                "overflow": db_manager.engine.pool.overflow() if db_manager.engine else 0
            },
            system={
                "cpu": {
                    "usage_percent": cpu_percent,
                    "core_count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used_percent": memory.percent,
                    "swap_used_percent": swap.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "used_percent": disk.percent
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errors_in": net_io.errin,
                    "errors_out": net_io.errout
                }
            },
            performance={
                "cpu_usage": metrics.cpu_usage,
                "memory_usage": metrics.memory_usage,
                "cache_hit_rate": metrics.cache_hit_rate,
                "request_rate": metrics.request_rate,
                "error_rate": metrics.error_rate
            },
            uptime=psutil.boot_time()
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        return DetailedHealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            error=str(e),
            database={},
            system={},
            performance={},
            uptime=0
        )
