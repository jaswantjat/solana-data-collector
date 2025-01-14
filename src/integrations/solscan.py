import aiohttp
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

from ..error_handling.api_errors import (
    APIError,
    handle_api_error,
    should_retry
)
from ..test.mock_data import (
    get_mock_holders,
    get_mock_events,
    get_mock_deployer,
    should_use_mock_data
)

logger = logging.getLogger(__name__)

class SolscanAPI:
    """Solscan API integration"""
    
    def __init__(self):
        """Initialize Solscan API"""
        self.api_key = os.getenv("SOLSCAN_API_KEY")
        self.base_url = "https://public-api.solscan.io"
        self.session = None
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY_MS", "1000")) / 1000
        self.use_mock = should_use_mock_data()
        
    async def initialize(self):
        """Initialize Solscan API session"""
        if not self.session:
            connector = aiohttp.TCPConnector(
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=15)
            )
            
    async def close(self):
        """Close the API session"""
        if self.session:
            try:
                await self.session.close()
                await asyncio.sleep(0.1)  # Give time for the session to close
            except Exception as e:
                logger.error(f"Error closing Solscan session: {str(e)}")
            finally:
                self.session = None
            
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict:
        """Make an API request with retries and error handling"""
        if not self.session:
            await self.initialize()
            
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Accept": "application/json"
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                try:
                    # Check if response is JSON
                    content_type = response.headers.get("content-type", "")
                    if "application/json" not in content_type.lower():
                        logger.error(f"Invalid content type from Solscan: {content_type}")
                        return {"success": False, "error": "invalid_content_type"}
                        
                    data = await response.json()
                except Exception as e:
                    logger.error(f"Error parsing Solscan response: {str(e)}")
                    return {"success": False, "error": "invalid_response"}
                    
                if response.status != 200:
                    error = handle_api_error(
                        Exception(str(data.get("message", "Unknown error"))),
                        "Solscan",
                        endpoint,
                        response.status,
                        data
                    )
                    
                    if should_retry(error, retry_count, self.max_retries):
                        await asyncio.sleep(1)  # Add delay between retries
                        return await self._make_request(
                            endpoint,
                            params,
                            retry_count + 1
                        )
                    return {"success": False, "error": str(error)}
                    
                return {"success": True, "data": data}
                
        except Exception as e:
            error = handle_api_error(e, "Solscan", endpoint)
            if should_retry(error, retry_count, self.max_retries):
                await asyncio.sleep(1)  # Add delay between retries
                return await self._make_request(
                    endpoint,
                    params,
                    retry_count + 1
                )
            return {"success": False, "error": str(error)}
            
    async def get_token_holders(self, token_address: str) -> List[Dict]:
        """Get token holders"""
        if self.use_mock:
            return get_mock_holders(token_address)
            
        try:
            result = await self._make_request(
                f"token/holders/{token_address}"
            )
            
            if not result.get("success"):
                logger.error(f"Error fetching token holders from Solscan: {result.get('error')}")
                return []
                
            holders = result.get("data", {}).get("holders", [])
            return [
                {
                    "address": holder.get("owner"),
                    "amount": float(holder.get("amount", 0))
                }
                for holder in holders
            ]
            
        except Exception as e:
            logger.error(f"Error getting token holders: {str(e)}")
            return []
            
    async def get_token_events(self, token_address: str, days: int = 30) -> List[Dict]:
        """Get token events"""
        if self.use_mock:
            return get_mock_events(token_address)
            
        try:
            result = await self._make_request(
                f"token/transactions/{token_address}",
                {"limit": 100}  # Adjust as needed
            )
            
            if not result.get("success"):
                logger.error(f"Error fetching token events from Solscan: {result.get('error')}")
                return []
                
            transactions = result.get("data", {}).get("transactions", [])
            return [
                {
                    "signature": tx.get("signature"),
                    "timestamp": tx.get("blockTime"),
                    "type": "TRANSFER",  # Solscan doesn't differentiate types
                    "amount": float(tx.get("amount", 0)),
                    "from_address": tx.get("src"),
                    "to_address": tx.get("dst")
                }
                for tx in transactions
                if datetime.fromtimestamp(tx.get("blockTime", 0)) > datetime.now() - timedelta(days=days)
            ]
            
        except Exception as e:
            logger.error(f"Error getting token events: {str(e)}")
            return []
            
    async def get_token_deployer(self, token_address: str) -> Optional[str]:
        """Get token deployer"""
        if self.use_mock:
            return get_mock_deployer(token_address)
            
        try:
            result = await self._make_request(
                f"token/meta/{token_address}"
            )
            
            if not result.get("success"):
                logger.error(f"Error fetching token deployer from Solscan: {result.get('error')}")
                return None
                
            return result.get("data", {}).get("mintAuthority")
            
        except Exception as e:
            logger.error(f"Error getting token deployer: {str(e)}")
            return None
