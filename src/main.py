"""Main entry point for the Solana token monitoring system"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
import uvicorn

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Load environment variables before any other imports
load_dotenv(os.path.join(project_root, '.env'))

from src.core.system_integrator import system
from src.api.server import app
from src.config import LOG_LEVEL, LOG_FORMAT
from src.api.errors import APIError, ValidationError, DatabaseError
from src.utils.logging import get_logger

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(project_root, 'app.log'))
    ]
)

logger = get_logger(__name__)

async def run_monitor():
    """Run the token monitoring system."""
    try:
        await system.start()
    except Exception as e:
        logger.exception("Failed to start monitoring system")
        raise APIError(
            message="Failed to start monitoring system",
            details={"error": str(e)}
        )

async def run_api():
    """Run the FastAPI server."""
    try:
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=int(os.getenv("PORT", 10000)),
            log_level="info",
            reload=False
        )
        server = uvicorn.Server(config)
        await server.serve()
    except Exception as e:
        logger.exception("Failed to start API server")
        raise APIError(
            message="Failed to start API server",
            details={"error": str(e)}
        )

if __name__ == "__main__":
    # Run the API server directly
    asyncio.run(run_api())
