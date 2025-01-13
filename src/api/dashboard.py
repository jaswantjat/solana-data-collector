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
from typing import Dict, List, Optional
import asyncio
from src.models.token_analysis import TokenAnalysis
from src.monitor.token_monitor import TokenMonitor
from src.analysis.analysis_tools import AnalysisTools
from src.reporting.report_generator import ReportGenerator
from src.security.security_manager import SecurityManager, rate_limit
from src.monitoring.performance_manager import PerformanceManager
from src.database.database_manager import DatabaseManager
from src.database.models import Token, TokenPrice, TokenHolder, TokenTransaction, WalletAnalysis
from .wallet import router as wallet_router
from .alerts import router as alerts_router
from src.collectors.background_tasks import init_background_tasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Solana Token Monitor",
    description="Dashboard for monitoring Solana token launches on pump.fun",
    version="1.0.0"
)

# Include routers
app.include_router(wallet_router, prefix="/api", tags=["wallets"])
app.include_router(alerts_router, prefix="/api", tags=["alerts"])

# Setup static and templates directories
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Initialize components
token_monitor = None
analysis_tools = None
report_generator = None
security_manager = None
performance_manager = None
database_manager = None
background_tasks = set()

# Store active websocket connections
websocket_connections = set()

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.on_event("startup")
async def startup_event():
    """Initialize components and background tasks"""
    global token_monitor, analysis_tools, report_generator, security_manager, performance_manager, database_manager, background_tasks
    
    # Initialize components
    token_monitor = TokenMonitor()
    analysis_tools = AnalysisTools()
    report_generator = ReportGenerator()
    security_manager = SecurityManager()
    performance_manager = PerformanceManager()
    database_manager = DatabaseManager()
    
    # Initialize database
    await database_manager.initialize()
    
    # Store managers in app state
    app.state.security_manager = security_manager
    app.state.performance_manager = performance_manager
    app.state.database_manager = database_manager
    
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
    
    # Start monitoring tasks
    monitoring_task = asyncio.create_task(token_monitor.run())
    background_tasks.add(monitoring_task)
    monitoring_task.add_done_callback(background_tasks.discard)
    
    # Start performance monitoring
    perf_task = asyncio.create_task(performance_manager.monitor_system_health())
    background_tasks.add(perf_task)
    perf_task.add_done_callback(background_tasks.discard)
    
    # Start data cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())
    background_tasks.add(cleanup_task)
    cleanup_task.add_done_callback(background_tasks.discard)
    
    # Start data refresh task
    refresh_task = asyncio.create_task(refresh_token_data())
    background_tasks.add(refresh_task)
    refresh_task.add_done_callback(background_tasks.discard)
    
    # Start backup task
    backup_task = asyncio.create_task(periodic_backup())
    background_tasks.add(backup_task)
    backup_task.add_done_callback(background_tasks.discard)

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Middleware to track request performance"""
    start_time = time.time()
    response = await call_next(request)
    
    # Record response time
    response_time = time.time() - start_time
    await performance_manager.record_response_time(
        request.url.path,
        response_time
    )
    
    return response

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks and connections"""
    # Cleanup background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)
    
    # Close Redis connection
    if security_manager and security_manager.redis:
        await security_manager.redis.close()

async def periodic_backup():
    """Periodically backup system data"""
    while True:
        try:
            # Backup token data
            token_data = token_monitor.get_token_data() if token_monitor else {}
            await security_manager.backup_data(token_data, "token_data")
            
            # Backup analysis data
            analysis_data = analysis_tools.get_analysis_data() if analysis_tools else {}
            await security_manager.backup_data(analysis_data, "analysis_data")
            
            logger.info("System backup completed")
            
        except Exception as e:
            logger.error(f"Backup error: {str(e)}")
            
        await asyncio.sleep(3600)  # Backup every hour

async def periodic_cleanup():
    """Periodically cleanup old data"""
    while True:
        try:
            await database_manager.cleanup_old_data(days=30)
            logger.info("Database cleanup completed")
        except Exception as e:
            logger.error(f"Database cleanup error: {str(e)}")
        await asyncio.sleep(86400)  # Run daily

