import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import aiofiles
import os

class BlacklistManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.blacklist_file = os.path.join(data_dir, "blacklists", "deployer_blacklist.json")
        self.wallet_backlog_file = os.path.join(data_dir, "backlogs", "wallet_backlog.json")
        self.blacklisted_deployers = {}
        self.wallet_backlog = {
            "scammer_wallets": {},
            "trusted_wallets": {}
        }
        self._ensure_directories()
        self._load_data()

    def _ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(os.path.join(self.data_dir, "blacklists"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "backlogs"), exist_ok=True)

    def _load_data(self):
        """Load blacklist and backlog data from files"""
        try:
            if os.path.exists(self.blacklist_file):
                with open(self.blacklist_file, 'r') as f:
                    self.blacklisted_deployers = json.load(f)
        except Exception as e:
            print(f"Error loading blacklist: {str(e)}")
            self.blacklisted_deployers = {}

        try:
            if os.path.exists(self.wallet_backlog_file):
                with open(self.wallet_backlog_file, 'r') as f:
                    self.wallet_backlog = json.load(f)
        except Exception as e:
            print(f"Error loading wallet backlog: {str(e)}")
            self.wallet_backlog = {
                "scammer_wallets": {},
                "trusted_wallets": {}
            }

    async def _save_blacklist(self):
        """Save blacklist data to file"""
        async with aiofiles.open(self.blacklist_file, 'w') as f:
            await f.write(json.dumps(self.blacklisted_deployers, indent=2))

    async def _save_wallet_backlog(self):
        """Save wallet backlog data to file"""
        async with aiofiles.open(self.wallet_backlog_file, 'w') as f:
            await f.write(json.dumps(self.wallet_backlog, indent=2))

    async def add_to_blacklist(
        self,
        deployer_address: str,
        reason: str,
        evidence: Dict
    ) -> bool:
        """
        Add a deployer to the blacklist
        """
        if deployer_address not in self.blacklisted_deployers:
            self.blacklisted_deployers[deployer_address] = {
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "evidence": evidence,
                "failed_tokens": [],
                "total_scam_amount": 0.0
            }
            await self._save_blacklist()
            return True
        return False

    async def add_failed_token(
        self,
        deployer_address: str,
        token_address: str,
        scam_amount: float
    ):
        """
        Add a failed token to a blacklisted deployer's record
        """
        if deployer_address in self.blacklisted_deployers:
            if token_address not in self.blacklisted_deployers[deployer_address]["failed_tokens"]:
                self.blacklisted_deployers[deployer_address]["failed_tokens"].append(token_address)
                self.blacklisted_deployers[deployer_address]["total_scam_amount"] += scam_amount
                await self._save_blacklist()
                return True
        return False

    def is_blacklisted(self, deployer_address: str) -> bool:
        """
        Check if a deployer is blacklisted
        """
        return deployer_address in self.blacklisted_deployers

    async def add_scammer_wallet(
        self,
        wallet_address: str,
        reason: str,
        evidence: Dict
    ) -> bool:
        """
        Add a wallet to the scammer backlog
        """
        if wallet_address not in self.wallet_backlog["scammer_wallets"]:
            self.wallet_backlog["scammer_wallets"][wallet_address] = {
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "evidence": evidence,
                "scam_history": [],
                "total_scam_amount": 0.0
            }
            await self._save_wallet_backlog()
            return True
        return False

    async def add_trusted_wallet(
        self,
        wallet_address: str,
        reason: str,
        performance_metrics: Dict
    ) -> bool:
        """
        Add a wallet to the trusted backlog
        """
        if wallet_address not in self.wallet_backlog["trusted_wallets"]:
            self.wallet_backlog["trusted_wallets"][wallet_address] = {
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "performance_metrics": performance_metrics,
                "successful_trades": [],
                "total_profit": 0.0
            }
            await self._save_wallet_backlog()
            return True
        return False

    async def update_scammer_history(
        self,
        wallet_address: str,
        scam_event: Dict
    ):
        """
        Update scammer wallet's history
        """
        if wallet_address in self.wallet_backlog["scammer_wallets"]:
            self.wallet_backlog["scammer_wallets"][wallet_address]["scam_history"].append(scam_event)
            self.wallet_backlog["scammer_wallets"][wallet_address]["total_scam_amount"] += scam_event.get("amount", 0)
            await self._save_wallet_backlog()
            return True
        return False

    async def update_trusted_history(
        self,
        wallet_address: str,
        trade_event: Dict
    ):
        """
        Update trusted wallet's trading history
        """
        if wallet_address in self.wallet_backlog["trusted_wallets"]:
            self.wallet_backlog["trusted_wallets"][wallet_address]["successful_trades"].append(trade_event)
            self.wallet_backlog["trusted_wallets"][wallet_address]["total_profit"] += trade_event.get("profit", 0)
            await self._save_wallet_backlog()
            return True
        return False

    def is_scammer_wallet(self, wallet_address: str) -> bool:
        """
        Check if a wallet is in the scammer backlog
        """
        return wallet_address in self.wallet_backlog["scammer_wallets"]

    def is_trusted_wallet(self, wallet_address: str) -> bool:
        """
        Check if a wallet is in the trusted backlog
        """
        return wallet_address in self.wallet_backlog["trusted_wallets"]

    def get_blacklist_info(self, deployer_address: str) -> Optional[Dict]:
        """
        Get information about a blacklisted deployer
        """
        return self.blacklisted_deployers.get(deployer_address)

    def get_wallet_info(self, wallet_address: str) -> Optional[Dict]:
        """
        Get information about a wallet from either backlog
        """
        return (
            self.wallet_backlog["scammer_wallets"].get(wallet_address) or
            self.wallet_backlog["trusted_wallets"].get(wallet_address)
        )

    def get_all_blacklisted_deployers(self) -> Dict:
        """
        Get all blacklisted deployers
        """
        return self.blacklisted_deployers

    def get_all_scammer_wallets(self) -> Dict:
        """
        Get all scammer wallets
        """
        return self.wallet_backlog["scammer_wallets"]

    def get_all_trusted_wallets(self) -> Dict:
        """
        Get all trusted wallets
        """
        return self.wallet_backlog["trusted_wallets"]

    async def generate_report(self) -> Dict:
        """
        Generate a comprehensive report of blacklists and backlogs
        """
        return {
            "blacklist_stats": {
                "total_blacklisted_deployers": len(self.blacklisted_deployers),
                "total_failed_tokens": sum(
                    len(d["failed_tokens"]) for d in self.blacklisted_deployers.values()
                ),
                "total_scam_amount": sum(
                    d["total_scam_amount"] for d in self.blacklisted_deployers.values()
                )
            },
            "backlog_stats": {
                "total_scammer_wallets": len(self.wallet_backlog["scammer_wallets"]),
                "total_trusted_wallets": len(self.wallet_backlog["trusted_wallets"]),
                "total_scam_amount": sum(
                    w["total_scam_amount"] for w in self.wallet_backlog["scammer_wallets"].values()
                ),
                "total_profit_trusted": sum(
                    w["total_profit"] for w in self.wallet_backlog["trusted_wallets"].values()
                )
            }
        }
