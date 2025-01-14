"""Token monitoring module for tracking new token launches and metrics"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI
from ..analysis.deployer_analysis import DeployerAnalyzer
from ..analysis.holder_analysis import HolderAnalyzer
from ..analysis.token_analysis import TokenAnalyzer
from ..events.event_manager import event_manager

logger = logging.getLogger(__name__)

class TokenMonitor:
    """Monitors token launches and metrics"""
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.deployer_analyzer = DeployerAnalyzer()
        self.holder_analyzer = HolderAnalyzer()
        self.token_analyzer = TokenAnalyzer()
        self.pump_fun_program = "PFv6UgNmGt3tECGZ8HyLTHx5fXgZCq5tYuqEyJmTXgw"
        self.min_market_cap = 30000  # $30k threshold
        self.recent_tokens = []  # Store recent tokens in memory
        self.is_running = False

    async def start(self):
        """Start monitoring"""
        if self.is_running:
            return

        self.is_running = True
        while self.is_running:
            try:
                await self.monitor_new_tokens()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry

    async def stop(self):
        """Stop monitoring"""
        self.is_running = False

    async def monitor_new_tokens(self):
        """Monitor pump.fun for new token launches"""
        try:
            # Get recent transactions from pump.fun program
            transactions = await self.helius.get_program_transactions(self.pump_fun_program)
            
            # Process each transaction to find new token launches
            for tx in transactions:
                token_address = self._extract_token_address(tx)
                if token_address:
                    token_info = await self._process_new_token(token_address)
                    if token_info:
                        # Add to recent tokens, maintain max 100 tokens
                        self.recent_tokens.append(token_info)
                        if len(self.recent_tokens) > 100:
                            self.recent_tokens.pop(0)
                        
                        # Emit new token event
                        await event_manager.emit("new_token_detected", token_info)
                    
        except Exception as e:
            logger.error(f"Error monitoring new tokens: {str(e)}")
            raise

    async def get_recent_tokens(self) -> List[Dict]:
        """Get list of recent tokens"""
        try:
            # Update data for existing tokens
            updated_tokens = []
            for token in self.recent_tokens:
                token_address = token.get("address")
                if token_address:
                    # Get latest price
                    price_data = await self.jupiter.get_token_price(token_address)
                    token["price"] = price_data.get("price", 0)
                    
                    # Get latest volume
                    liquidity_data = await self.jupiter.get_token_liquidity(token_address)
                    token["volume"] = liquidity_data.get("volume24h", 0)
                    
                    # Update market cap
                    token["market_cap"] = token["price"] * float(token.get("supply", 0))
                    
                    # Update token metrics
                    metrics = await self.token_analyzer.analyze_token(token_address)
                    token["metrics"] = metrics
                    
                    updated_tokens.append(token)
                    
                    # Emit token updated event
                    await event_manager.emit("token_updated", token)
            
            return sorted(updated_tokens, key=lambda x: x.get("market_cap", 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting recent tokens: {str(e)}")
            return []

    async def _process_new_token(self, token_address: str) -> Optional[Dict]:
        """Process a newly detected token"""
        try:
            # Get token metadata
            metadata = await self.helius.get_token_metadata(token_address)
            if not metadata:
                logger.warning(f"No metadata found for token {token_address}")
                return None

            # Get supply info
            supply_info = await self.helius.get_token_supply(token_address)
            
            # Calculate market cap
            price_data = await self.jupiter.get_token_price(token_address)
            price = price_data.get("price", 0)
            price_change = price_data.get("price_change_24h", 0)
            market_cap = self._calculate_market_cap(supply_info.get("supply", 0), 
                                                  supply_info.get("decimals", 0), 
                                                  price)

            # Check if meets threshold
            if market_cap >= self.min_market_cap:
                # Analyze token
                token_analysis = await self.token_analyzer.analyze_token(token_address)
                
                # Analyze holders
                holder_analysis = await self.holder_analyzer.analyze_holders(token_address)
                
                # Analyze deployer
                deployer_analysis = await self.deployer_analyzer.analyze_deployer(token_address)
                
                token_info = {
                    "address": token_address,
                    "name": metadata.get("name", "Unknown"),
                    "symbol": metadata.get("symbol", "Unknown"),
                    "decimals": supply_info.get("decimals", 0),
                    "supply": supply_info.get("supply", 0),
                    "price": price,
                    "price_change_24h": price_change,
                    "market_cap": market_cap,
                    "launch_time": datetime.now().isoformat(),
                    "token_analysis": token_analysis,
                    "holder_analysis": holder_analysis,
                    "deployer_analysis": deployer_analysis,
                    "metadata": metadata
                }
                
                return token_info
                
            return None
            
        except Exception as e:
            logger.error(f"Error processing new token {token_address}: {str(e)}")
            return None

    def _calculate_market_cap(self, supply: int, decimals: int, price: float) -> float:
        """Calculate market cap from supply and price"""
        try:
            actual_supply = float(supply) / (10 ** decimals)
            return actual_supply * price
        except Exception as e:
            logger.error(f"Error calculating market cap: {str(e)}")
            return 0.0

    def _extract_token_address(self, transaction: Dict) -> Optional[str]:
        """Extract token address from transaction data"""
        try:
            # Extract token address from transaction logs
            # This is a placeholder - actual implementation would depend on
            # the specific structure of pump.fun program transactions
            return transaction.get("token_address")
        except Exception as e:
            logger.error(f"Error extracting token address: {str(e)}")
            return None
