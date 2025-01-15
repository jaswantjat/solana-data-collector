from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class Wallet(BaseModel):
    address: str
    label: Optional[str] = None
    watch_only: bool = False

class WalletManager:
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.wallets_file = self.data_dir / "wallets.json"
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        try:
            # Create data directory if it doesn't exist
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensuring data directory exists at: {self.data_dir}")
            
            # Create wallets file if it doesn't exist
            if not self.wallets_file.exists():
                logger.info(f"Creating wallets file at: {self.wallets_file}")
                self.wallets_file.write_text('{"wallets": []}')
            else:
                logger.info(f"Wallets file already exists at: {self.wallets_file}")
        except Exception as e:
            logger.error(f"Error ensuring wallet file exists: {e}")
            raise
            
    def get_wallets(self) -> List[Wallet]:
        try:
            data = json.loads(self.wallets_file.read_text())
            return [Wallet(**w) for w in data["wallets"]]
        except Exception as e:
            logger.error(f"Error getting wallets: {e}")
            raise
            
    def add_wallet(self, wallet: Wallet):
        try:
            data = json.loads(self.wallets_file.read_text())
            if any(w["address"] == wallet.address for w in data["wallets"]):
                raise HTTPException(status_code=400, detail="Wallet already exists")
            data["wallets"].append(wallet.dict())
            self.wallets_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            raise
            
    def remove_wallet(self, address: str):
        try:
            data = json.loads(self.wallets_file.read_text())
            data["wallets"] = [w for w in data["wallets"] if w["address"] != address]
            self.wallets_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error removing wallet: {e}")
            raise

wallet_manager = WalletManager()

@router.get("/wallets", response_model=List[Wallet])
async def get_wallets():
    try:
        return wallet_manager.get_wallets()
    except Exception as e:
        logger.error(f"Error getting wallets: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/wallets", response_model=Wallet)
async def add_wallet(wallet: Wallet):
    try:
        wallet_manager.add_wallet(wallet)
        return wallet
    except Exception as e:
        logger.error(f"Error adding wallet: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/wallets/{address}")
async def remove_wallet(address: str):
    try:
        wallet_manager.remove_wallet(address)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error removing wallet: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
