import logging
from typing import Dict, List, Optional
from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI

logger = logging.getLogger(__name__)

class SupplyAnalyzer:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        
    async def analyze_supply_distribution(self, token_address: str) -> Dict:
        """Analyze token supply distribution"""
        try:
            # Get all token holders
            holders = await self.helius.get_token_holders(token_address)
            
            # Sort holders by balance
            sorted_holders = sorted(holders, key=lambda x: float(x.get("amount", 0)), reverse=True)
            
            # Calculate total supply
            total_supply = sum(float(h.get("amount", 0)) for h in holders)
            
            # Analyze distribution
            whale_count = 0
            top_10_percent = 0
            unique_holders = len(holders)
            
            for holder in sorted_holders:
                balance = float(holder.get("amount", 0))
                percent = (balance / total_supply) * 100
                
                if percent > 8:
                    whale_count += 1
                    
            # Calculate top 10 holders percentage (excluding known addresses)
            top_10 = sorted_holders[:10]
            top_10_percent = sum(float(h.get("amount", 0)) for h in top_10) / total_supply * 100
            
            return {
                "total_supply": total_supply,
                "unique_holders": unique_holders,
                "whale_count": whale_count,
                "top_10_percent": top_10_percent,
                "distribution_score": self._calculate_distribution_score(
                    whale_count,
                    top_10_percent,
                    unique_holders
                ),
                "holders": [
                    {
                        "address": h.get("address"),
                        "balance": float(h.get("amount", 0)),
                        "percent": (float(h.get("amount", 0)) / total_supply) * 100
                    }
                    for h in sorted_holders[:30]  # Return top 30 holders
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing supply distribution: {str(e)}")
            return {}
            
    def _calculate_distribution_score(self, whale_count: int, top_10_percent: float, unique_holders: int) -> float:
        """Calculate supply distribution score"""
        try:
            # Penalize for too many whales
            whale_penalty = max(0, (whale_count - 2) * 20)
            
            # Penalize for high concentration in top 10
            concentration_penalty = max(0, (top_10_percent - 25) * 2)
            
            # Bonus for more unique holders
            holder_bonus = min(20, (unique_holders / 100))
            
            # Calculate final score (0-100)
            score = 100 - whale_penalty - concentration_penalty + holder_bonus
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculating distribution score: {str(e)}")
            return 0
            
    async def is_supply_suspicious(self, token_address: str) -> bool:
        """Check if token supply distribution is suspicious"""
        try:
            analysis = await self.analyze_supply_distribution(token_address)
            
            return (
                analysis.get("whale_count", 0) > 2 or
                analysis.get("top_10_percent", 0) > 25 or
                analysis.get("distribution_score", 0) < 50
            )
            
        except Exception as e:
            logger.error(f"Error checking suspicious supply: {str(e)}")
            return True  # Assume suspicious on error
