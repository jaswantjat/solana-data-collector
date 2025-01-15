"""Health check endpoints for the API."""
from datetime import datetime, timedelta
from typing import Dict, Optional
import time
import os

import psutil
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.database.connection import db_manager
from src.monitoring.performance_manager import PerformanceManager
from src.utils.logging import get_logger

# Initialize router and logger
router = APIRouter(tags=["Health"])
logger = get_logger(__name__)

# Initialize performance manager
perf_manager = PerformanceManager()

# Track start time for uptime calculation
START_TIME = time.time()

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Current health status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field("1.0.0", description="API version")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")

class DetailedHealthResponse(HealthResponse):
    """Detailed health check response model."""
    database: Dict = Field(..., description="Database health metrics")
    system: Dict = Field(..., description="System health metrics")
    performance: Dict = Field(..., description="Performance metrics")
    environment: Dict = Field(..., description="Environment information")

def get_system_info() -> Dict:
    """Get system metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        net_io = psutil.net_io_counters()
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else None,
                "load_average": psutil.getloadavg()
            },
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_percent": memory.percent,
                "swap_used_percent": swap.percent
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "error_in": net_io.errin,
                "error_out": net_io.errout
            }
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {
            "error": str(e)
        }

def get_environment_info() -> Dict:
    """Get environment information."""
    try:
        return {
            "python_version": os.sys.version,
            "platform": os.sys.platform,
            "environment": os.getenv("ENVIRONMENT", "production"),
            "timezone": datetime.now().astimezone().tzinfo.tzname(None)
        }
    except Exception as e:
        logger.error(f"Error getting environment info: {str(e)}")
        return {
            "error": str(e)
        }

@router.get(
    "/",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns basic health status of the API"
)
async def health_check() -> Dict:
    """Basic health check endpoint.
    
    Returns:
        Dict containing basic health status
    
    Raises:
        HTTPException: If health check fails
    """
    try:
        # Check database connection
        db_healthy = await db_manager.check_connection()
        
        # Calculate uptime
        uptime = time.time() - START_TIME
        
        if not db_healthy:
            return HealthResponse(
                status="unhealthy",
                timestamp=datetime.utcnow(),
                error="Database connection failed",
                uptime_seconds=uptime
            )
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

@router.get(
    "/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="Returns detailed health metrics including system and database status"
)
async def detailed_health() -> Dict:
    """Detailed health check with system metrics.
    
    Returns:
        Dict containing detailed system health information
    
    Raises:
        HTTPException: If health check fails
    """
    try:
        # Initialize performance manager if not already initialized
        if not perf_manager._initialized:
            await perf_manager.initialize()
        
        # Get performance metrics
        metrics = await perf_manager.get_performance_metrics()
        
        # Check database
        db_healthy = await db_manager.check_connection()
        db_info = {
            "status": "connected" if db_healthy else "disconnected",
            "pool_size": db_manager.engine.pool.size() if db_manager.engine else 0,
            "overflow": db_manager.engine.pool.overflow() if db_manager.engine else 0
        }
        
        # Calculate uptime
        uptime = time.time() - START_TIME
        
        return DetailedHealthResponse(
            status="healthy" if db_healthy else "degraded",
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            database=db_info,
            system=get_system_info(),
            performance=metrics.__dict__ if metrics else {},
            environment=get_environment_info()
        )
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
