"""Dashboard API endpoints"""
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import json
import os
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import plotly.utils
import pytz
from pathlib import Path
import logging
from typing import Dict, List, Optional, Set
import asyncio
from contextlib import asynccontextmanager

from ..models.token_analysis import TokenAnalysis
from ..monitor.token_monitor import TokenMonitor
from ..analysis.analysis_tools import AnalysisTools
from ..reporting.report_generator import ReportGenerator
from ..security.security_manager import SecurityManager, rate_limit
from ..monitoring.performance_manager import PerformanceManager
from ..database.connection import db_manager
from ..database.models import Token, TokenPrice, TokenHolder, TokenTransaction, WalletAnalysis
from ..events.event_manager import event_manager
from .wallet import router as wallet_router
from .alerts import router as alerts_router
from ..collectors.background_tasks import init_background_tasks

# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Solana Token Monitor",
    description="Dashboard for monitoring Solana token activity",
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

# Add Gzip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize templates
templates = Jinja2Templates(directory=str(static_dir / "templates"))

# Initialize components
security_manager = SecurityManager()
performance_manager = PerformanceManager()
token_monitor = TokenMonitor()
analysis_tools = AnalysisTools()
report_generator = ReportGenerator()

# WebSocket connections
active_connections: Set[WebSocket] = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the API"""
    try:
        # Initialize components
        await db_manager.initialize()
        await event_manager.initialize()
        await token_monitor.initialize()
        
        # Start background tasks
        background_tasks = await init_background_tasks()
        
        yield
        
        # Cleanup
        for task in background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        await token_monitor.close()
        await event_manager.close()
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Error in API lifecycle: {str(e)}")
        raise

app.lifespan = lifespan

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Track request performance"""
    start_time = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start_time).total_seconds()
    
    # Record metrics
    await performance_manager.record_request_metric(
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration=duration
    )
    
    return response

@app.middleware("http")
async def error_handler(request: Request, call_next):
    """Global error handling middleware"""
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    try:
        await websocket.accept()
        active_connections.add(websocket)
        
        try:
            while True:
                data = await websocket.receive_text()
                # Process incoming messages if needed
                
        except WebSocketDisconnect:
            pass
            
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        
    finally:
        active_connections.remove(websocket)

async def broadcast_update(message: Dict):
    """Broadcast update to all connected clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {str(e)}")
            active_connections.remove(connection)

@app.get("/")
async def root(request: Request):
    """Redirect to dashboard"""
    return {"message": "Welcome to Solana Token Monitor API"}

@app.get("/dashboard")
@rate_limit()
async def dashboard(request: Request):
    """Main dashboard view"""
    try:
        # Get monitored tokens
        tokens = await token_monitor.get_monitored_tokens()
        
        # Get system metrics
        metrics = await performance_manager.get_current_metrics()
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "tokens": tokens,
                "metrics": metrics
            }
        )
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tokens/{token_address}")
@rate_limit()
async def get_token_analysis(token_address: str):
    """Get token analysis"""
    try:
        analysis = await analysis_tools.analyze_token(token_address)
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Token analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/monitor/add")
@rate_limit()
async def add_token_monitor(token_address: str):
    """Add token to monitoring"""
    try:
        await token_monitor.add_token(token_address)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding token monitor: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db_healthy = await db_manager.check_connection()
        
        # Check event system
        event_healthy = event_manager.is_healthy()
        
        # Check token monitor
        monitor_healthy = await token_monitor.check_health()
        
        status = "healthy" if all([db_healthy, event_healthy, monitor_healthy]) else "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "components": {
                "database": "healthy" if db_healthy else "unhealthy",
                "events": "healthy" if event_healthy else "unhealthy",
                "monitor": "healthy" if monitor_healthy else "unhealthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Include routers
app.include_router(wallet_router, prefix="/api/wallet", tags=["wallet"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["alerts"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=True)
