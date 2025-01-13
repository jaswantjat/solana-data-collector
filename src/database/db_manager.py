import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union
import json
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize database files
        self.wallet_db_file = self.data_dir / "wallet_database.json"
        self.token_db_file = self.data_dir / "token_database.json"
        self.blacklist_db_file = self.data_dir / "blacklist_database.json"
        
        self._load_databases()
        
    def _load_databases(self):
        """Load all databases from files"""
        try:
            # Load Wallet Database
            if self.wallet_db_file.exists():
                with open(self.wallet_db_file, 'r') as f:
                    self.wallet_db = json.load(f)
            else:
                self.wallet_db = {
                    "scammers": {},
                    "trusted_traders": {},
                    "snipers": {},
                    "insiders": {},
                    "performance_metrics": {}
                }
                self._save_wallet_db()

            # Load Token Database
            if self.token_db_file.exists():
                with open(self.token_db_file, 'r') as f:
                    self.token_db = json.load(f)
            else:
                self.token_db = {
                    "tokens": {},
                    "launches": {},
                    "performance": {},
                    "risk_scores": {},
                    "price_history": {}
                }
                self._save_token_db()

            # Load Blacklist Database
            if self.blacklist_db_file.exists():
                with open(self.blacklist_db_file, 'r') as f:
                    self.blacklist_db = json.load(f)
            else:
                self.blacklist_db = {
                    "scammer_addresses": {},
                    "failed_deployers": {},
                    "suspicious_patterns": {},
                    "compromised_contracts": {}
                }
                self._save_blacklist_db()
                
        except Exception as e:
            logger.error(f"Error loading databases: {str(e)}")
            self._initialize_empty_databases()

    def _initialize_empty_databases(self):
        """Initialize empty databases with default structure"""
        self.wallet_db = {
            "scammers": {},
            "trusted_traders": {},
            "snipers": {},
            "insiders": {},
            "performance_metrics": {}
        }
        
        self.token_db = {
            "tokens": {},
            "launches": {},
            "performance": {},
            "risk_scores": {},
            "price_history": {}
        }
        
        self.blacklist_db = {
            "scammer_addresses": {},
            "failed_deployers": {},
            "suspicious_patterns": {},
            "compromised_contracts": {}
        }
        
        self._save_all_databases()

    def _save_wallet_db(self):
        with open(self.wallet_db_file, 'w') as f:
            json.dump(self.wallet_db, f, indent=2)

    def _save_token_db(self):
        with open(self.token_db_file, 'w') as f:
            json.dump(self.token_db, f, indent=2)

    def _save_blacklist_db(self):
        with open(self.blacklist_db_file, 'w') as f:
            json.dump(self.blacklist_db, f, indent=2)

    def _save_all_databases(self):
        """Save all databases"""
        self._save_wallet_db()
        self._save_token_db()
        self._save_blacklist_db()

    # Wallet Database Methods
    def add_scammer_wallet(self, address: str, evidence: Dict) -> bool:
        """Add a known scammer wallet"""
        try:
            if address not in self.wallet_db["scammers"]:
                self.wallet_db["scammers"][address] = {
                    "evidence": evidence,
                    "added_at": datetime.now().isoformat(),
                    "incidents": [],
                    "risk_score": 1.0
                }
            else:
                self.wallet_db["scammers"][address]["incidents"].append(evidence)
                
            self._save_wallet_db()
            
            # Also add to blacklist
            self.add_to_blacklist("scammer_addresses", address, evidence)
            return True
        except Exception as e:
            logger.error(f"Error adding scammer wallet {address}: {str(e)}")
            return False

    def add_trusted_trader(self, address: str, metrics: Dict) -> bool:
        """Add a trusted trader wallet"""
        try:
            if address not in self.wallet_db["trusted_traders"]:
                self.wallet_db["trusted_traders"][address] = {
                    "metrics": metrics,
                    "added_at": datetime.now().isoformat(),
                    "performance_history": [],
                    "trust_score": self._calculate_trust_score(metrics)
                }
            else:
                self.wallet_db["trusted_traders"][address]["metrics"].update(metrics)
                self.wallet_db["trusted_traders"][address]["performance_history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                })
            
            self._save_wallet_db()
            return True
        except Exception as e:
            logger.error(f"Error adding trusted trader {address}: {str(e)}")
            return False

    def add_sniper_wallet(self, address: str, pattern: Dict) -> bool:
        """Add a sniper wallet"""
        try:
            if address not in self.wallet_db["snipers"]:
                self.wallet_db["snipers"][address] = {
                    "pattern": pattern,
                    "added_at": datetime.now().isoformat(),
                    "incidents": [],
                    "confidence_score": pattern.get("confidence", 0.5)
                }
            else:
                self.wallet_db["snipers"][address]["incidents"].append(pattern)
                
            self._save_wallet_db()
            return True
        except Exception as e:
            logger.error(f"Error adding sniper wallet {address}: {str(e)}")
            return False

    def add_insider_wallet(self, address: str, evidence: Dict) -> bool:
        """Add an insider trading wallet"""
        try:
            if address not in self.wallet_db["insiders"]:
                self.wallet_db["insiders"][address] = {
                    "evidence": evidence,
                    "added_at": datetime.now().isoformat(),
                    "incidents": [],
                    "confidence_score": evidence.get("confidence", 0.5)
                }
            else:
                self.wallet_db["insiders"][address]["incidents"].append(evidence)
                
            self._save_wallet_db()
            return True
        except Exception as e:
            logger.error(f"Error adding insider wallet {address}: {str(e)}")
            return False

    def update_wallet_performance(self, address: str, metrics: Dict) -> bool:
        """Update wallet performance metrics"""
        try:
            if address not in self.wallet_db["performance_metrics"]:
                self.wallet_db["performance_metrics"][address] = {
                    "metrics": metrics,
                    "history": [],
                    "last_updated": datetime.now().isoformat()
                }
            else:
                self.wallet_db["performance_metrics"][address]["metrics"].update(metrics)
                self.wallet_db["performance_metrics"][address]["history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                })
                self.wallet_db["performance_metrics"][address]["last_updated"] = datetime.now().isoformat()
            
            self._save_wallet_db()
            return True
        except Exception as e:
            logger.error(f"Error updating wallet performance {address}: {str(e)}")
            return False

    # Token Database Methods
    def add_token(self, address: str, metadata: Dict) -> bool:
        """Add a token to the database"""
        try:
            if address not in self.token_db["tokens"]:
                self.token_db["tokens"][address] = {
                    "metadata": metadata,
                    "added_at": datetime.now().isoformat(),
                    "updates": []
                }
            else:
                self.token_db["tokens"][address]["updates"].append({
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata
                })
            
            self._save_token_db()
            return True
        except Exception as e:
            logger.error(f"Error adding token {address}: {str(e)}")
            return False

    def add_token_launch(self, address: str, launch_data: Dict) -> bool:
        """Add token launch data"""
        try:
            if address not in self.token_db["launches"]:
                self.token_db["launches"][address] = {
                    "launch_data": launch_data,
                    "launch_time": datetime.now().isoformat(),
                    "updates": []
                }
            else:
                self.token_db["launches"][address]["updates"].append({
                    "timestamp": datetime.now().isoformat(),
                    "data": launch_data
                })
            
            self._save_token_db()
            return True
        except Exception as e:
            logger.error(f"Error adding token launch {address}: {str(e)}")
            return False

    def update_token_performance(self, address: str, metrics: Dict) -> bool:
        """Update token performance metrics"""
        try:
            if address not in self.token_db["performance"]:
                self.token_db["performance"][address] = {
                    "metrics": metrics,
                    "history": [],
                    "last_updated": datetime.now().isoformat()
                }
            else:
                self.token_db["performance"][address]["metrics"].update(metrics)
                self.token_db["performance"][address]["history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                })
            
            self._save_token_db()
            return True
        except Exception as e:
            logger.error(f"Error updating token performance {address}: {str(e)}")
            return False

    def update_token_risk_score(self, address: str, risk_data: Dict) -> bool:
        """Update token risk score"""
        try:
            if address not in self.token_db["risk_scores"]:
                self.token_db["risk_scores"][address] = {
                    "current_score": risk_data.get("score", 0.5),
                    "factors": risk_data.get("factors", {}),
                    "history": [],
                    "last_updated": datetime.now().isoformat()
                }
            else:
                self.token_db["risk_scores"][address]["current_score"] = risk_data.get("score", 0.5)
                self.token_db["risk_scores"][address]["factors"] = risk_data.get("factors", {})
                self.token_db["risk_scores"][address]["history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "score": risk_data.get("score", 0.5),
                    "factors": risk_data.get("factors", {})
                })
            
            self._save_token_db()
            return True
        except Exception as e:
            logger.error(f"Error updating token risk score {address}: {str(e)}")
            return False

    def add_price_data(self, address: str, price_data: Dict) -> bool:
        """Add token price data"""
        try:
            if address not in self.token_db["price_history"]:
                self.token_db["price_history"][address] = {
                    "prices": [price_data],
                    "last_updated": datetime.now().isoformat()
                }
            else:
                self.token_db["price_history"][address]["prices"].append(price_data)
                self.token_db["price_history"][address]["last_updated"] = datetime.now().isoformat()
            
            self._save_token_db()
            return True
        except Exception as e:
            logger.error(f"Error adding price data {address}: {str(e)}")
            return False

    # Blacklist Database Methods
    def add_to_blacklist(self, category: str, address: str, evidence: Dict) -> bool:
        """Add an address to the specified blacklist category"""
        try:
            if category not in self.blacklist_db:
                logger.error(f"Invalid blacklist category: {category}")
                return False
                
            if address not in self.blacklist_db[category]:
                self.blacklist_db[category][address] = {
                    "evidence": evidence,
                    "added_at": datetime.now().isoformat(),
                    "incidents": []
                }
            else:
                self.blacklist_db[category][address]["incidents"].append({
                    "timestamp": datetime.now().isoformat(),
                    "evidence": evidence
                })
            
            self._save_blacklist_db()
            return True
        except Exception as e:
            logger.error(f"Error adding to blacklist {category} {address}: {str(e)}")
            return False

    def add_suspicious_pattern(self, pattern: Dict) -> bool:
        """Add a suspicious wallet pattern"""
        try:
            pattern_id = f"pattern_{len(self.blacklist_db['suspicious_patterns'])}"
            self.blacklist_db["suspicious_patterns"][pattern_id] = {
                "pattern": pattern,
                "added_at": datetime.now().isoformat(),
                "matches": []
            }
            
            self._save_blacklist_db()
            return True
        except Exception as e:
            logger.error(f"Error adding suspicious pattern: {str(e)}")
            return False

    def add_compromised_contract(self, address: str, details: Dict) -> bool:
        """Add a compromised contract"""
        try:
            if address not in self.blacklist_db["compromised_contracts"]:
                self.blacklist_db["compromised_contracts"][address] = {
                    "details": details,
                    "added_at": datetime.now().isoformat(),
                    "incidents": []
                }
            else:
                self.blacklist_db["compromised_contracts"][address]["incidents"].append({
                    "timestamp": datetime.now().isoformat(),
                    "details": details
                })
            
            self._save_blacklist_db()
            return True
        except Exception as e:
            logger.error(f"Error adding compromised contract {address}: {str(e)}")
            return False

    # Helper Methods
    def _calculate_trust_score(self, metrics: Dict) -> float:
        """Calculate trust score for a wallet based on metrics"""
        try:
            score = 0.0
            
            # Factor 1: Success rate
            success_rate = metrics.get("success_rate", 0)
            score += success_rate * 0.4
            
            # Factor 2: Age
            age_days = metrics.get("age_days", 0)
            age_score = min(1.0, age_days / 365)  # Cap at 1 year
            score += age_score * 0.3
            
            # Factor 3: Transaction volume
            volume = metrics.get("volume", 0)
            volume_score = min(1.0, volume / 1_000_000)  # Cap at $1M
            score += volume_score * 0.3
            
            return min(1.0, score)
        except Exception as e:
            logger.error(f"Error calculating trust score: {str(e)}")
            return 0.0

    def get_wallet_status(self, address: str) -> Dict:
        """Get comprehensive wallet status"""
        try:
            status = {
                "is_scammer": address in self.wallet_db["scammers"],
                "is_trusted": address in self.wallet_db["trusted_traders"],
                "is_sniper": address in self.wallet_db["snipers"],
                "is_insider": address in self.wallet_db["insiders"],
                "performance": self.wallet_db["performance_metrics"].get(address, {}),
                "blacklist_status": {
                    "scammer": address in self.blacklist_db["scammer_addresses"],
                    "failed_deployer": address in self.blacklist_db["failed_deployers"],
                    "suspicious": any(address in pattern.get("matches", [])
                                   for pattern in self.blacklist_db["suspicious_patterns"].values())
                }
            }
            return status
        except Exception as e:
            logger.error(f"Error getting wallet status {address}: {str(e)}")
            return {}
