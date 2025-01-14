"""Token holder analysis module"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..utils.validation import validate_solana_address
from ..test.mock_data import get_mock_holders, should_use_mock_data
from ..events.event_manager import event_manager

logger = logging.getLogger(__name__)

class HolderAnalyzer:
    """Analyzes token holder patterns and distribution"""
    def __init__(self):
        self.use_mock = should_use_mock_data()
        self.holder_cache = {}
        self.logger = logging.getLogger(__name__)
        self.is_running = False

    def _get_cached_analysis(self, token_address: str) -> Optional[Dict]:
        """Get cached holder analysis if available"""
        if token_address not in self.holder_cache:
            return None
            
        cached = self.holder_cache[token_address]
        if datetime.now() - cached["timestamp"] > timedelta(hours=1):
            del self.holder_cache[token_address]
            return None
            
        return cached["data"]

    async def start(self) -> None:
        """Start the analyzer"""
        self.is_running = True

    async def shutdown(self) -> None:
        """Shutdown the analyzer"""
        self.is_running = False

    async def analyze_holders(self, token_address: str) -> Dict:
        """Analyze token holders"""
        try:
            # Check cache first
            cached = self._get_cached_analysis(token_address)
            if cached:
                return cached

            # Validate address
            if not validate_solana_address(token_address):
                raise ValueError(f"Invalid Solana address: {token_address}")

            # Get holder data
            if self.use_mock:
                holders = get_mock_holders(token_address)
            else:
                # TODO: Implement real holder data fetching
                holders = []

            # Calculate distribution metrics
            total_supply = sum(holder["balance"] for holder in holders)
            sorted_holders = sorted(holders, key=lambda x: x["balance"], reverse=True)

            # Calculate concentration metrics
            top_10_holders = sorted_holders[:10] if len(sorted_holders) >= 10 else sorted_holders
            top_10_concentration = sum(h["balance"] for h in top_10_holders) / total_supply if total_supply > 0 else 0

            # Calculate distribution metrics
            distribution = {
                "total_holders": len(holders),
                "total_supply": total_supply,
                "concentration_score": top_10_concentration,
                "top_holders": [
                    {
                        "address": h["address"],
                        "balance": h["balance"],
                        "percentage": (h["balance"] / total_supply * 100) if total_supply > 0 else 0
                    }
                    for h in top_10_holders
                ]
            }

            # Calculate risk factors
            risk_factors = {
                "high_concentration": top_10_concentration > 0.5,
                "low_holder_count": len(holders) < 100,
                "uneven_distribution": top_10_concentration > 0.8
            }

            analysis = {
                "token_address": token_address,
                "timestamp": datetime.now().isoformat(),
                "distribution": distribution,
                "risk_factors": risk_factors
            }

            # Cache results
            self.holder_cache[token_address] = {
                "data": analysis,
                "timestamp": datetime.now()
            }

            # Emit analysis complete event
            await event_manager.emit("holder_analysis_complete", analysis)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing holders for {token_address}: {str(e)}")
            raise
