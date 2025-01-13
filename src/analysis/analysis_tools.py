import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import json
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI
from ..database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class AnalysisTools:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.db = DatabaseManager()
        
    async def screen_tokens(self, criteria: Dict) -> List[Dict]:
        """Screen tokens based on specified criteria"""
        try:
            filtered_tokens = []
            all_tokens = self.db.token_db["tokens"]
            
            for address, token in all_tokens.items():
                if self._matches_criteria(address, token, criteria):
                    token_data = await self._get_token_details(address)
                    if token_data:
                        filtered_tokens.append(token_data)
            
            return sorted(filtered_tokens, 
                        key=lambda x: x.get("score", 0),
                        reverse=True)
                        
        except Exception as e:
            logger.error(f"Error screening tokens: {str(e)}")
            return []
            
    def _matches_criteria(self, address: str, token: Dict, criteria: Dict) -> bool:
        """Check if token matches screening criteria"""
        try:
            # Get all relevant data
            performance = self.db.token_db["performance"].get(address, {})
            risk_score = self.db.token_db["risk_scores"].get(address, {})
            price_history = self.db.token_db["price_history"].get(address, {})
            
            # Check each criterion
            for key, value in criteria.items():
                if key == "min_market_cap" and performance.get("market_cap", 0) < value:
                    return False
                elif key == "min_holders" and performance.get("holders", 0) < value:
                    return False
                elif key == "max_risk_score" and risk_score.get("current_score", 1) > value:
                    return False
                elif key == "min_age_days":
                    launch_date = datetime.fromisoformat(token.get("added_at", datetime.now().isoformat()))
                    age_days = (datetime.now() - launch_date).days
                    if age_days < value:
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Error matching criteria: {str(e)}")
            return False

    async def analyze_wallet(self, address: str) -> Dict:
        """Comprehensive wallet analysis"""
        try:
            # Get wallet status
            status = self.db.get_wallet_status(address)
            
            # Get transaction history
            transactions = await self.helius.get_wallet_transactions(address)
            
            # Analyze patterns
            patterns = self._analyze_wallet_patterns(transactions)
            
            # Calculate metrics
            metrics = self._calculate_wallet_metrics(transactions)
            
            # Get token holdings
            holdings = await self._get_wallet_holdings(address)
            
            return {
                "address": address,
                "status": status,
                "patterns": patterns,
                "metrics": metrics,
                "holdings": holdings,
                "risk_score": self._calculate_wallet_risk_score(status, patterns, metrics)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing wallet: {str(e)}")
            return {}

    def _analyze_wallet_patterns(self, transactions: List[Dict]) -> Dict:
        """Analyze wallet transaction patterns"""
        try:
            patterns = {
                "trading_frequency": self._calculate_trading_frequency(transactions),
                "preferred_tokens": self._get_preferred_tokens(transactions),
                "typical_position_size": self._calculate_position_size(transactions),
                "holding_period": self._calculate_holding_period(transactions),
                "risk_profile": self._determine_risk_profile(transactions)
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing patterns: {str(e)}")
            return {}

    def _calculate_wallet_metrics(self, transactions: List[Dict]) -> Dict:
        """Calculate wallet performance metrics"""
        try:
            if not transactions:
                return {}
                
            # Calculate basic metrics
            total_volume = sum(float(tx.get("amount", 0)) for tx in transactions)
            win_count = sum(1 for tx in transactions if float(tx.get("profit", 0)) > 0)
            loss_count = sum(1 for tx in transactions if float(tx.get("profit", 0)) < 0)
            
            metrics = {
                "total_transactions": len(transactions),
                "total_volume": total_volume,
                "win_rate": win_count / len(transactions) if transactions else 0,
                "average_position_size": total_volume / len(transactions) if transactions else 0,
                "activity_score": self._calculate_activity_score(transactions)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}

    async def explore_transactions(self, query: Dict) -> List[Dict]:
        """Explore transactions based on query parameters"""
        try:
            transactions = []
            
            # Get transactions based on query type
            if query.get("token"):
                transactions = await self.helius.get_token_transactions(query["token"])
            elif query.get("wallet"):
                transactions = await self.helius.get_wallet_transactions(query["wallet"])
            elif query.get("pattern"):
                transactions = await self._find_pattern_matches(query["pattern"])
                
            # Apply filters
            filtered = self._filter_transactions(transactions, query.get("filters", {}))
            
            # Sort results
            sorted_txs = self._sort_transactions(filtered, query.get("sort_by", "timestamp"))
            
            return sorted_txs
            
        except Exception as e:
            logger.error(f"Error exploring transactions: {str(e)}")
            return []

    async def recognize_patterns(self, data: Union[List[Dict], str], pattern_type: str) -> List[Dict]:
        """Recognize patterns in transaction or price data"""
        try:
            if isinstance(data, str):
                # If data is a token address, get its transactions
                data = await self.helius.get_token_transactions(data)
                
            patterns = []
            
            if pattern_type == "price":
                patterns.extend(self._find_price_patterns(data))
            elif pattern_type == "volume":
                patterns.extend(self._find_volume_patterns(data))
            elif pattern_type == "wallet":
                patterns.extend(self._find_wallet_patterns(data))
            elif pattern_type == "trading":
                patterns.extend(self._find_trading_patterns(data))
                
            return sorted(patterns, key=lambda x: x.get("confidence", 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Error recognizing patterns: {str(e)}")
            return []

    async def calculate_risk_score(self, target: Union[str, Dict], target_type: str) -> Dict:
        """Calculate comprehensive risk score"""
        try:
            if isinstance(target, str):
                if target_type == "token":
                    target = await self._get_token_details(target)
                elif target_type == "wallet":
                    target = await self.analyze_wallet(target)
                    
            if not target:
                return {"score": 1.0, "factors": {}}
                
            risk_factors = {}
            
            if target_type == "token":
                risk_factors = await self._calculate_token_risk_factors(target)
            elif target_type == "wallet":
                risk_factors = self._calculate_wallet_risk_factors(target)
                
            # Calculate weighted risk score
            total_weight = sum(factor["weight"] for factor in risk_factors.values())
            weighted_score = sum(
                factor["score"] * factor["weight"]
                for factor in risk_factors.values()
            ) / total_weight if total_weight > 0 else 1.0
            
            return {
                "score": min(1.0, weighted_score),
                "factors": risk_factors
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return {"score": 1.0, "factors": {}}

    async def _get_token_details(self, address: str) -> Optional[Dict]:
        """Get comprehensive token details"""
        try:
            token = self.db.token_db["tokens"].get(address)
            if not token:
                return None
                
            performance = self.db.token_db["performance"].get(address, {})
            risk_score = self.db.token_db["risk_scores"].get(address, {})
            price_history = self.db.token_db["price_history"].get(address, {})
            
            return {
                "address": address,
                "metadata": token.get("metadata", {}),
                "performance": performance.get("metrics", {}),
                "risk_score": risk_score.get("current_score", 1.0),
                "price_data": price_history.get("prices", [])[-100:],  # Last 100 price points
                "score": self._calculate_token_score(token, performance, risk_score)
            }
            
        except Exception as e:
            logger.error(f"Error getting token details: {str(e)}")
            return None

    def _calculate_token_score(self, token: Dict, performance: Dict, risk_score: Dict) -> float:
        """Calculate overall token score"""
        try:
            score = 0.0
            
            # Factor 1: Performance (40%)
            perf_metrics = performance.get("metrics", {})
            perf_score = (
                perf_metrics.get("price_change", 0) * 0.4 +
                perf_metrics.get("volume_change", 0) * 0.3 +
                perf_metrics.get("holder_change", 0) * 0.3
            )
            score += max(0, min(1, perf_score)) * 0.4
            
            # Factor 2: Risk (30%)
            risk = float(risk_score.get("current_score", 1.0))
            score += (1 - risk) * 0.3
            
            # Factor 3: Age and stability (30%)
            age_days = (datetime.now() - datetime.fromisoformat(token.get("added_at", datetime.now().isoformat()))).days
            age_score = min(1.0, age_days / 30)  # Cap at 30 days
            score += age_score * 0.3
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating token score: {str(e)}")
            return 0.0

    async def _get_wallet_holdings(self, address: str) -> List[Dict]:
        """Get wallet token holdings"""
        try:
            holdings = await self.helius.get_wallet_tokens(address)
            
            # Enrich with token data
            enriched = []
            for token in holdings:
                token_data = await self._get_token_details(token["mint"])
                if token_data:
                    enriched.append({
                        "token": token_data,
                        "balance": token["amount"],
                        "value_usd": float(token["amount"]) * float(token_data["performance"].get("price", 0))
                    })
                    
            return sorted(enriched, key=lambda x: x["value_usd"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting wallet holdings: {str(e)}")
            return []

    def _calculate_activity_score(self, transactions: List[Dict]) -> float:
        """Calculate wallet activity score"""
        try:
            if not transactions:
                return 0.0
                
            # Calculate daily activity
            daily_volume = defaultdict(float)
            for tx in transactions:
                date = datetime.fromisoformat(tx["timestamp"]).date().isoformat()
                daily_volume[date] += float(tx.get("amount", 0))
                
            # Calculate metrics
            avg_daily_volume = sum(daily_volume.values()) / len(daily_volume)
            active_days = len(daily_volume)
            total_days = (datetime.now().date() - min(datetime.fromisoformat(d).date() 
                        for d in daily_volume.keys())).days + 1
                        
            # Calculate score components
            volume_score = min(1.0, avg_daily_volume / 10000)  # Cap at $10k daily average
            activity_score = active_days / total_days if total_days > 0 else 0
            
            return (volume_score * 0.7 + activity_score * 0.3)
            
        except Exception as e:
            logger.error(f"Error calculating activity score: {str(e)}")
            return 0.0

    def _calculate_wallet_risk_score(self, status: Dict, patterns: Dict, metrics: Dict) -> float:
        """Calculate wallet risk score"""
        try:
            risk_score = 0.0
            
            # Factor 1: Status flags (40%)
            if status["is_scammer"] or status["blacklist_status"]["scammer"]:
                risk_score += 0.4
            elif status["is_sniper"] or status["is_insider"]:
                risk_score += 0.3
            elif not status["is_trusted"]:
                risk_score += 0.2
                
            # Factor 2: Trading patterns (30%)
            pattern_risk = patterns.get("risk_profile", {}).get("risk_level", 0.5)
            risk_score += pattern_risk * 0.3
            
            # Factor 3: Metrics (30%)
            metrics_risk = 0.0
            if metrics.get("win_rate", 0) < 0.4:
                metrics_risk += 0.15
            if metrics.get("average_position_size", 0) > 10000:  # High position sizes
                metrics_risk += 0.15
                
            risk_score += metrics_risk
            
            return min(1.0, risk_score)
            
        except Exception as e:
            logger.error(f"Error calculating wallet risk score: {str(e)}")
            return 1.0  # Maximum risk on error
