import asyncio
from .token_collector import start_collector
import logging

logger = logging.getLogger(__name__)

async def start_background_tasks():
    """Start all background tasks"""
    try:
        # Start token collector
        asyncio.create_task(start_collector())
        logger.info("Started background token collector")
    except Exception as e:
        logger.error(f"Error starting background tasks: {str(e)}")

def init_background_tasks():
    """Initialize background tasks"""
    loop = asyncio.get_event_loop()
    loop.create_task(start_background_tasks())
