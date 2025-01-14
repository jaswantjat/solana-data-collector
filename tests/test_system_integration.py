"""Integration tests for the Solana token monitoring system"""
import pytest
import asyncio
import logging
from typing import Dict
from datetime import datetime

from src.monitoring.token_monitor import TokenMonitor
from src.analysis.token_analysis import TokenAnalyzer
from src.analysis.holder_analysis import HolderAnalyzer
from src.analysis.deployer_analysis import DeployerAnalyzer
from src.analysis.activity_analysis import ActivityAnalyzer
from src.notifications.notification_manager import NotificationManager
from src.events.event_manager import event_manager

from src.core.system_integrator import system
from src.database.models import Token, TokenPrice, TokenHolder

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def setup_teardown():
    """Setup and teardown for all tests"""
    # Clear any existing event handlers
    event_manager.clear_all_handlers()
    event_manager.timeout = 5.0  # Set shorter timeout for tests
    
    yield
    
    # Cleanup after tests
    event_manager.clear_all_handlers()
    await event_manager.wait_for_handlers()

@pytest.fixture
def mock_token():
    """Create a mock token for testing"""
    return {
        "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "symbol": "TEST",
        "name": "Test Token",
        "decimals": 9,
        "supply": "1000000000",
        "holders": 100,
        "price": "1.0",
        "volume_24h": "1000000",
        "holder_concentration": 0.8,
        "price_volatility": 0.7,
        "volume_change": 0.7
    }

@pytest.fixture
def mock_transactions():
    """Create mock transactions for testing"""
    return [
        {
            "token_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "signature": "tx1",
            "from_address": "holder1",
            "amount": 1000,
            "timestamp": datetime.now().isoformat()
        },
        {
            "token_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "signature": "tx2",
            "from_address": "holder2",
            "amount": 500,
            "timestamp": datetime.now().isoformat()
        }
    ]

@pytest.fixture
async def test_system():
    """Create test system with all components"""
    token_analyzer = TokenAnalyzer()
    holder_analyzer = HolderAnalyzer()
    deployer_analyzer = DeployerAnalyzer()
    activity_analyzer = ActivityAnalyzer()
    notification_manager = NotificationManager()
    
    components = {
        "token_monitor": TokenMonitor(
            token_analyzer=token_analyzer,
            holder_analyzer=holder_analyzer,
            deployer_analyzer=deployer_analyzer,
            activity_analyzer=activity_analyzer
        ),
        "token_analyzer": token_analyzer,
        "holder_analyzer": holder_analyzer,
        "deployer_analyzer": deployer_analyzer,
        "activity_analyzer": activity_analyzer,
        "notification_manager": notification_manager
    }
    
    try:
        # Initialize components
        for component in components.values():
            if hasattr(component, 'initialize'):
                await component.initialize()
                
        # Start components
        for component in components.values():
            if hasattr(component, 'start'):
                await component.start()
        
        return components
        
    except Exception as e:
        logger.error(f"Error setting up test system: {str(e)}")
        # Ensure cleanup on setup failure
        await cleanup_components(components)
        raise
        
    finally:
        # Register cleanup to run after test
        pytest.fixture(autouse=True)(lambda: cleanup_components(components))

async def cleanup_components(components):
    """Helper to cleanup test components"""
    if not components:
        return
        
    # Shutdown components in reverse order
    for component in reversed(list(components.values())):
        try:
            if hasattr(component, 'shutdown'):
                await component.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down component {component.__class__.__name__}: {str(e)}")
    
    # Wait for any pending tasks
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_system_initialization(test_system):
    """Test system initialization"""
    # Get initialized components
    components = await test_system
    
    # Verify all components are initialized
    assert components["token_monitor"] is not None
    assert components["token_analyzer"] is not None
    assert components["holder_analyzer"] is not None
    assert components["deployer_analyzer"] is not None
    assert components["notification_manager"] is not None
    
    # Check health status
    health = await components["token_monitor"].check_health()
    assert health["status"] == "healthy"
    assert health["apis_healthy"] is True
    
    # Verify token monitor is ready
    assert components["token_monitor"].is_running is True
    assert len(components["token_monitor"].tasks) > 0

@pytest.mark.asyncio
async def test_new_token_detection(test_system, mock_token):
    """Test new token detection and analysis"""
    # Get initialized system
    components = await test_system
    
    # Create future to wait for analysis completion
    analysis_complete = asyncio.Future()
    
    # Register event handler
    async def on_analysis_complete(event):
        if not analysis_complete.done():
            analysis_complete.set_result(event.data)
    
    event_manager.on("token_analysis_complete", on_analysis_complete)
    
    try:
        # Emit new token event
        await event_manager.emit("new_token_detected", mock_token)
        
        # Wait for analysis with timeout
        analysis_data = await asyncio.wait_for(analysis_complete, timeout=5.0)
        
        # Verify analysis data
        assert analysis_data is not None
        assert analysis_data["token_address"] == mock_token["address"]
        assert "metrics" in analysis_data
        assert "timestamp" in analysis_data
        
    finally:
        # Cleanup
        event_manager.off("token_analysis_complete", on_analysis_complete)
        await event_manager.wait_for_handlers()