async def validate_request(request: Request):
    """Validate request middleware"""
    try:
        if security_manager:
            await security_manager.validate_request(request)
    except HTTPException as e:
        security_manager.audit_log("request_rejected", {
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host,
            "reason": str(e.detail)
        })
        raise
    except Exception as e:
        logger.error(f"Request validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Add request validation middleware
app.middleware("http")(validate_request)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.add(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

async def broadcast_token_updates():
    """Broadcast token updates to all connected clients"""
    if not websocket_connections:
        return
        
    try:
        if token_monitor:
            tokens = await token_monitor.get_recent_tokens()
            
            # Calculate stats
            total_confidence = sum(t.get("analysis_score", 0) for t in tokens)
            avg_confidence = total_confidence / len(tokens) if tokens else 0
            
            # Prepare update data
            update_data = {
                "tokens": tokens,
                "stats": {
                    "total_tokens": len(tokens),
                    "avg_analysis_score": avg_confidence
                }
            }
            
            # Broadcast to all clients
            for connection in websocket_connections:
                try:
                    await connection.send_json(update_data)
                except Exception as e:
                    logger.error(f"Error sending update to client: {str(e)}")
                    websocket_connections.remove(connection)
                    
    except Exception as e:
        logger.error(f"Error broadcasting updates: {str(e)}")

async def refresh_token_data():
    """Periodically refresh token data"""
    while True:
        try:
            if token_monitor:
                await token_monitor.monitor_new_tokens()
                await broadcast_token_updates()
                logger.info("Refreshed token data")
        except Exception as e:
            logger.error(f"Error refreshing token data: {str(e)}")
        await asyncio.sleep(10)  # Refresh every 10 seconds

@app.get("/api/system/metrics")
@rate_limit("high_priority")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        metrics = await performance_manager.get_performance_metrics()
        return JSONResponse(content={
            "response_time": metrics.response_time,
            "cpu_usage": metrics.cpu_usage,
            "memory_usage": metrics.memory_usage,
            "active_connections": metrics.active_connections,
            "cache_hit_rate": metrics.cache_hit_rate,
            "error_rate": metrics.error_rate
        })
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/metrics/history/{metric_type}")
@rate_limit("normal")
async def get_metrics_history(metric_type: str, hours: int = 24):
    """Get historical metrics"""
    try:
        history = await performance_manager.get_metrics_history(metric_type, hours)
        return JSONResponse(content=history)
    except Exception as e:
        logger.error(f"Error getting metrics history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def load_json_file(filename: str) -> Dict:
    """Load JSON file from data directory"""
    try:
        file_path = DATA_DIR / filename
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {filename}: {str(e)}")
    return {}

def parse_datetime(date_str: str) -> datetime:
    """Parse datetime string to datetime object"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
    except Exception:
        return datetime.now(pytz.UTC)

def calculate_token_age(created_at: str) -> int:
    """Calculate token age in days"""
    try:
        created_date = parse_datetime(created_at)
        now = datetime.now(pytz.UTC)
        return (now - created_date).days
    except Exception:
        return 0

def generate_token_chart(token_data: List[Dict], timeframe: str = "1D") -> str:
    """Generate token price and volume chart"""
    try:
        # Convert data to pandas DataFrame
        df = pd.DataFrame(token_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Create figure with secondary y-axis
        fig = go.Figure()

        # Add price line
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['price'],
                name="Price",
                line=dict(color='#2196f3', width=2)
            )
        )

        # Add volume bars
        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['volume'],
                name="Volume",
                marker_color='rgba(158,158,158,0.2)',
                yaxis='y2'
            )
        )

        # Update layout
        fig.update_layout(
            title=dict(
                text="Token Price and Volume",
                x=0.5,
                xanchor='center'
            ),
            xaxis=dict(
                title="Time",
                gridcolor='rgba(158,158,158,0.1)',
                showgrid=True
            ),
            yaxis=dict(
                title="Price (USD)",
                gridcolor='rgba(158,158,158,0.1)',
                showgrid=True,
                side='left'
            ),
            yaxis2=dict(
                title="Volume (USD)",
                overlaying='y',
                side='right'
            ),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            ),
            template='plotly_dark',
            hovermode='x unified',
            margin=dict(l=0, r=0, t=30, b=0)
        )

        # Convert to JSON
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return "{}"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard"""
    return await dashboard(request)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard view"""
    try:
        # Get token monitor data
        token_data = []
        if token_monitor:
            # Get recent tokens from monitor
            recent_tokens = await token_monitor.get_recent_tokens()
            
            # Calculate average confidence
            total_confidence = sum(t.get("analysis_score", 0) for t in recent_tokens)
            avg_confidence = total_confidence / len(recent_tokens) if recent_tokens else 0
            
            # Process tokens
            token_data = []
            for token in recent_tokens:
                # Format token data
                token_data.append({
                    "address": token.get("address"),
                    "name": token.get("name"),
                    "symbol": token.get("symbol"),
                    "market_cap": token.get("market_cap", 0),
                    "price": token.get("price", 0),
                    "price_change_24h": token.get("price_change_24h", 0),
                    "distribution_score": token.get("distribution_score", 0),
                    "contract_score": token.get("contract_score", 0),
                    "deployer_score": token.get("deployer_score", 0),
                    "holder_count": token.get("holder_count", 0),
                    "whale_count": token.get("whale_count", 0),
                    "mentions": token.get("mentions", 0),
                    "top_holder_win_rate": token.get("top_holder_win_rate", 0),
                    "analysis_score": token.get("analysis_score", 0),
                    "age_days": token.get("age_days", 0),
                    "volume": token.get("volume", 0),
                    "volume_history": token.get("volume_history", [])
                })

        # Sort tokens by analysis score
        token_data.sort(key=lambda x: x["analysis_score"], reverse=True)

        # Calculate statistics
        stats = {
            "total_tokens": len(token_data),
            "avg_analysis_score": avg_confidence
        }

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "tokens": token_data,
                "stats": stats
            }
        )

    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tokens/screen")
@rate_limit("high_priority")
async def screen_tokens(request: Request):
    """Screen tokens based on criteria"""
    try:
        # Try to get cached results
        cache_key = f"token_screen_{hash(str(request.query_params))}"
        cached_data = await performance_manager.get_cached_data(cache_key)
        if cached_data:
            return JSONResponse(content=cached_data)
            
        # Get fresh data
        criteria = await request.json()
        results = await analysis_tools.screen_tokens(criteria)
        
        # Store results in database
        for token_data in results:
            await database_manager.add_token(token_data)
            
        # Cache results
        await performance_manager.set_cached_data(cache_key, results, ttl=300)
        
        # Audit log
        security_manager.audit_log("token_screen", {
            "criteria": criteria,
            "results_count": len(results)
        })
        
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"Token screening error: {str(e)}")
        performance_manager.record_error("token_screen_error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallet/analyze/{address}")
@rate_limit("normal")
async def analyze_wallet(address: str, request: Request):
    """Analyze wallet"""
    try:
        # Try to get cached results
        cache_key = f"wallet_analysis_{address}"
        cached_data = await performance_manager.get_cached_data(cache_key)
        if cached_data:
            return JSONResponse(content=cached_data)
            
        # Check database
        wallet_analysis = await database_manager.get_wallet_analysis(address)
        if wallet_analysis and (datetime.utcnow() - wallet_analysis.created_at).total_seconds() < 3600:
            return JSONResponse(content=wallet_analysis.analysis_data)
            
        # Get fresh data
        analysis = await analysis_tools.analyze_wallet(address)
        
        # Store in database
        await database_manager.add_wallet_analysis({
            "wallet_address": address,
            "analysis_data": analysis,
            "token_count": len(analysis.get("tokens", [])),
            "total_value_usd": analysis.get("total_value_usd", 0),
            "transaction_count": analysis.get("transaction_count", 0),
            "first_transaction": analysis.get("first_transaction"),
            "last_transaction": analysis.get("last_transaction")
        })
        
        # Cache results
        await performance_manager.set_cached_data(cache_key, analysis, ttl=1800)
        
        # Audit log
        security_manager.audit_log("wallet_analysis", {
            "address": address,
            "client_ip": request.client.host
        })
        
        return JSONResponse(content=analysis)
    except Exception as e:
        logger.error(f"Wallet analysis error: {str(e)}")
        performance_manager.record_error("wallet_analysis_error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions/explore")
async def explore_transactions(request: Request):
    """Explore transactions"""
    try:
        query = await request.json()
        results = await analysis_tools.explore_transactions(query)
        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patterns/recognize")
async def recognize_patterns(request: Request):
    """Recognize patterns"""
    try:
        data = await request.json()
        patterns = await analysis_tools.recognize_patterns(
            data["data"],
            data["pattern_type"]
        )
        return JSONResponse(content=patterns)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/risk/calculate")
async def calculate_risk(request: Request):
    """Calculate risk score"""
    try:
        data = await request.json()
        risk_score = await analysis_tools.calculate_risk_score(
            data["target"],
            data["target_type"]
        )
        return JSONResponse(content=risk_score)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/performance/{token_address}")
async def get_performance_report(token_address: str):
    """Get performance report"""
    try:
        report = await report_generator.generate_performance_report(token_address)
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/risk/{token_address}")
async def get_risk_report(token_address: str):
    """Get risk report"""
    try:
        report = await report_generator.generate_risk_report(token_address)
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/wallet/{wallet_address}")
async def get_wallet_report(wallet_address: str):
    """Get wallet report"""
    try:
        report = await report_generator.generate_wallet_report(wallet_address)
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/market")
async def get_market_report():
    """Get market trend report"""
    try:
        report = await report_generator.generate_market_report()
        return JSONResponse(content=report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/alerts/configure")
async def configure_alert(request: Request):
    """Configure custom alert"""
    try:
        config = await request.json()
        success = report_generator.configure_alert(config)
        return JSONResponse(content={"success": success})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    try:
        # Check database connection
        db_health = await database_manager.health_check()
        cache_health = await performance_manager.health_check()
        
        status = "healthy"
        if db_health["status"] != "healthy" or cache_health["status"] != "healthy":
            status = "degraded"
            
        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "database": db_health,
            "cache": cache_health,
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8000, reload=True)
