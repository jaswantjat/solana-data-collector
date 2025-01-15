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

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(project_root, 'app.log'))
    ]
)

logger = logging.getLogger(__name__)

async def run_monitor():
    """Run the token monitoring system"""
    try:
        logger.info("Starting Solana Token Monitor...")
        
        # Initialize system
        try:
            if not await system.initialize():
                logger.error("System initialization failed")
                return
        except Exception as e:
            logger.error(f"System initialization error: {str(e)}")
            # Continue running even if system initialization fails
            # This allows the API to work even if the monitoring system fails

        # Start system operations
        await system.start()
        
    except Exception as e:
        logger.error(f"Error in run_monitor: {str(e)}")
    finally:
        await system.stop()

def run_api():
    """Run the FastAPI server"""
    try:
        port = int(os.getenv('PORT', '10000'))
        host = "0.0.0.0" if os.getenv('RENDER', '0') == '1' else "127.0.0.1"
        
        # Start the FastAPI server
        uvicorn.run(
            "src.api.server:app",
            host=host,
            port=port,
            reload=False,
            workers=1,
            log_level=LOG_LEVEL.lower()
        )
    except Exception as e:
        logger.error(f"Error in run_api: {str(e)}")

if __name__ == "__main__":
    # Run the API server directly
    run_api()