@pytest.mark.asyncio
async def test_holder_analysis(test_system, mock_token):
    """Test holder analysis"""
    # Get initialized system
    components = await test_system
    
    # Create future to wait for analysis completion
    analysis_complete = asyncio.Future()
    
    # Register event handler
    async def on_analysis_complete(event):
        if not analysis_complete.done():
            analysis_complete.set_result(event.data)
    
    event_manager.on("holder_analysis_complete", on_analysis_complete)
    
    try:
        # Start analysis
        await components["holder_analyzer"].analyze_holders(mock_token["address"])
        
        # Wait for analysis with timeout
        analysis_data = await asyncio.wait_for(analysis_complete, timeout=5.0)
        
        # Verify analysis data
        assert analysis_data is not None
        assert analysis_data["token_address"] == mock_token["address"]
        assert "distribution" in analysis_data
        assert "risk_factors" in analysis_data
        
    finally:
        # Cleanup
        event_manager.off("holder_analysis_complete", on_analysis_complete)
        await event_manager.wait_for_handlers()

@pytest.mark.asyncio
async def test_suspicious_activity_detection(test_system, mock_token, mock_transactions):
    """Test suspicious activity detection"""
    # Get initialized system
    components = await test_system
    
    # Create future to wait for detection
    detection_complete = asyncio.Future()
    
    # Register event handler
    async def on_suspicious_activity(event):
        if not detection_complete.done():
            detection_complete.set_result(event.data)
    
    event_manager.on("suspicious_activity", on_suspicious_activity)
    
    try:
        # Emit transaction events
        for tx in mock_transactions:
            await event_manager.emit("transaction_detected", tx)
        
        # Wait for detection with timeout
        detection_data = await asyncio.wait_for(detection_complete, timeout=5.0)
        
        # Verify detection data
        assert detection_data is not None
        assert detection_data["token_address"] == mock_token["address"]
        assert detection_data["activity_type"] == "high_risk_score"
        assert detection_data["risk_level"] == "high"
        
    finally:
        # Cleanup
        event_manager.off("suspicious_activity", on_suspicious_activity)
        await event_manager.wait_for_handlers()

@pytest.mark.asyncio
async def test_price_monitoring(test_system, mock_token):
    """Test price monitoring and alerts"""
    # Get initialized system
    components = await test_system
    
    # Create price change event
    price_change = {
        "token_address": mock_token["address"],
        "old_price": 1.0,
        "new_price": 2.0,
        "percent_change": 100.0,
        "timestamp": datetime.now().isoformat()
    }
    
    # Create future to wait for alert
    alert_received = asyncio.Future()
    
    # Register event handler
    async def on_alert(event):
        if not alert_received.done():
            alert_received.set_result(event.data)
    
    event_manager.on("alert_generated", on_alert)
    
    try:
        # Emit price alert
        await event_manager.emit("price_alert", price_change)
        
        # Wait for alert with timeout
        alert_data = await asyncio.wait_for(alert_received, timeout=5.0)
        
        # Verify alert data
        assert alert_data is not None
        assert alert_data["token_address"] == mock_token["address"]
        assert alert_data["alert_type"] == "price_change"
        assert alert_data["severity"] == "high"
        
    finally:
        # Cleanup
        event_manager.off("alert_generated", on_alert)
        await event_manager.wait_for_handlers()

@pytest.mark.asyncio
async def test_concurrent_operations(test_system, mock_token):
    """Test system handling of concurrent operations"""
    # Get initialized system
    components = await test_system
    
    # Create multiple concurrent tasks
    tasks = []
    for _ in range(5):
        tasks.append(
            components["token_analyzer"].analyze_token(mock_token)
        )
    
    try:
        # Run tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all tasks completed successfully
        for result in results:
            assert not isinstance(result, Exception)
            assert result is not None
            assert result["token_address"] == mock_token["address"]
            assert "metrics" in result
            assert "timestamp" in result
            
    finally:
        # Wait for any pending handlers
        await event_manager.wait_for_handlers()

@pytest.mark.asyncio
async def test_system_shutdown(test_system):
    """Test system shutdown procedure"""
    # Get initialized system
    components = await test_system
    
    try:
        # Wait briefly for tasks to start
        await asyncio.sleep(0.1)
        
        # Initiate shutdown
        await components["token_monitor"].shutdown()
        
        # Verify all tasks are cancelled
        assert len(components["token_monitor"].tasks) == 0
        
        # Verify components are closed
        health = await components["token_monitor"].check_health()
        assert health["status"] == "shutdown"
        
    finally:
        # Wait for any pending handlers
        await event_manager.wait_for_handlers()
