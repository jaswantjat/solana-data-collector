"""Main entry point for the Solana token monitoring system"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

from .core.system_integrator import system
from .config import (
    DISCORD_WEBHOOK_URL,
    MIN_MARKET_CAP,
    CONFIDENCE_SCORE_THRESHOLD,
    POLLING_INTERVAL,
    LOG_LEVEL,
    LOG_FORMAT
)

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point"""
    try:
        logger.info("Starting Solana Token Monitor...")
        
        # Initialize system
        if not await system.initialize():
            logger.error("System initialization failed")
            return
            
        # Start monitoring
        await system.start()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
        
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        
    finally:
        # Ensure clean shutdown
        await system.shutdown()

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Start system
    asyncio.run(main())
