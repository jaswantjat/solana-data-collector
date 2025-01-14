"""Token activity analysis module"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from ..utils.validation import validate_solana_address
from ..test.mock_data import get_mock_transactions, should_use_mock_data
from ..events.event_manager import event_manager

logger = logging.getLogger(__name__)

class ActivityAnalyzer:
    """Analyzes token trading activity and patterns"""
    def __init__(self):
        self.use_mock = should_use_mock_data()
        self.activity_cache = {}
        self.logger = logging.getLogger(__name__)
        self.is_running = False

        # Register event handlers
        event_manager.on("transaction_detected", self._handle_transaction)

    def _get_cached_analysis(self, token_address: str) -> Optional[Dict]:
        """Get cached activity analysis if available"""
        if token_address not in self.activity_cache:
            return None
            
        cached = self.activity_cache[token_address]
        if datetime.now() - cached["timestamp"] > timedelta(hours=1):
            del self.activity_cache[token_address]
            return None
            
        return cached["data"]

    async def start(self) -> None:
        """Start the analyzer"""
        self.is_running = True

    async def shutdown(self) -> None:
        """Shutdown the analyzer"""
        self.is_running = False

    async def _handle_transaction(self, event) -> None:
        """Handle new transaction event"""
        if not self.is_running:
            return

        try:
            tx_data = event.data
            token_address = tx_data["token_address"]

            # Analyze activity
            analysis = await self.analyze_activity(token_address)

            # Check for suspicious activity
            if any(analysis["risk_factors"].values()):
                await event_manager.emit("suspicious_activity", {
                    "token_address": token_address,
                    "activity_type": "high_risk_score",
                    "risk_level": "high",
                    "risk_factors": analysis["risk_factors"],
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            self.logger.error(f"Error handling transaction: {str(e)}")

    async def analyze_activity(self, token_address: str) -> Dict:
        """Analyze token activity"""
        try:
            # Check cache first
            cached = self._get_cached_analysis(token_address)
            if cached:
                return cached

            # Validate address
            if not validate_solana_address(token_address):
                raise ValueError(f"Invalid Solana address: {token_address}")

            # Get transaction data
            if self.use_mock:
                transactions = get_mock_transactions(token_address)
            else:
                # TODO: Implement real transaction data fetching
                transactions = []

            # Calculate activity metrics
            total_volume = sum(tx["amount"] for tx in transactions)
            unique_addresses = len(set(tx["from_address"] for tx in transactions) | 
                                set(tx.get("to_address", "") for tx in transactions))

            # Calculate time-based metrics
            timestamps = [datetime.fromisoformat(tx["timestamp"]) for tx in transactions]
            if timestamps:
                time_range = max(timestamps) - min(timestamps)
                avg_time_between = time_range.total_seconds() / len(transactions) if len(transactions) > 1 else 0
            else:
                avg_time_between = 0

            # Calculate transaction patterns
            large_txs = [tx for tx in transactions if tx["amount"] > total_volume * 0.1]
            repeated_addresses = [addr for addr in set(tx["from_address"] for tx in transactions)
                                if sum(1 for t in transactions if t["from_address"] == addr) > 3]

            activity_metrics = {
                "total_transactions": len(transactions),
                "total_volume": total_volume,
                "unique_addresses": unique_addresses,
                "avg_time_between_txs": avg_time_between,
                "large_transactions": len(large_txs),
                "repeated_addresses": len(repeated_addresses)
            }

            # Calculate risk factors
            risk_factors = {
                "high_volume": total_volume > 1000000,
                "frequent_large_txs": len(large_txs) > len(transactions) * 0.2,
                "suspicious_addresses": len(repeated_addresses) > 0
            }

            analysis = {
                "token_address": token_address,
                "timestamp": datetime.now().isoformat(),
                "metrics": activity_metrics,
                "risk_factors": risk_factors,
                "suspicious_transactions": [tx for tx in large_txs if tx["amount"] > total_volume * 0.2]
            }

            # Cache the analysis
            self.activity_cache[token_address] = {
                "timestamp": datetime.now(),
                "data": analysis
            }

            # Emit analysis complete event
            await event_manager.emit("activity_analysis_complete", analysis)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing activity for {token_address}: {str(e)}")
            raise
