import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from ..integrations.helius import HeliusAPI
from ..integrations.jupiter import JupiterAPI

logger = logging.getLogger(__name__)

class WalletTracker:
    def __init__(self):
        self.helius = HeliusAPI()
        self.jupiter = JupiterAPI()
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.wallet_file = self.data_dir / "wallet_data.json"
        self._load_data()
        
    def _load_data(self):
        """Load wallet data from file"""
        try:
            if self.wallet_file.exists():
                with open(self.wallet_file, 'r') as f:
                    self.wallet_data = json.load(f)
            else:
                self.wallet_data = {
                    "sniper_wallets": [],
                    "insider_wallets": [],
                    "good_wallets": [],
                    "scam_wallets": [],
                    "wallet_stats": {}
                }
        except Exception as e:
            logger.error(f"Error loading wallet data: {str(e)}")
            self.wallet_data = {
                "sniper_wallets": [],
                "insider_wallets": [],
                "good_wallets": [],
                "scam_wallets": [],
                "wallet_stats": {}
            }
            
    def _save_data(self):
        """Save wallet data to file"""
        try:
            with open(self.wallet_file, 'w') as f:
                json.dump(self.wallet_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving wallet data: {str(e)}")
            
    async def analyze_wallet(self, address: str) -> Dict:
        """Analyze a wallet's behavior and performance"""
        try:
            # Get wallet's transaction history
            transactions = await self.helius.get_wallet_history(address, days=30)
            
            # Analyze trading patterns
            token_trades = {}
            quick_sells = 0
            total_trades = 0
            profitable_trades = 0
            
            for tx in transactions:
                if "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" in tx.get("programIds", []):
                    token_address = tx.get("tokenTransfers", [{}])[0].get("mint")
                    if token_address:
                        if token_address not in token_trades:
                            token_trades[token_address] = {
                                "buy_time": None,
                                "sell_time": None,
                                "buy_price": 0,
                                "sell_price": 0
                            }
                            
                        # Get token price
                        price_info = await self.jupiter.get_token_price(token_address)
                        current_price = price_info.get("price", 0)
                        
                        if tx.get("type") == "TRANSFER":
                            total_trades += 1
                            trade = token_trades[token_address]
                            
                            if not trade["buy_time"]:
                                trade["buy_time"] = tx["timestamp"]
                                trade["buy_price"] = current_price
                            else:
                                trade["sell_time"] = tx["timestamp"]
                                trade["sell_price"] = current_price
                                
                                # Calculate trade metrics
                                hold_time = datetime.fromisoformat(trade["sell_time"]) - datetime.fromisoformat(trade["buy_time"])
                                if hold_time < timedelta(minutes=5):
                                    quick_sells += 1
                                    
                                if trade["sell_price"] > trade["buy_price"]:
                                    profitable_trades += 1
                                    
            # Calculate wallet metrics
            metrics = {
                "total_trades": total_trades,
                "quick_sells": quick_sells,
                "quick_sell_ratio": quick_sells / total_trades if total_trades > 0 else 0,
                "win_rate": profitable_trades / total_trades if total_trades > 0 else 0,
                "unique_tokens": len(token_trades)
            }
            
            # Classify wallet behavior
            if metrics["quick_sell_ratio"] > 0.5:
                classification = "sniper"
            elif metrics["win_rate"] > 0.7 and metrics["total_trades"] > 50:
                classification = "good_trader"
            elif metrics["quick_sell_ratio"] > 0.3 and metrics["win_rate"] < 0.3:
                classification = "scammer"
            else:
                classification = "normal"
                
            return {
                "address": address,
                "metrics": metrics,
                "classification": classification,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing wallet: {str(e)}")
            return {}
            
    async def update_wallet_classification(self, address: str, force_update: bool = False):
        """Update wallet classification"""
        try:
            current_time = datetime.now()
            stats = self.wallet_data["wallet_stats"].get(address, {})
            last_updated = datetime.fromisoformat(stats.get("last_updated", "2000-01-01T00:00:00")) if stats else None
            
            # Update if never analyzed or last update was more than 24 hours ago
            if force_update or not last_updated or (current_time - last_updated) > timedelta(hours=24):
                analysis = await self.analyze_wallet(address)
                
                if analysis:
                    # Update wallet stats
                    self.wallet_data["wallet_stats"][address] = analysis
                    
                    # Update classification lists
                    classification = analysis["classification"]
                    
                    # Remove from all lists first
                    for list_name in ["sniper_wallets", "good_wallets", "scam_wallets"]:
                        if address in self.wallet_data[list_name]:
                            self.wallet_data[list_name].remove(address)
                            
                    # Add to appropriate list
                    if classification == "sniper":
                        self.wallet_data["sniper_wallets"].append(address)
                    elif classification == "good_trader":
                        self.wallet_data["good_wallets"].append(address)
                    elif classification == "scammer":
                        self.wallet_data["scam_wallets"].append(address)
                        
                    self._save_data()
                    
        except Exception as e:
            logger.error(f"Error updating wallet classification: {str(e)}")
            
    def is_sniper(self, address: str) -> bool:
        """Check if wallet is a known sniper"""
        return address in self.wallet_data["sniper_wallets"]
        
    def is_insider(self, address: str) -> bool:
        """Check if wallet is a known insider"""
        return address in self.wallet_data["insider_wallets"]
        
    def is_good_wallet(self, address: str) -> bool:
        """Check if wallet is a known good trader"""
        return address in self.wallet_data["good_wallets"]
        
    def is_scammer(self, address: str) -> bool:
        """Check if wallet is a known scammer"""
        return address in self.wallet_data["scam_wallets"]
        
    def get_wallet_stats(self, address: str) -> Dict:
        """Get wallet statistics"""
        return self.wallet_data["wallet_stats"].get(address, {})
