"""FastAPI server for Solana Data Collector."""
import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config import config
from src.collectors.token_launcher import TokenLaunchCollector
from src.collectors.dex_trade import DexTradeCollector
from src.collectors.wallet_analyzer import WalletAnalyzer
from src.analyzers.suspicious_activity_analyzer import SuspiciousActivityAnalyzer
from src.managers.blacklist_manager import BlacklistManager
from src.database.connection import db_manager
from src.utils.logging import get_logger
from src.api.middleware import setup_middleware
from src.api.health import router as health_router
from src.api.errors import (
    setup_error_handlers,
    NotFoundError,
    ValidationAPIError,
    DatabaseError
)

# Configure logging
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Solana Data Collector API",
    description="API for analyzing Solana tokens and tracking suspicious activity",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('CORS_ORIGINS', ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up middleware and error handlers
setup_middleware(app)
setup_error_handlers(app)

# Include routers
app.include_router(health_router, prefix="/health", tags=["Health"])

# Initialize managers
blacklist_manager = BlacklistManager()
suspicious_analyzer = SuspiciousActivityAnalyzer()

# Pydantic models for request/response
class TokenAnalysisRequest(BaseModel):
    token_address: str
    include_holder_analysis: bool = True
    include_twitter_analysis: bool = True

class TokenAnalysisResponse(BaseModel):
    token_address: str
    is_suspicious: bool
    risk_factors: List[str]
    confidence_score: float
    analysis_timestamp: datetime

class WalletAnalysisRequest(BaseModel):
    wallet_address: str
    include_transaction_history: bool = True

class WalletAnalysisResponse(BaseModel):
    wallet_address: str
    risk_score: float
    suspicious_transactions: List[Dict]
    analysis_timestamp: datetime

class BlacklistInfo(BaseModel):
    total_blacklisted: int
    total_scam_amount: float
    recent_additions: List[Dict]

async def get_db():
    """Dependency for database sessions."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Initializing database connection...")
        db_manager.get_session()
        
        logger.info("Initializing blacklist manager...")
        await blacklist_manager.initialize()
        
        logger.info("API server started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise DatabaseError("Failed to initialize services", {"error": str(e)})

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.post("/analyze/token", response_model=TokenAnalysisResponse)
async def analyze_token(
    request: TokenAnalysisRequest,
    db=Depends(get_db)
):
    """Analyze a Solana token for suspicious activity."""
    try:
        logger.info(f"Analyzing token: {request.token_address}")
        
        # Perform analysis
        analysis_result = await suspicious_analyzer.analyze_token(
            request.token_address,
            include_holder_analysis=request.include_holder_analysis,
            include_twitter_analysis=request.include_twitter_analysis,
            db_session=db
        )
        
        if not analysis_result:
            raise NotFoundError(
                f"Token {request.token_address} not found",
                {"token_address": request.token_address}
            )
        
        return TokenAnalysisResponse(
            token_address=request.token_address,
            is_suspicious=analysis_result.is_suspicious,
            risk_factors=analysis_result.risk_factors,
            confidence_score=analysis_result.confidence_score,
            analysis_timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error analyzing token {request.token_address}: {str(e)}")
        if isinstance(e, NotFoundError):
            raise
        raise DatabaseError(
            "Failed to analyze token",
            {"token_address": request.token_address, "error": str(e)}
        )

@app.post("/analyze/wallet", response_model=WalletAnalysisResponse)
async def analyze_wallet(
    request: WalletAnalysisRequest,
    db=Depends(get_db)
):
    """Analyze a wallet's trading history and behavior."""
    try:
        analyzer = WalletAnalyzer(db_session=db)
        analysis = await analyzer.analyze_wallet(
            request.wallet_address,
            include_history=request.include_transaction_history
        )
        
        if not analysis:
            raise NotFoundError(
                f"Wallet {request.wallet_address} not found",
                {"wallet_address": request.wallet_address}
            )
            
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing wallet {request.wallet_address}: {str(e)}")
        if isinstance(e, NotFoundError):
            raise
        raise DatabaseError(
            "Failed to analyze wallet",
            {"wallet_address": request.wallet_address, "error": str(e)}
        )

@app.get("/blacklist/stats", response_model=BlacklistInfo)
async def get_blacklist_stats(db=Depends(get_db)):
    """Get statistics about blacklisted addresses."""
    try:
        stats = await blacklist_manager.get_stats(db_session=db)
        return BlacklistInfo(**stats)
    except Exception as e:
        logger.error(f"Error getting blacklist stats: {str(e)}")
        raise DatabaseError("Failed to get blacklist stats", {"error": str(e)})

@app.get("/monitor/status")
async def get_monitor_status(db=Depends(get_db)):
    """Get current monitoring status."""
    try:
        return {
            "status": "active",
            "last_update": datetime.utcnow(),
            "monitored_tokens": await TokenLaunchCollector(db_session=db).get_monitored_count(),
            "active_alerts": await suspicious_analyzer.get_active_alerts_count(db_session=db)
        }
    except Exception as e:
        logger.error(f"Error getting monitor status: {str(e)}")
        raise DatabaseError("Failed to get monitor status", {"error": str(e)})

@app.get("/token/{token_address}")
async def get_token_data(token_address: str, db=Depends(get_db)):
    """Gather all relevant data for a token."""
    try:
        collector = TokenLaunchCollector(db_session=db)
        token_data = await collector.get_token_data(token_address)
        
        if not token_data:
            raise NotFoundError(
                f"Token {token_address} not found",
                {"token_address": token_address}
            )
            
        return token_data
    except Exception as e:
        logger.error(f"Error getting token data for {token_address}: {str(e)}")
        if isinstance(e, NotFoundError):
            raise
        raise DatabaseError(
            "Failed to get token data",
            {"token_address": token_address, "error": str(e)}
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(
        "src.api.server:app",  # Use the correct module path
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production
    )
