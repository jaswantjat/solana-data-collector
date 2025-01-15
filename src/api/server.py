"""FastAPI server initialization and configuration."""
import os
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

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
from src.monitoring.performance_manager import PerformanceManager

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
performance_manager = PerformanceManager()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Initializing database connection...")
        db_manager.get_session()
        
        logger.info("Initializing blacklist manager...")
        await blacklist_manager.initialize()
        
        logger.info("Initializing performance manager...")
        await performance_manager.initialize()
        
        logger.info("API server started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise DatabaseError("Failed to initialize services", {"error": str(e)})

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down services...")
        if performance_manager.redis:
            await performance_manager.redis.close()
        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

async def get_db():
    """Dependency for database sessions."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }

@app.post("/analyze/token")
async def analyze_token(
    token_address: str,
    include_holder_analysis: bool = True,
    include_twitter_analysis: bool = True,
    db=Depends(get_db)
):
    """Analyze a Solana token for suspicious activity."""
    try:
        logger.info(f"Analyzing token: {token_address}")
        
        # Record request start time
        start_time = datetime.utcnow()
        
        # Perform analysis
        analysis_result = await suspicious_analyzer.analyze_token(
            token_address,
            include_holder_analysis=include_holder_analysis,
            include_twitter_analysis=include_twitter_analysis,
            db_session=db
        )
        
        if not analysis_result:
            raise NotFoundError(
                f"Token {token_address} not found",
                {"token_address": token_address}
            )
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        await performance_manager.record_request("analyze_token", "POST", duration)
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing token {token_address}: {str(e)}")
        await performance_manager.record_error("analyze_token", str(type(e).__name__))
        if isinstance(e, NotFoundError):
            raise
        raise DatabaseError(
            "Failed to analyze token",
            {"token_address": token_address, "error": str(e)}
        )

@app.post("/analyze/wallet")
async def analyze_wallet(
    wallet_address: str,
    include_transaction_history: bool = True,
    db=Depends(get_db)
):
    """Analyze a wallet's trading history and behavior."""
    try:
        start_time = datetime.utcnow()
        
        analyzer = WalletAnalyzer(db_session=db)
        analysis = await analyzer.analyze_wallet(
            wallet_address,
            include_history=include_transaction_history
        )
        
        if not analysis:
            raise NotFoundError(
                f"Wallet {wallet_address} not found",
                {"wallet_address": wallet_address}
            )
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        await performance_manager.record_request("analyze_wallet", "POST", duration)
            
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing wallet {wallet_address}: {str(e)}")
        await performance_manager.record_error("analyze_wallet", str(type(e).__name__))
        if isinstance(e, NotFoundError):
            raise
        raise DatabaseError(
            "Failed to analyze wallet",
            {"wallet_address": wallet_address, "error": str(e)}
        )

@app.get("/blacklist/stats")
async def get_blacklist_stats(db=Depends(get_db)):
    """Get statistics about blacklisted addresses."""
    try:
        start_time = datetime.utcnow()
        stats = await blacklist_manager.get_stats()
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        await performance_manager.record_request("blacklist_stats", "GET", duration)
        
        return stats
    except Exception as e:
        logger.error(f"Error getting blacklist stats: {str(e)}")
        await performance_manager.record_error("blacklist_stats", str(type(e).__name__))
        raise DatabaseError("Failed to get blacklist stats", {"error": str(e)})

@app.get("/monitor/status")
async def get_monitor_status(db=Depends(get_db)):
    """Get current monitoring status."""
    try:
        start_time = datetime.utcnow()
        
        # Get monitoring data
        status = {
            "status": "active",
            "last_update": datetime.utcnow(),
            "monitored_tokens": await TokenLaunchCollector(db_session=db).get_monitored_count(),
            "active_alerts": await suspicious_analyzer.get_active_alerts_count(db_session=db),
            "performance_metrics": await performance_manager.get_performance_metrics()
        }
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        await performance_manager.record_request("monitor_status", "GET", duration)
        
        return status
    except Exception as e:
        logger.error(f"Error getting monitor status: {str(e)}")
        await performance_manager.record_error("monitor_status", str(type(e).__name__))
        raise DatabaseError("Failed to get monitor status", {"error": str(e)})

@app.get("/token/{token_address}")
async def get_token_data(token_address: str, db=Depends(get_db)):
    """Get all relevant data for a token."""
    try:
        start_time = datetime.utcnow()
        
        collector = TokenLaunchCollector(db_session=db)
        token_data = await collector.get_token_data(token_address)
        
        if not token_data:
            raise NotFoundError(
                f"Token {token_address} not found",
                {"token_address": token_address}
            )
        
        # Record metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        await performance_manager.record_request("get_token", "GET", duration)
            
        return token_data
    except Exception as e:
        logger.error(f"Error getting token data for {token_address}: {str(e)}")
        await performance_manager.record_error("get_token", str(type(e).__name__))
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
