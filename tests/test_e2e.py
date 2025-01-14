"""End-to-end system tests"""
import pytest
import asyncio
from typing import Dict
from datetime import datetime

from src.monitoring.token_monitor import TokenMonitor
from src.analysis.token_analysis import TokenAnalyzer
from src.analysis.holder_analysis import HolderAnalyzer
from src.analysis.deployer_analysis import DeployerAnalyzer
from src.notifications.notification_manager import NotificationManager
from src.events.event_manager import event_manager

import logging
import psutil
import time
from src.utils.recovery import recovery_manager, APIHealthMonitor, DatabaseRecoveryManager
from src.integrations.helius import HeliusAPI
from src.api.dashboard import app as dashboard_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemTestMetrics:
    """Tracks system metrics during tests"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.cpu_usage = []
        self.memory_usage = []
        self.event_counts = {}
        self.errors = []
        
    def start_monitoring(self):
        """Start monitoring system metrics"""
        self.start_time = datetime.now()
        self.cpu_usage = []
        self.memory_usage = []
        
    def record_metrics(self):
        """Record current system metrics"""
        process = psutil.Process()
        self.cpu_usage.append(process.cpu_percent())
        self.memory_usage.append(process.memory_info().rss)
        
    def stop_monitoring(self):
        """Stop monitoring and calculate final metrics"""
        self.end_time = datetime.now()
        return {
            "duration": (self.end_time - self.start_time).total_seconds(),
            "avg_cpu": sum(self.cpu_usage) / len(self.cpu_usage) if self.cpu_usage else 0,
            "max_cpu": max(self.cpu_usage) if self.cpu_usage else 0,
            "avg_memory": sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0,
            "max_memory": max(self.memory_usage) if self.memory_usage else 0,
            "event_counts": self.event_counts,
            "error_count": len(self.errors)
        }

@pytest.fixture
def metrics():
    """Create system metrics tracker"""
    return SystemTestMetrics()

@pytest.fixture
async def system_components():
    """Fixture to create system components for testing"""
    components = {
        "token_monitor": TokenMonitor(),
        "token_analyzer": TokenAnalyzer(),
        "holder_analyzer": HolderAnalyzer(),
        "deployer_analyzer": DeployerAnalyzer(),
        "notification_manager": NotificationManager()
    }
    
    # Initialize components
    for component in components.values():
        if hasattr(component, 'initialize'):
            await component.initialize()
    
    try:
        return components
    finally:
        # Cleanup components
        for component in components.values():
            if hasattr(component, 'cleanup'):
                await component.cleanup()

async def simulate_data_flow(components: Dict, metrics: SystemTestMetrics):
    """Simulate complete data flow through system"""
    try:
        metrics.start_monitoring()
        
        # Start token monitoring in background task
        monitor_task = asyncio.create_task(components["token_monitor"].start())
        
        try:
            # Simulate new token detection
            token_address = "So11111111111111111111111111111111111111112"
            
            # Analyze token
            token_analysis = await components["token_analyzer"].analyze_token(token_address)
            assert token_analysis is not None
            metrics.event_counts["token_analyzed"] = metrics.event_counts.get("token_analyzed", 0) + 1
            
            # Analyze holders
            holder_analysis = await components["holder_analyzer"].analyze_holders(token_address)
            assert holder_analysis is not None
            metrics.event_counts["holder_analysis_complete"] = metrics.event_counts.get("holder_analysis_complete", 0) + 1
            
            # Analyze deployer
            deployer_analysis = await components["deployer_analyzer"].analyze_deployer(token_address)
            assert deployer_analysis is not None
            metrics.event_counts["deployer_analysis_complete"] = metrics.event_counts.get("deployer_analysis_complete", 0) + 1
            
        finally:
            # Stop monitoring
            await components["token_monitor"].stop()
            await monitor_task
        
        # Record final metrics
        metrics.record_metrics()
        return metrics.stop_monitoring()
        
    except Exception as e:
        logger.error(f"Error in data flow simulation: {str(e)}")
        metrics.errors.append(str(e))
        raise

@pytest.mark.asyncio
async def test_complete_workflow(system_components, metrics):
    """Test complete system workflow"""
    try:
        # Get initialized components
        components = await system_components
        
        # Run data flow simulation
        results = await simulate_data_flow(components, metrics)
        
        # Verify metrics
        assert results["duration"] > 0
        assert results["avg_cpu"] > 0
        assert results["avg_memory"] > 0
        assert results["error_count"] == 0
        
        # Verify event counts
        assert results["event_counts"]["token_analyzed"] > 0
        assert results["event_counts"]["holder_analysis_complete"] > 0
        assert results["event_counts"]["deployer_analysis_complete"] > 0
        
    except Exception as e:
        logger.error(f"Error in complete workflow test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_cross_component_communication(system_components, metrics):
    """Test communication between components"""
    try:
        # Get initialized components
        components = await system_components
        
        # Start monitoring
        metrics.start_monitoring()
        
        # Subscribe to events
        events_received = []
        
        async def event_handler(event_data):
            events_received.append(event_data)
            
        event_manager.on("token_analyzed", event_handler)
        event_manager.on("holder_analysis_complete", event_handler)
        event_manager.on("deployer_analysis_complete", event_handler)
        
        # Trigger analysis
        token_address = "So11111111111111111111111111111111111111112"
        await components["token_analyzer"].analyze_token(token_address)
        await components["holder_analyzer"].analyze_holders(token_address)
        await components["deployer_analyzer"].analyze_deployer(token_address)
        
        # Wait for events
        await asyncio.sleep(1)
        
        # Verify events
        assert len(events_received) >= 3
        
        # Stop monitoring
        metrics.record_metrics()
        results = metrics.stop_monitoring()
        
        # Verify metrics
        assert results["error_count"] == 0
        
    except Exception as e:
        logger.error(f"Error in cross-component communication test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_data_consistency(system_components, metrics):
    """Test data consistency across components"""
    try:
        # Get initialized components
        components = await system_components
        
        # Start monitoring
        metrics.start_monitoring()
        
        # Analyze token
        token_address = "So11111111111111111111111111111111111111112"
        token_data = await components["token_analyzer"].analyze_token(token_address)
        
        # Verify token data
        assert token_data is not None
        assert "address" in token_data
        assert "risk_score" in token_data
        
        # Analyze holders
        holder_data = await components["holder_analyzer"].analyze_holders(token_address)
        
        # Verify holder data
        assert holder_data is not None
        assert "distribution" in holder_data
        assert "risk_factors" in holder_data
        
        # Analyze deployer
        deployer_data = await components["deployer_analyzer"].analyze_deployer(token_address)
        
        # Verify deployer data
        assert deployer_data is not None
        assert "deployer_address" in deployer_data
        assert "risk_score" in deployer_data
        
        # Stop monitoring
        metrics.record_metrics()
        results = metrics.stop_monitoring()
        
        # Verify metrics
        assert results["error_count"] == 0
        
    except Exception as e:
        logger.error(f"Error in data consistency test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_system_stability(system_components, metrics):
    """Test system stability under load"""
    try:
        # Get initialized components
        components = await system_components
        
        # Start monitoring
        metrics.start_monitoring()
        
        # Run multiple analyses in parallel
        token_addresses = [
            "So11111111111111111111111111111111111111112",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
        ]
        
        tasks = []
        for address in token_addresses:
            tasks.append(components["token_analyzer"].analyze_token(address))
            tasks.append(components["holder_analyzer"].analyze_holders(address))
            tasks.append(components["deployer_analyzer"].analyze_deployer(address))
            
        # Wait for all tasks
        await asyncio.gather(*tasks)
        
        # Stop monitoring
        metrics.record_metrics()
        results = metrics.stop_monitoring()
        
        # Verify metrics
        assert results["error_count"] == 0
        assert results["avg_cpu"] < 80  # CPU usage should be reasonable
        assert results["avg_memory"] < 1e9  # Memory usage should be under 1GB
        
    except Exception as e:
        logger.error(f"Error in system stability test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_resource_efficiency(system_components, metrics):
    """Test resource usage efficiency"""
    try:
        # Get initialized components
        components = await system_components
        
        # Start monitoring
        metrics.start_monitoring()
        
        # Run analysis
        token_address = "So11111111111111111111111111111111111111112"
        await components["token_analyzer"].analyze_token(token_address)
        
        # Stop monitoring
        metrics.record_metrics()
        results = metrics.stop_monitoring()
        
        # Verify resource usage
        assert results["avg_cpu"] < 50  # CPU usage should be under 50%
        assert results["max_memory"] < 5e8  # Max memory under 500MB
        assert results["error_count"] == 0
        
    except Exception as e:
        logger.error(f"Error in resource efficiency test: {str(e)}")
        raise

def test_documentation():
    """Verify system documentation"""
    try:
        # Check module docstrings
        assert TokenAnalyzer.__doc__ is not None, "TokenAnalyzer missing module docstring"
        assert HolderAnalyzer.__doc__ is not None, "HolderAnalyzer missing module docstring"
        assert DeployerAnalyzer.__doc__ is not None, "DeployerAnalyzer missing module docstring"
        assert TokenMonitor.__doc__ is not None, "TokenMonitor missing module docstring"
        
        # Check main functions
        assert TokenAnalyzer.analyze_token.__doc__ is not None, "analyze_token missing docstring"
        assert HolderAnalyzer.analyze_holders.__doc__ is not None, "analyze_holders missing docstring"
        assert DeployerAnalyzer.analyze_deployer.__doc__ is not None, "analyze_deployer missing docstring"
        assert TokenMonitor.start.__doc__ is not None, "start missing docstring"
        
    except Exception as e:
        pytest.fail(f"Documentation test failed: {str(e)}")
