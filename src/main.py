"""Main entry point for the Solana token monitoring system."""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
import uvicorn
from contextlib import asynccontextmanager

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Load environment variables before any other imports
load_dotenv(os.path.join(project_root, '.env'))

from src.core.system_integrator import system
from src.api.server import app
from src.config import LOG_LEVEL, LOG_FORMAT
from src.api.errors import APIError, ValidationError, DatabaseError, ConfigError, ServiceUnavailableError
from src.utils.logging import get_logger, setup_logging
from src.monitoring.performance_manager import PerformanceManager

# Configure logging
setup_logging(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    log_file=os.path.join(project_root, 'app.log')
)

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app):
    """Handle startup and shutdown events."""
    try:
        # Initialize performance monitoring
        perf_manager = PerformanceManager()
        await perf_manager.initialize()
        
        # Start system components
        await system.start()
        
        logger.info(
            "System initialized successfully",
            extra={
                "components": ["api", "monitor", "performance"],
                "startup_time": datetime.utcnow().isoformat()
            }
        )
        
        yield
        
    except Exception as e:
        logger.exception("Failed to initialize system")
        raise ConfigError(
            message="System initialization failed",
            details={"error": str(e)}
        )
        
    finally:
        # Cleanup on shutdown
        try:
            await system.stop()
            await perf_manager.cleanup()
            
            logger.info(
                "System shutdown complete",
                extra={
                    "components": ["api", "monitor", "performance"],
                    "shutdown_time": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.exception("Error during system shutdown")

async def start_api_server():
    """Start the FastAPI server with proper error handling."""
    try:
        port = int(os.getenv("PORT", "10000"))
        host = "0.0.0.0"
        
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            reload=False,
            lifespan="on"
        )
        
        server = uvicorn.Server(config)
        
        logger.info(
            "Starting API server",
            extra={
                "host": host,
                "port": port,
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        )
        
        await server.serve()
        
    except OSError as e:
        logger.exception("Failed to start API server - Port binding error")
        raise ServiceUnavailableError(
            message=f"Failed to bind to port {port}",
            service="api_server",
            details={"error": str(e)}
        )
        
    except Exception as e:
        logger.exception("Failed to start API server")
        raise APIError(
            message="Failed to start API server",
            details={"error": str(e)}
        )

async def main():
    """Main entry point with proper error handling."""
    try:
        await start_api_server()
        
    except Exception as e:
        logger.exception("Critical error in main process")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception("Unhandled exception in main process")
        sys.exit(1)
