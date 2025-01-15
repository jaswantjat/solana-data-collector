from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import logging
from ..config.paths import DATA_DIR, WALLETS_FILE

router = APIRouter()
logger = logging.getLogger(__name__)

class Wallet(BaseModel):
    address: str
    label: Optional[str] = None
    watch_only: bool = False

class WalletManager:
    def __init__(self):
        self.wallets_file = WALLETS_FILE
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.wallets_file), exist_ok=True)
            logger.info(f"Using data directory: {DATA_DIR}")
            
            # Create wallets file if it doesn't exist
            if not os.path.exists(self.wallets_file):
                logger.info(f"Creating wallets file: {self.wallets_file}")
                with open(self.wallets_file, 'w') as f:
                    json.dump({"wallets": []}, f, indent=2)
            else:
                logger.info(f"Using existing wallets file: {self.wallets_file}")
        except Exception as e:
            logger.error(f"Error ensuring wallet file exists: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize wallet storage: {str(e)}")
            
    def get_wallets(self) -> List[Wallet]:
        try:
            with open(self.wallets_file, 'r') as f:
                data = json.load(f)
            return [Wallet(**w) for w in data["wallets"]]
        except Exception as e:
            logger.error(f"Error getting wallets: {e}")
            raise HTTPException(status_code=500, detail="Failed to read wallets")
            
    def add_wallet(self, wallet: Wallet):
        try:
            with open(self.wallets_file, 'r') as f:
                data = json.load(f)
                
            if any(w["address"] == wallet.address for w in data["wallets"]):
                raise HTTPException(status_code=400, detail="Wallet already exists")
                
            data["wallets"].append(wallet.dict())
            
            with open(self.wallets_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Added wallet: {wallet.address}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            raise HTTPException(status_code=500, detail="Failed to add wallet")
            
    def remove_wallet(self, address: str):
        try:
            with open(self.wallets_file, 'r') as f:
                data = json.load(f)
                
            original_length = len(data["wallets"])
            data["wallets"] = [w for w in data["wallets"] if w["address"] != address]
            
            if len(data["wallets"]) == original_length:
                raise HTTPException(status_code=404, detail="Wallet not found")
                
            with open(self.wallets_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Removed wallet: {address}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error removing wallet: {e}")
            raise HTTPException(status_code=500, detail="Failed to remove wallet")

wallet_manager = WalletManager()

@router.get("/wallets", response_model=List[Wallet])
async def get_wallets():
    return wallet_manager.get_wallets()

@router.post("/wallets", response_model=Wallet)
async def add_wallet(wallet: Wallet):
    wallet_manager.add_wallet(wallet)
    return wallet

@router.delete("/wallets/{address}")
async def remove_wallet(address: str):
    wallet_manager.remove_wallet(address)
    return {"status": "success", "message": f"Wallet {address} removed"}
