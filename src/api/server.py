from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import asyncio
import uvicorn
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.token_launcher import TokenLaunchCollector
from collectors.dex_trades import DexTradeCollector
from collectors.wallet_analyzer import WalletAnalyzer
from analyzers.suspicious_activity_analyzer import SuspiciousActivityAnalyzer
from managers.blacklist_manager import BlacklistManager

app = FastAPI(
    title="Solana Data Collector API",
    description="API for analyzing Solana tokens and tracking suspicious activity",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
blacklist_manager = BlacklistManager()
suspicious_analyzer = SuspiciousActivityAnalyzer()

# Pydantic models for request/response
class TokenAnalysisRequest(BaseModel):
    token_address: str
    include_holder_analysis: bool = True
    include_twitter_analysis: bool = True

class WalletAnalysisRequest(BaseModel):
    wallet_address: str

class BlacklistInfo(BaseModel):
    total_blacklisted: int
    total_scam_amount: float
    recent_additions: List[Dict]

@app.get("/")
async def root():
    return {"status": "online", "service": "Solana Data Collector"}

@app.post("/analyze/token")
async def analyze_token(request: TokenAnalysisRequest):
    """
    Analyze a Solana token for suspicious activity
    """
    try:
        # Check if token's deployer is blacklisted
        token_data = await get_token_data(request.token_address)
        deployer_address = token_data.get('deployer_data', {}).get('address')
        
        if deployer_address and blacklist_manager.is_blacklisted(deployer_address):
            raise HTTPException(
                status_code=400,
                detail=f"Token deployer {deployer_address} is blacklisted"
            )
        
        # Perform analysis
        analysis_result = await suspicious_analyzer.analyze_volume_patterns(
            token_data.get('trading_data', {}).get('trades', [])
        )
        
        # Update blacklist if suspicious
        if analysis_result['is_suspicious']:
            await blacklist_manager.add_to_blacklist(
                deployer_address,
                "Suspicious token activity detected",
                {
                    "token_address": request.token_address,
                    "reasons": analysis_result['reasons']
                }
            )
        
        return {
            "token_address": request.token_address,
            "analysis_result": analysis_result,
            "token_data": token_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/wallet")
async def analyze_wallet(request: WalletAnalysisRequest):
    """
    Analyze a wallet's trading history and behavior
    """
    try:
        wallet_analyzer = WalletAnalyzer()
        analysis_result = await wallet_analyzer.analyze_wallet(request.wallet_address)
        
        # Check if wallet is in backlogs
        backlog_info = blacklist_manager.get_wallet_info(request.wallet_address)
        
        return {
            "wallet_address": request.wallet_address,
            "analysis_result": analysis_result,
            "backlog_info": backlog_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blacklist/stats")
async def get_blacklist_stats():
    """
    Get statistics about blacklisted addresses
    """
    try:
        report = await blacklist_manager.generate_report()
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/status")
async def get_monitor_status():
    """
    Get current monitoring status
    """
    try:
        # Get statistics about current monitoring
        return {
            "status": "active",
            "tokens_monitored": 0,  # Implement counter
            "alerts_today": 0,  # Implement counter
            "last_update": "2024-01-12T16:44:14+05:30"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_token_data(token_address: str) -> Dict:
    """
    Gather all relevant data for a token
    """
    # Implement token data collection
    # This should aggregate data from various collectors
    pass

def start():
    """
    Start the FastAPI server
    """
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    start()
