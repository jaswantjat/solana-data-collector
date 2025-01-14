"""Token deployer analysis module"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path
import time

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI
from ..events.event_manager import event_manager
from ..test.mock_data import get_mock_deployer, should_use_mock_data

logger = logging.getLogger(__name__)

class DeployerAnalyzer:
    """Analyzes token deployers and their history"""
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.blacklist_file = Path(__file__).parent.parent.parent / "data" / "blacklist.json"
        self.deployer_history_file = Path(__file__).parent.parent.parent / "data" / "deployer_history.json"
        self.use_mock = should_use_mock_data()
        self._load_data()

    def _load_data(self):
        """Load blacklist and deployer history from files"""
        try:
            if self.blacklist_file.exists():
                with open(self.blacklist_file, 'r') as f:
                    self.blacklist = json.load(f)
            else:
                self.blacklist = {"deployers": [], "tokens": []}
                self._save_blacklist()

            if self.deployer_history_file.exists():
                with open(self.deployer_history_file, 'r') as f:
                    self.deployer_history = json.load(f)
            else:
                self.deployer_history = {}
                self._save_history()
        except Exception as e:
            logger.error(f"Error loading data: {str(e)}")
            self.blacklist = {"deployers": [], "tokens": []}
            self.deployer_history = {}

    def _save_blacklist(self):
        """Save blacklist to file"""
        try:
            with open(self.blacklist_file, 'w') as f:
                json.dump(self.blacklist, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving blacklist: {str(e)}")

    def _save_history(self):
        """Save deployer history to file"""
        try:
            with open(self.deployer_history_file, 'w') as f:
                json.dump(self.deployer_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {str(e)}")
            
    async def initialize(self):
        """Initialize API connections"""
        if not self.use_mock:
            await self.helius.initialize()
            await self.jupiter.initialize()
        
    async def close(self):
        """Close API connections"""
        if not self.use_mock:
            await self.helius.close()
            await self.jupiter.close()
        
    async def analyze_deployer(self, token_address: str) -> Dict:
        """Analyze token deployer"""
        try:
            # Get deployer info
            if self.use_mock:
                deployer = get_mock_deployer(token_address)
                analysis = {
                    "deployer_address": deployer["address"],
                    "other_tokens": [],  # Mock data doesn't track other tokens
                    "risk_score": deployer["risk_score"],
                    "analysis": {
                        "token_count": 1,
                        "success_rate": 1.0,
                        "avg_token_age": 30,  # 30 days
                        "verified": deployer["verified"],
                        "blacklisted": False
                    }
                }
                await event_manager.emit("deployer_analysis_complete", analysis)
                return analysis

            # Get deployer address from real API
            deployer = await self.helius.get_token_deployer(token_address)
            if not deployer or not deployer.get("address"):
                analysis = {
                    "deployer_address": None,
                    "other_tokens": [],
                    "risk_score": 0,
                    "analysis": {
                        "token_count": 0,
                        "success_rate": 0.0,
                        "avg_token_age": 0,
                        "verified": False,
                        "blacklisted": False
                    }
                }
                await event_manager.emit("deployer_analysis_complete", analysis)
                return analysis
            
            deployer_address = deployer["address"]
            
            # Get other tokens deployed by this address
            other_tokens = await self.helius.get_deployer_tokens(deployer_address)
            
            # Calculate metrics
            token_count = len(other_tokens)
            success_rate = sum(1 for t in other_tokens if t.get("success", False)) / max(token_count, 1)
            
            # Calculate average token age
            current_time = int(time.time())
            ages = [current_time - t.get("created_at", current_time) for t in other_tokens]
            avg_age = sum(ages) / max(len(ages), 1) / (24 * 3600)  # Convert to days
            
            # Calculate risk score (0-100)
            risk_score = self._calculate_risk_score(token_count, success_rate, avg_age)
            
            # Check blacklist
            is_blacklisted = (
                deployer_address in self.blacklist["deployers"] or
                token_address in self.blacklist["tokens"]
            )
            
            # Update deployer history
            self._update_deployer_history(deployer_address, token_address, risk_score)
            
            analysis = {
                "deployer_address": deployer_address,
                "other_tokens": [
                    {
                        "address": t["address"],
                        "name": t.get("name", "Unknown"),
                        "success": t.get("success", False),
                        "age_days": (current_time - t.get("created_at", current_time)) / (24 * 3600)
                    }
                    for t in other_tokens
                ],
                "risk_score": risk_score,
                "analysis": {
                    "token_count": token_count,
                    "success_rate": success_rate,
                    "avg_token_age": avg_age,
                    "verified": False,  # TODO: Implement verification check
                    "blacklisted": is_blacklisted
                }
            }
            
            # Emit analysis event
            await event_manager.emit("deployer_analysis_complete", analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing deployer for token {token_address}: {str(e)}")
            raise
            
    def _calculate_risk_score(self, token_count: int, success_rate: float, avg_age: float) -> float:
        """Calculate risk score based on deployer metrics"""
        try:
            # Base score starts at 50
            score = 50
            
            # Adjust for token count
            if token_count == 0:
                score += 20  # New deployer, higher risk
            elif token_count > 10:
                score -= 10  # Experienced deployer
                
            # Adjust for success rate
            if success_rate < 0.5:
                score += 20  # Poor track record
            elif success_rate > 0.8:
                score -= 10  # Good track record
                
            # Adjust for average token age
            if avg_age < 7:  # Less than a week
                score += 10
            elif avg_age > 30:  # More than a month
                score -= 10
                
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {str(e)}")
            return 50  # Default to medium risk
            
    def _update_deployer_history(self, deployer_address: str, token_address: str, risk_score: float):
        """Update deployer history"""
        try:
            if deployer_address not in self.deployer_history:
                self.deployer_history[deployer_address] = {
                    "tokens": [],
                    "avg_risk_score": risk_score,
                    "last_updated": datetime.now().isoformat()
                }
                
            history = self.deployer_history[deployer_address]
            history["tokens"].append({
                "address": token_address,
                "risk_score": risk_score,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update average risk score
            scores = [t["risk_score"] for t in history["tokens"]]
            history["avg_risk_score"] = sum(scores) / len(scores)
            history["last_updated"] = datetime.now().isoformat()
            
            # Save updated history
            self._save_history()
            
        except Exception as e:
            logger.error(f"Error updating deployer history: {str(e)}")
            
    async def start(self) -> None:
        """Start the analyzer"""
        pass

    async def shutdown(self) -> None:
        """Shutdown the analyzer"""
        await self.close()
