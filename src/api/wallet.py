from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path

router = APIRouter()

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
        if not self.wallets_file.exists():
            self.wallets_file.write_text('{"wallets": []}')
            
    def get_wallets(self) -> List[Wallet]:
        data = json.loads(self.wallets_file.read_text())
        return [Wallet(**w) for w in data["wallets"]]
        
    def add_wallet(self, wallet: Wallet):
        data = json.loads(self.wallets_file.read_text())
        if any(w["address"] == wallet.address for w in data["wallets"]):
            raise HTTPException(status_code=400, detail="Wallet already exists")
        data["wallets"].append(wallet.dict())
        self.wallets_file.write_text(json.dumps(data, indent=2))
        
    def remove_wallet(self, address: str):
        data = json.loads(self.wallets_file.read_text())
        data["wallets"] = [w for w in data["wallets"] if w["address"] != address]
        self.wallets_file.write_text(json.dumps(data, indent=2))

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
    return {"status": "success"}
