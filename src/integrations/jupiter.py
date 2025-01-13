import aiohttp
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class JupiterAPI:
    def __init__(self):
        self.base_url = "https://price.jup.ag/v4"
        
    async def get_token_price(self, mint_address: str) -> Dict:
        """Get token price from Jupiter"""
        try:
            url = f"{self.base_url}/price?ids={mint_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    return data.get("data", {}).get(mint_address, {})
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return {}

    async def get_token_liquidity(self, mint_address: str) -> Dict:
        """Get token liquidity info"""
        try:
            url = f"{self.base_url}/liquidity?ids={mint_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    data = await response.json()
                    return data.get("data", {}).get(mint_address, {})
        except Exception as e:
            logger.error(f"Error getting token liquidity: {str(e)}")
            return {}
