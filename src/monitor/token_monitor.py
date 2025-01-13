import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI
from ..analysis.deployer_analysis import DeployerAnalysis

logger = logging.getLogger(__name__)

class TokenMonitor:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.deployer_analysis = DeployerAnalysis()
        self.pump_fun_program = "PFv6UgNmGt3tECGZ8HyLTHx5fXgZCq5tYuqEyJmTXgw"
        self.min_market_cap = 30000  # $30k threshold
        self.recent_tokens = []  # Store recent tokens in memory

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
                    
        except Exception as e:
            logger.error(f"Error monitoring new tokens: {str(e)}")

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
                    
                    updated_tokens.append(token)
            
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
                # Get holder data
                holder_data = await self.helius.get_token_holders(token_address)
                holder_count = len(holder_data)
                whale_count = sum(1 for h in holder_data if float(h.get("amount", 0)) > supply_info.get("supply", 0) * 0.01)
                
                # Analyze supply distribution
                distribution_score = await self._analyze_supply_distribution(token_address)
                
                # Verify contract
                contract_score = await self._verify_contract(token_address)
                
                # Calculate deployer score
                deployer_score = await self._calculate_deployer_score(token_address)
                
                # Get volume and mentions
                volume_data = await self.jupiter.get_token_liquidity(token_address)
                mentions = await self._get_social_mentions(token_address)
                
                # Calculate top holder win rate
                win_rate = await self._calculate_top_holder_win_rate(token_address)
                
                # Calculate analysis score
                analysis_score = (distribution_score * 0.3 + 
                                contract_score * 0.3 + 
                                deployer_score * 0.2 +
                                (mentions / 1000) * 0.1 +
                                win_rate * 0.1)
                
                # Calculate age in days
                created_at = metadata.get("onChainMetadata", {}).get("metadata", {}).get("updateAuthority", {}).get("createdAt", "")
                age_days = (datetime.now() - datetime.fromisoformat(created_at)) if created_at else 0
                
                # Create token info
                token_info = {
                    "address": token_address,
                    "name": metadata.get("onChainMetadata", {}).get("metadata", {}).get("data", {}).get("name", "Unknown"),
                    "symbol": metadata.get("onChainMetadata", {}).get("metadata", {}).get("data", {}).get("symbol", "???"),
                    "market_cap": market_cap,
                    "price": price,
                    "price_change_24h": price_change,
                    "distribution_score": distribution_score,
                    "contract_score": contract_score,
                    "deployer_score": deployer_score,
                    "holder_count": holder_count,
                    "whale_count": whale_count,
                    "mentions": mentions,
                    "top_holder_win_rate": win_rate,
                    "analysis_score": analysis_score,
                    "age_days": age_days.days if isinstance(age_days, timedelta) else 0,
                    "supply": supply_info.get("supply", 0),
                    "decimals": supply_info.get("decimals", 0),
                    "volume": volume_data.get("volume24h", 0),
                    "timestamp": datetime.now().isoformat(),
                    "volume_history": await self._get_volume_history(token_address)
                }
                
                return token_info

        except Exception as e:
            logger.error(f"Error processing token {token_address}: {str(e)}")
            return None

    def _extract_token_address(self, transaction: Dict) -> Optional[str]:
        """Extract token mint address from transaction"""
        try:
            # Look for token creation in transaction
            for instruction in transaction.get("instructions", []):
                if instruction.get("programId") == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                    if instruction.get("name") == "initializeMint":
                        return instruction.get("params", {}).get("mint")
            return None
        except Exception as e:
            logger.error(f"Error extracting token address: {str(e)}")
            return None

    def _calculate_market_cap(self, supply: str, decimals: int, price: float) -> float:
        """Calculate market cap from supply and price"""
        try:
            supply_float = float(supply) / (10 ** decimals)
            return supply_float * price
        except Exception as e:
            logger.error(f"Error calculating market cap: {str(e)}")
            return 0

    async def _analyze_supply_distribution(self, token_address: str) -> float:
        """Analyze token supply distribution"""
        try:
            # Get token transfers to analyze holder patterns
            transfers = await self.helius.get_token_transfers(token_address)
            
            if not transfers:
                return 0

            # Create holder map from transfers
            holders = {}
            for transfer in transfers:
                source = transfer.get("sourceAddress")
                destination = transfer.get("destinationAddress")
                amount = float(transfer.get("amount", 0))
                
                if source:
                    holders[source] = holders.get(source, 0) - amount
                if destination:
                    holders[destination] = holders.get(destination, 0) + amount

            # Remove zero balances
            holders = {k: v for k, v in holders.items() if v > 0}
            
            if not holders:
                return 0

            # Calculate Gini coefficient
            total_supply = sum(holders.values())
            if total_supply == 0:
                return 0

            # Sort holders by amount
            sorted_holders = sorted(holders.items(), key=lambda x: x[1])
            
            # Calculate Gini coefficient
            n = len(holders)
            coefficient = sum((2 * i - n - 1) * amount 
                            for i, (_, amount) in enumerate(sorted_holders))
            coefficient = coefficient / (n * total_supply)
            
            # Convert to score (0-100, where 100 is perfect distribution)
            return max(0, min(100, (1 - coefficient) * 100))

        except Exception as e:
            logger.error(f"Error analyzing supply distribution: {str(e)}")
            return 0

    async def _verify_contract(self, token_address: str) -> float:
        """Verify token contract for potential risks"""
        try:
            metadata = await self.helius.get_token_metadata(token_address)
            if not metadata:
                return 0

            supply_info = metadata.get("onChainAccountInfo", {}).get("accountInfo", {}).get("data", {}).get("parsed", {}).get("info", {})
            
            score = 100  # Start with perfect score
            
            # Check if mint authority exists (can mint more tokens)
            if supply_info.get("mintAuthority"):
                score -= 30
            
            # Check if freeze authority exists (can freeze transfers)
            if supply_info.get("freezeAuthority"):
                score -= 30
            
            # Check if metadata exists
            if not metadata.get("onChainMetadata", {}).get("metadata", {}).get("data", {}).get("name"):
                score -= 20
            
            # Check if symbol exists
            if not metadata.get("onChainMetadata", {}).get("metadata", {}).get("data", {}).get("symbol"):
                score -= 20
            
            return max(0, score)

        except Exception as e:
            logger.error(f"Error verifying contract: {str(e)}")
            return 0

    async def _calculate_deployer_score(self, token_address: str) -> float:
        """Calculate deployer trustworthiness score"""
        try:
            # Get deployer address
            deployer = await self.helius.get_token_deployer(token_address)
            if not deployer:
                return 0

            # Check if deployer is blacklisted
            if self.deployer_analysis.is_blacklisted(deployer):
                return 0

            # Analyze deployer
            analysis = await self.deployer_analysis.analyze_deployer(deployer)
            
            # Calculate score based on analysis
            if analysis["risk_level"] == "Low":
                return min(100, analysis["success_rate"])
            elif analysis["risk_level"] == "Medium":
                return min(70, analysis["success_rate"])
            else:
                return min(40, analysis["success_rate"])
            
        except Exception as e:
            logger.error(f"Error calculating deployer score: {str(e)}")
            return 0

    async def _get_social_mentions(self, token_address: str) -> int:
        """Get number of social media mentions"""
        try:
            # This would integrate with Twitter/Discord APIs
            # For now, return random number for demo
            return random.randint(100, 15000)
        except Exception:
            return 0

    async def _calculate_top_holder_win_rate(self, token_address: str) -> float:
        """Calculate win rate of top holders"""
        try:
            # Get top holders
            holders = await self.helius.get_token_holders(token_address)
            if not holders:
                return 0
                
            # Get their transaction history
            win_count = 0
            total_trades = 0
            
            for holder in holders[:10]:  # Top 10 holders
                trades = await self.helius.get_wallet_history(holder.get("owner"))
                if trades:
                    wins = sum(1 for t in trades if t.get("profit", 0) > 0)
                    win_count += wins
                    total_trades += len(trades)
            
            return (win_count / total_trades * 100) if total_trades > 0 else 0
            
        except Exception:
            return 0

    async def _get_volume_history(self, token_address: str) -> List[Dict]:
        """Get historical volume data"""
        try:
            # Get 24h volume data in 2h intervals
            intervals = 12
            volume_history = []
            
            for i in range(intervals):
                timestamp = datetime.now() - timedelta(hours=2*i)
                volume = await self.jupiter.get_token_liquidity(token_address, timestamp)
                volume_history.append({
                    "timestamp": timestamp.isoformat(),
                    "volume": volume.get("volume", 0)
                })
            
            return volume_history
            
        except Exception:
            return []

    async def run(self):
        """Run the token monitor"""
        while True:
            await self.monitor_new_tokens()
            await asyncio.sleep(10)  # Check every 10 seconds
