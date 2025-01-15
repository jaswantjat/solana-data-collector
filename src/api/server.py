"""FastAPI server for Solana Data Collector."""
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.collectors.token_launcher import TokenLaunchCollector
from src.collectors.dex_trade import DexTradeCollector
from src.collectors.wallet_analyzer import WalletAnalyzer
from src.analyzers.suspicious_activity_analyzer import SuspiciousActivityAnalyzer
from src.managers.blacklist_manager import BlacklistManager
from src.database.connection import db_manager

logger = logging.getLogger(__name__)

# Create FastAPI app
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

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    try:
        # Test database connection
        with db_manager.get_session() as session:
            result = session.execute("SELECT 1").scalar()
            if result != 1:
                raise ValueError("Database connection test failed")
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to establish database connection: {str(e)}")
        # Don't raise the error - let the app start anyway
        # Individual endpoints will handle DB errors

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
        analysis = await suspicious_analyzer.analyze_token(
            token_data=token_data,
            trade_data=trade_data,
            include_holder_analysis=request.include_holder_analysis,
            include_twitter_analysis=request.include_twitter_analysis
        )
        
        return {
            "token_address": request.token_address,
            "analysis_results": analysis,
            "token_data": token_data,
            "trade_data": trade_data
        }
        
    except Exception as e:
        logger.error(f"Error analyzing token {request.token_address}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing token: {str(e)}"
        )

@app.post("/analyze/wallet")
async def analyze_wallet(request: WalletAnalysisRequest):
    """Analyze a wallet's trading history and behavior."""
    try:
        analyzer = WalletAnalyzer()
        analysis = await analyzer.analyze_wallet(request.wallet_address)
        return {
            "wallet_address": request.wallet_address,
            "analysis_results": analysis
        }
    except Exception as e:
        logger.error(f"Error analyzing wallet {request.wallet_address}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blacklist/stats")
def get_blacklist_stats() -> BlacklistInfo:
    """Get statistics about blacklisted addresses."""
    try:
        stats = blacklist_manager.get_stats()
        return BlacklistInfo(**stats)
    except Exception as e:
        logger.error(f"Error getting blacklist stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/status")
def get_monitor_status():
    """Get current monitoring status."""
    try:
        with db_manager.get_session() as session:
            recent_txs = session.execute(
                "SELECT COUNT(*) FROM transactions WHERE timestamp > NOW() - INTERVAL '1 hour'"
            ).scalar()
            
            return {
                "status": "running",
                "transactions_last_hour": recent_txs,
                "last_update": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Error getting monitor status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/token/{token_address}")
def get_token_data(token_address: str):
    """Gather all relevant data for a token."""
    try:
        with db_manager.get_session() as session:
            token_data = session.execute(
                "SELECT * FROM tokens WHERE address = %s", (token_address,)
            ).fetchone()
            return {"token_data": token_data}
    except Exception as e:
        logger.error(f"Error getting token data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        "src.api.server:app",  # Use the correct module path
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production
    )
