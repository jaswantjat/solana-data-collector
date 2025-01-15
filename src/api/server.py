"""FastAPI server for Solana Data Collector."""
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
def root():
    """Root endpoint."""
    return {"message": "Solana Data Collector API is running"}

@app.post("/analyze/token")
async def analyze_token(request: TokenAnalysisRequest):
    """Analyze a Solana token for suspicious activity."""
    try:
        # Initialize collectors
        token_collector = TokenLaunchCollector()
        dex_collector = DexTradeCollector()
        
        # Collect token data
        token_data = await token_collector.collect_token_data(request.token_address)
        trade_data = await dex_collector.collect_trade_data(request.token_address)
        
        # Analyze for suspicious activity
        analysis = suspicious_analyzer.analyze_token(
            token_data=token_data,
            trade_data=trade_data,
            include_holder_analysis=request.include_holder_analysis,
            include_twitter_analysis=request.include_twitter_analysis
        )
        
        return {
            "token_address": request.token_address,
            "analysis_results": analysis,
            "risk_score": analysis.get("risk_score", 0),
            "warnings": analysis.get("warnings", []),
            "recommendations": analysis.get("recommendations", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/wallet")
async def analyze_wallet(request: WalletAnalysisRequest):
    """Analyze a wallet's trading history and behavior."""
    try:
        analyzer = WalletAnalyzer()
        analysis = await analyzer.analyze_wallet(request.wallet_address)
        
        return {
            "wallet_address": request.wallet_address,
            "analysis_results": analysis,
            "risk_score": analysis.get("risk_score", 0),
            "suspicious_transactions": analysis.get("suspicious_transactions", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blacklist/stats")
async def get_blacklist_stats():
    """Get statistics about blacklisted addresses."""
    try:
        stats = blacklist_manager.get_stats()
        return BlacklistInfo(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/status")
async def get_monitor_status():
    """Get current monitoring status."""
    try:
        # Get status from various collectors
        token_status = TokenLaunchCollector().get_status()
        dex_status = DexTradeCollector().get_status()
        
        return {
            "token_monitor": token_status,
            "dex_monitor": dex_status,
            "last_update": str(asyncio.get_event_loop().time())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/token/{token_address}")
async def get_token_data(token_address: str):
    """Gather all relevant data for a token."""
    try:
        token_collector = TokenLaunchCollector()
        return await token_collector.collect_token_data(token_address)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start():
    """Start the FastAPI server."""
    port = int(os.environ.get("PORT", 10000))  # Render's default port is 10000
    uvicorn.run(
        app,
        host="0.0.0.0",  # Required for Render
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    start()
