from typing import Dict, Optional
import logging
from datetime import datetime, timedelta

from ..integrations.birdeye import BirdeyeAPI
from ..integrations.jupiter import JupiterAPI
from ..integrations.shyft import ShyftAPI
from ..integrations.bitquery import BitqueryAPI
from ..test.mock_data import (
    get_mock_price,
    get_mock_volume,
    should_use_mock_data
)

logger = logging.getLogger(__name__)

class MarketAnalysis:
    def __init__(self):
        """Initialize market analysis"""
        self.birdeye = BirdeyeAPI()
        self.jupiter = JupiterAPI()
        self.shyft = ShyftAPI()
        self.bitquery = BitqueryAPI()
        self.use_mock = should_use_mock_data()
        
    async def initialize(self):
        """Initialize API connections"""
        await self.birdeye.initialize()
        await self.jupiter.initialize()
        await self.shyft.initialize()
        await self.bitquery.initialize()
        
    async def close(self):
        """Close API connections"""
        await self.birdeye.close()
        await self.jupiter.close()
        await self.shyft.close()
        await self.bitquery.close()
        
    async def get_price(self, token_address: str) -> Dict:
        """Get token price from multiple sources with fallback"""
        try:
            if self.use_mock:
                return get_mock_price(token_address)
                
            # Try Birdeye first
            try:
                birdeye_price = await self.birdeye.get_token_price(token_address)
                if not birdeye_price.get("error"):
                    return birdeye_price
                logger.warning(f"Birdeye price fetch failed, trying Jupiter: {birdeye_price['error']}")
            except Exception as e:
                logger.warning(f"Birdeye price fetch failed, trying Jupiter: {str(e)}")
            
            # Fallback to Jupiter
            try:
                jupiter_price = await self.jupiter.get_token_price(token_address)
                if not jupiter_price.get("error"):
                    return jupiter_price
                logger.warning(f"Jupiter price fetch failed: {jupiter_price['error']}")
            except Exception as e:
                logger.warning(f"Jupiter price fetch failed: {str(e)}")
            
            # If both fail, return error
            return {
                "price": 0,
                "price_change_24h": 0,
                "error": "Failed to fetch price from all sources"
            }
            
        except Exception as e:
            logger.error(f"Error getting token price: {str(e)}")
            return {
                "price": 0,
                "price_change_24h": 0,
                "error": str(e)
            }
            
    async def get_market_cap(self, token_address: str) -> Dict:
        """Get token market cap"""
        try:
            if self.use_mock:
                price_data = get_mock_price(token_address)
                supply_data = {"total_supply": 1000000000}
                return {
                    "market_cap": price_data["price"] * supply_data["total_supply"],
                    "error": None
                }
                
            # Get price and supply
            price_data = await self.get_price(token_address)
            if price_data.get("error"):
                logger.error(f"Error getting price for market cap: {price_data['error']}")
                return {
                    "market_cap": 0,
                    "error": f"Price error: {price_data['error']}"
                }
                
            try:
                supply_data = await self.shyft.get_token_supply(token_address)
                if supply_data.get("error"):
                    logger.warning(f"Shyft supply fetch failed: {supply_data['error']}")
                    supply_data = {"total_supply": 0, "error": None}
            except Exception as e:
                logger.warning(f"Shyft supply fetch failed: {str(e)}")
                supply_data = {"total_supply": 0, "error": str(e)}
            
            return {
                "market_cap": price_data["price"] * supply_data["total_supply"],
                "error": None if not supply_data.get("error") else f"Supply error: {supply_data['error']}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating market cap: {str(e)}")
            return {
                "market_cap": 0,
                "error": str(e)
            }
            
    async def get_volume(self, token_address: str) -> Dict:
        """Get token volume"""
        try:
            if self.use_mock:
                return get_mock_volume(token_address)
                
            try:
                volume_data = await self.bitquery.get_token_volume(token_address)
                if not volume_data.get("error"):
                    return volume_data
                logger.warning(f"Bitquery volume fetch failed: {volume_data['error']}")
            except Exception as e:
                logger.warning(f"Bitquery volume fetch failed: {str(e)}")
            
            # If Bitquery fails, try getting volume from price APIs
            try:
                birdeye_data = await self.birdeye.get_token_price(token_address)
                if not birdeye_data.get("error") and "volume_24h" in birdeye_data:
                    return {
                        "volume_24h": birdeye_data["volume_24h"],
                        "error": None
                    }
            except Exception as e:
                logger.warning(f"Birdeye volume fetch failed: {str(e)}")
            
            # Return zero volume if all sources fail
            return {
                "volume_24h": 0,
                "error": "Failed to fetch volume from all sources"
            }
            
        except Exception as e:
            logger.error(f"Error getting token volume: {str(e)}")
            return {
                "volume_24h": 0,
                "error": str(e)
            }

    async def analyze_market(self, token_address: str) -> Dict:
        """Analyze market data for a token"""
        try:
            if self.use_mock:
                price_data = get_mock_price(token_address)
                volume_data = get_mock_volume(token_address)
                return {
                    "price": price_data["price"],
                    "price_change_24h": price_data["price_change_24h"],
                    "volume_24h": volume_data["volume_24h"],
                    "market_cap": price_data["price"] * 1000000000,  # Mock supply
                    "error": None
                }
                
            # Get price data
            price_data = await self.get_price(token_address)
            if price_data.get("error"):
                return {
                    "price": 0,
                    "price_change_24h": 0,
                    "volume_24h": 0,
                    "market_cap": 0,
                    "error": f"Price error: {price_data['error']}"
                }
                
            # Get market cap
            market_data = await self.get_market_cap(token_address)
            if market_data.get("error"):
                logger.warning(f"Market cap fetch failed: {market_data['error']}")
                
            # Get volume
            volume_data = await self.get_volume(token_address)
            if volume_data.get("error"):
                logger.warning(f"Volume fetch failed: {volume_data['error']}")
                
            return {
                "price": price_data["price"],
                "price_change_24h": price_data.get("price_change_24h", 0),
                "volume_24h": volume_data.get("volume_24h", 0),
                "market_cap": market_data.get("market_cap", 0),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market data: {str(e)}")
            return {
                "price": 0,
                "price_change_24h": 0,
                "volume_24h": 0,
                "market_cap": 0,
                "error": str(e)
            }
