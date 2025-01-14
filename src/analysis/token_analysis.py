"""Token analysis module"""
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from ..utils.validation import validate_solana_address
from ..test.mock_data import get_mock_token, should_use_mock_data
from ..events.event_manager import event_manager

logger = logging.getLogger(__name__)

class TokenAnalyzer:
    """Analyzes token metrics and patterns"""
    def __init__(self):
        self.use_mock = should_use_mock_data()
        self.token_cache = {}
        self.logger = logging.getLogger(__name__)
        self.is_running = False

    def _get_cached_analysis(self, token_address: str) -> Optional[Dict]:
        """Get cached token analysis if available"""
        if token_address not in self.token_cache:
            return None
            
        cached = self.token_cache[token_address]
        if datetime.now() - cached["timestamp"] > timedelta(hours=1):
            del self.token_cache[token_address]
            return None
            
        return cached["data"]

    async def start(self) -> None:
        """Start the analyzer"""
        self.is_running = True

    async def shutdown(self) -> None:
        """Shutdown the analyzer"""
        self.is_running = False
        await event_manager.emit("token_analyzer_shutdown", {
            "timestamp": datetime.now().isoformat()
        })

    async def analyze_token(self, token_data: Dict) -> Dict:
        """Analyze a token's metrics and patterns"""
        try:
            token_address = token_data["address"]

            # Check cache first
            cached = self._get_cached_analysis(token_address)
            if cached:
                await event_manager.emit("token_analysis_complete", cached)
                return cached

            # Validate address
            if not validate_solana_address(token_address):
                raise ValueError(f"Invalid Solana address: {token_address}")

            # Get token data
            if self.use_mock:
                token = get_mock_token(token_address)
            else:
                token = token_data

            # Calculate risk score
            risk_score = self._calculate_risk_score(token)

            analysis = {
                "token_address": token_address,
                "name": token.get("name", "Unknown"),
                "symbol": token.get("symbol", "???"),
                "metrics": {
                    "holder_concentration": token.get("holder_concentration", 0.0),
                    "price_volatility": token.get("price_volatility", 0.0),
                    "volume_change": token.get("volume_change", 0.0),
                    "risk_score": risk_score
                },
                "timestamp": datetime.now().isoformat()
            }

            # Cache results
            self.token_cache[token_address] = {
                "data": analysis,
                "timestamp": datetime.now()
            }

            # Emit analysis complete event
            await event_manager.emit("token_analysis_complete", analysis)

            # Check for suspicious activity
            if risk_score > 0.7:
                await event_manager.emit("suspicious_activity", {
                    "token_address": token_address,
                    "activity_type": "high_risk_score",
                    "risk_level": "high",
                    "details": {
                        "risk_score": risk_score,
                        "metrics": analysis["metrics"]
                    },
                    "timestamp": datetime.now().isoformat()
                })

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing token {token_address}: {str(e)}")
            raise

    def _calculate_risk_score(self, token_data: Dict) -> float:
        """Calculate risk score based on token metrics"""
        try:
            # Get metrics with defaults
            holder_concentration = float(token_data.get("holder_concentration", 0.0))
            price_volatility = float(token_data.get("price_volatility", 0.0))
            volume_change = float(token_data.get("volume_change", 0.0))
            
            # Calculate weighted score
            weights = {
                "holder_concentration": 0.4,
                "price_volatility": 0.3,
                "volume_change": 0.3
            }
            
            risk_score = (
                holder_concentration * weights["holder_concentration"] +
                price_volatility * weights["price_volatility"] +
                volume_change * weights["volume_change"]
            )
            
            return min(max(risk_score, 0.0), 1.0)  # Clamp between 0 and 1
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {str(e)}")
            return 0.0

    async def analyze_price_movement(self, token_address: str, price_data: Dict) -> Dict:
        """Analyze token price movements"""
        try:
            # Get token data for context
            if self.use_mock:
                token_data = get_mock_token(token_address)
            else:
                # TODO: Implement real token data fetching
                token_data = {}

            # Calculate price metrics
            old_price = price_data.get("old_price", 0.0)
            new_price = price_data.get("new_price", 0.0)
            price_change = (new_price - old_price) / old_price if old_price > 0 else 0.0

            analysis = {
                "token_address": token_address,
                "token_name": token_data.get("name", "Unknown"),
                "token_symbol": token_data.get("symbol", "???"),
                "timestamp": datetime.now().isoformat(),
                "price_data": price_data,
                "metrics": {
                    "price_change": price_change,
                    "volatility": abs(price_change),
                    "trend": "up" if price_change > 0 else "down" if price_change < 0 else "stable"
                }
            }

            # Emit price analysis complete event
            await event_manager.emit("price_analysis_complete", analysis)

            # Generate alert if price change is significant
            if abs(price_change) > 0.1:  # 10% change
                alert_data = {
                    "token_address": token_address,
                    "alert_type": "price_change",
                    "severity": "high" if abs(price_change) > 0.5 else "medium" if abs(price_change) > 0.2 else "low",
                    "details": {
                        "old_price": old_price,
                        "new_price": new_price,
                        "percent_change": price_change * 100
                    },
                    "timestamp": datetime.now().isoformat()
                }
                await event_manager.emit("alert_generated", alert_data)

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing price movement for {token_address}: {str(e)}")
            raise
