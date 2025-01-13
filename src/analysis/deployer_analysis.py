import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path

from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI

logger = logging.getLogger(__name__)

class DeployerAnalysis:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.blacklist_file = Path(__file__).parent.parent.parent / "data" / "blacklist.json"
        self.deployer_history_file = Path(__file__).parent.parent.parent / "data" / "deployer_history.json"
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

    async def analyze_deployer(self, deployer_address: str) -> Dict:
        """Analyze a deployer's history and performance"""
        try:
            # Check if blacklisted
            if deployer_address in self.blacklist["deployers"]:
                return {
                    "address": deployer_address,
                    "blacklisted": True,
                    "risk_level": "High",
                    "success_rate": 0,
                    "total_tokens": 0,
                    "successful_tokens": 0,
                    "failed_tokens": 0,
                    "avg_token_age": 0,
                    "total_mc": 0,
                    "history": []
                }

            # Check if we have recent history
            history = self.deployer_history.get(deployer_address, {})
            if history and (datetime.now() - datetime.fromisoformat(history.get("last_updated", "2000-01-01"))).total_seconds() < 3600:
                return {
                    "address": deployer_address,
                    "blacklisted": deployer_address in self.blacklist["deployers"],
                    **history,
                    "history": history.get("history", [])
                }

            # Get deployer's tokens
            tokens = await self.helius.get_deployer_tokens(deployer_address)
            if not tokens:
                return self._create_new_deployer_profile(deployer_address)

            # Analyze each token
            successful_tokens = 0
            failed_tokens = 0
            total_mc = 0
            token_history = []

            for token in tokens:
                token_address = token.get("address")
                if not token_address:
                    continue

                try:
                    # Get token metrics
                    price_data = await self.jupiter.get_token_price(token_address)
                    price = float(price_data.get("price", 0))
                    
                    supply_info = await self.helius.get_token_supply(token_address)
                    supply = float(supply_info.get("supply", "0"))
                    decimals = int(supply_info.get("decimals", 0))
                    
                    # Calculate market cap (price * actual supply)
                    market_cap = price * supply
                    
                    # Check success/failure thresholds
                    if market_cap >= 3_000_000:  # 3M MC
                        successful_tokens += 1
                    elif market_cap <= 200_000:  # 200k MC
                        failed_tokens += 1

                    total_mc += market_cap

                    # Get token age
                    metadata = await self.helius.get_token_metadata(token_address)
                    created_at = metadata.get("onChainMetadata", {}).get("metadata", {}).get("updateAuthority", {}).get("createdAt", "")
                    age = (datetime.now() - datetime.fromisoformat(created_at)).days if created_at else 0

                    # Add to history
                    token_history.append({
                        "address": token_address,
                        "market_cap": market_cap,
                        "age_days": age,
                        "success": market_cap >= 3_000_000
                    })

                except Exception as e:
                    logger.error(f"Error processing token {token_address}: {str(e)}")
                    continue

            # Calculate metrics
            total_tokens = len(token_history)  # Use actual processed tokens
            success_rate = (successful_tokens / total_tokens * 100) if total_tokens > 0 else 0
            avg_token_age = sum(t["age_days"] for t in token_history) / len(token_history) if token_history else 0

            # Determine risk level based on multiple factors
            risk_level = "Medium"  # Default risk level
            
            if total_tokens >= 3:
                if success_rate >= 70:
                    risk_level = "Low"
                elif success_rate <= 30 or (failed_tokens / total_tokens) >= 0.5:
                    risk_level = "High"
            elif total_tokens > 0:
                if successful_tokens > 0:
                    risk_level = "Low"
                elif failed_tokens > 0:
                    risk_level = "High"

            # Update deployer history
            history_data = {
                "last_updated": datetime.now().isoformat(),
                "success_rate": success_rate,
                "total_tokens": total_tokens,
                "successful_tokens": successful_tokens,
                "failed_tokens": failed_tokens,
                "avg_token_age": avg_token_age,
                "total_mc": total_mc,
                "risk_level": risk_level,
                "history": token_history
            }
            self.deployer_history[deployer_address] = history_data
            self._save_history()

            # Check if should be blacklisted
            if risk_level == "High" and total_tokens >= 3 and failed_tokens >= 2:
                if deployer_address not in self.blacklist["deployers"]:
                    self.blacklist["deployers"].append(deployer_address)
                    self._save_blacklist()

            return {
                "address": deployer_address,
                "blacklisted": deployer_address in self.blacklist["deployers"],
                **history_data
            }

        except Exception as e:
            logger.error(f"Error analyzing deployer {deployer_address}: {str(e)}")
            return self._create_new_deployer_profile(deployer_address)

    def _create_new_deployer_profile(self, deployer_address: str) -> Dict:
        """Create profile for new deployer"""
        return {
            "address": deployer_address,
            "blacklisted": False,
            "risk_level": "Medium",  # New deployers start as medium risk
            "success_rate": 0,
            "total_tokens": 0,
            "successful_tokens": 0,
            "failed_tokens": 0,
            "avg_token_age": 0,
            "total_mc": 0,
            "history": []
        }

    def is_blacklisted(self, address: str, address_type: str = "deployer") -> bool:
        """Check if an address is blacklisted"""
        return address in self.blacklist.get(f"{address_type}s", [])
