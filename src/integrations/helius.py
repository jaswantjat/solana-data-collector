import aiohttp
import logging
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta
import json
import asyncio

from ..error_handling.api_errors import (
    APIError,
    APIKeyError,
    handle_api_error,
    should_retry
)
from .base_api import BaseAPI, APIConfig
from ..test.mock_data import (
    get_mock_holders,
    get_mock_transactions,
    get_mock_deployer,
    should_use_mock_data
)

logger = logging.getLogger(__name__)

class HeliusAPI(BaseAPI):
    """Helius API integration"""
    
    def __init__(self):
        """Initialize Helius API"""
        api_key = os.getenv("HELIUS_API_KEY")
        if not api_key:
            raise APIKeyError("Helius")
            
        config = APIConfig(
            api_key=api_key,
            base_url="https://api.helius.xyz/v0",
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY_MS", "1000")) / 1000,
            timeout={"total": 15},
            rate_limit={"default": 10}
        )
        super().__init__("helius", config)
        self.use_mock = should_use_mock_data()
        
    async def get_token_holders(self, token_address: str) -> List[Dict]:
        """Get token holders for a given token"""
        if self.use_mock:
            return get_mock_holders(token_address)
            
        endpoint = f"/token-holders/{token_address}"
        return await self._make_request("GET", endpoint)
        
    async def get_token_events(self, token_address: str, start_time: Optional[datetime] = None) -> List[Dict]:
        """Get token events for a given token"""
        if self.use_mock:
            return get_mock_transactions(token_address)
            
        params = {"token": token_address}
        if start_time:
            params["since"] = (start_time - timedelta(days=30)).isoformat()
            
        endpoint = "/token-events"
        return await self._make_request("GET", endpoint, params=params)
        
    async def get_token_deployer(self, token_address: str) -> Optional[str]:
        """Get token deployer"""
        if self.use_mock:
            return get_mock_deployer(token_address)
            
        endpoint = f"/token-metadata/{token_address}"
        result = await self._make_request("GET", endpoint)
        return result.get("deployer")
        
    async def get_token_transactions(self, token_address: str, days: int = 30) -> List[Dict]:
        """Get token transactions within a time range"""
        try:
            result = await self.get_token_events(token_address, start_time=datetime.now() - timedelta(days=days))
            events = result.get("data", [])
            if not events:
                return []
                
            transactions = []
            for event in events:
                try:
                    tx = {
                        "signature": event.get("signature"),
                        "timestamp": event.get("timestamp"),
                        "type": event.get("type"),
                        "amount": float(event.get("amount", 0)),
                        "from_address": event.get("source"),
                        "to_address": event.get("destination"),
                        "token_address": token_address
                    }
                    
                    # Add swap-specific fields
                    if event.get("type") == "SWAP":
                        tx.update({
                            "swap_from_amount": float(event.get("swapFromAmount", 0)),
                            "swap_to_amount": float(event.get("swapToAmount", 0)),
                            "swap_from_mint": event.get("swapFromMint"),
                            "swap_to_mint": event.get("swapToMint")
                        })
                        
                    transactions.append(tx)
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing transaction data: {str(e)}")
                    continue
                    
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting token transactions: {str(e)}")
            return []
            
    async def _get_solscan_holders(self, token_address: str) -> List[Dict]:
        """Get token holders from Solscan"""
        try:
            solscan = SolscanAPI()
            await solscan.initialize()
            try:
                return await solscan.get_token_holders(token_address)
            finally:
                await solscan.close()
        except Exception as e:
            logger.error(f"Error in Solscan fallback for holders: {str(e)}")
            return []
            
    async def _get_solscan_events(self, token_address: str, days: int = 30) -> List[Dict]:
        """Get token events from Solscan"""
        try:
            solscan = SolscanAPI()
            await solscan.initialize()
            try:
                return await solscan.get_token_events(token_address, days)
            finally:
                await solscan.close()
        except Exception as e:
            logger.error(f"Error in Solscan fallback for events: {str(e)}")
            return []
            
    async def _get_solscan_deployer(self, token_address: str) -> Optional[str]:
        """Get token deployer from Solscan"""
        try:
            solscan = SolscanAPI()
            await solscan.initialize()
            try:
                return await solscan.get_token_deployer(token_address)
            finally:
                await solscan.close()
        except Exception as e:
            logger.error(f"Error in Solscan fallback for deployer: {str(e)}")
            return None
