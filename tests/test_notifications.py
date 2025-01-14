import pytest
import asyncio
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.notifications.notification_manager import NotificationManager
from src.events.event_manager import event_manager, EventManager

# Test data
TEST_WEBHOOK_URL = "https://discord.com/api/webhooks/test"
TEST_ALERT_RULES = {
    "1": {
        "conditions": [
            {
                "field": "price_change",
                "operator": "greater_than",
                "value": "10"
            }
        ],
        "priority": "high",
        "enabled": True
    },
    "2": {
        "conditions": [
            {
                "field": "volume",
                "operator": "less_than",
                "value": "1000"
            }
        ],
        "priority": "low",
        "enabled": True
    }
}

@pytest.fixture(autouse=True)
async def reset_event_manager():
    """Reset event manager before each test"""
    await asyncio.sleep(0)  # Ensure event loop is running
    event_manager.reset()
    yield
    # Clean up any pending tasks
    await asyncio.sleep(0)  # Allow pending tasks to complete

@pytest.fixture
def notification_manager():
    """Create a notification manager for testing"""
    with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": TEST_WEBHOOK_URL}):
        manager = NotificationManager()
        # Mock alert rules
        manager.alert_rules = TEST_ALERT_RULES
        return manager

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session"""
    class MockResponse:
        def __init__(self, status):
            self.status = status
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    class MockSession:
        def __init__(self):
            self.last_request = None
            self.response_status = 204
            
        def post(self, url, json=None):
            self.last_request = {"url": url, "json": json}
            return MockResponse(self.response_status)
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
            
    return MockSession()

@pytest.mark.asyncio
async def test_discord_notification_success(notification_manager, mock_aiohttp_session):
    """Test successful Discord notification"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        # Create an event to store notifications
        notifications_sent = []
        
        async def on_notification(event):
            notifications_sent.append(event.data)
        
        event_manager.subscribe("notification_sent", on_notification)
        
        content = {
            "title": "Test Alert",
            "description": "Test Description",
            "priority": "high"
        }
        
        # Send notification
        success = await notification_manager.send_discord_notification(content, "high")
        
        # Wait for events to process
        await asyncio.sleep(0.1)
        
        assert success == True
        assert len(notifications_sent) == 1
        assert notifications_sent[0]["title"] == "Test Alert"
        assert notifications_sent[0]["description"] == "Test Description"
        assert notifications_sent[0]["priority"] == "high"
        
        # Verify request
        request = mock_aiohttp_session.last_request
        assert request["url"] == TEST_WEBHOOK_URL
        assert request["json"]["embeds"][0]["title"] == "Test Alert"
        assert request["json"]["embeds"][0]["description"] == "Test Description"
        assert request["json"]["embeds"][0]["color"] == 0xFF0000  # Red for high priority
        
        # Cleanup
        event_manager.unsubscribe("notification_sent", on_notification)

@pytest.mark.asyncio
async def test_discord_notification_rate_limit(notification_manager, mock_aiohttp_session):
    """Test Discord notification rate limiting"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        # Create an event to store notifications
        notifications_sent = []
        
        async def on_notification(event):
            notifications_sent.append(event.data)
        
        event_manager.subscribe("notification_sent", on_notification)
        
        content = {"title": "Rate Limit Test"}
        
        # Send multiple notifications quickly
        results = []
        for _ in range(5):
            success = await notification_manager.send_discord_notification(content)
            results.append(success)
            await asyncio.sleep(0.1)  # Small delay
            
        # Wait for events to process
        await asyncio.sleep(0.1)
            
        # All should succeed with rate limiting
        assert all(results)
        assert len(notifications_sent) == 5
        
        # Cleanup
        event_manager.unsubscribe("notification_sent", on_notification)

@pytest.mark.asyncio
async def test_alert_rule_matching(notification_manager):
    """Test alert rule condition matching"""
    # Test high priority alert
    alert_data = {
        "price_change": "15",
        "volume": "2000"
    }
    
    matches = notification_manager._matches_conditions(
        alert_data,
        TEST_ALERT_RULES["1"]["conditions"]
    )
    assert matches == True
    
    # Test non-matching alert
    alert_data = {
        "price_change": "5",
        "volume": "2000"
    }
    
    matches = notification_manager._matches_conditions(
        alert_data,
        TEST_ALERT_RULES["1"]["conditions"]
    )
    assert matches == False

@pytest.mark.asyncio
async def test_alert_processing(notification_manager, mock_aiohttp_session):
    """Test alert processing with rules"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        # Create an event to store notifications
        notifications_sent = []
        
        async def on_notification(event):
            notifications_sent.append(event.data)
        
        event_manager.subscribe("notification_sent", on_notification)
        
        # Test alert that should trigger high priority notification
        alert_data = {
            "title": "Price Alert",
            "description": "Significant price change detected",
            "price_change": "15",
            "volume": "2000"
        }
        
        success = await notification_manager.process_alert(alert_data)
        
        # Wait for events to process
        await asyncio.sleep(0.1)
        
        assert success == True
        assert len(notifications_sent) == 1
        assert notifications_sent[0]["priority"] == "high"
        
        # Verify notification was sent with correct priority
        request = mock_aiohttp_session.last_request
        assert request["json"]["embeds"][0]["color"] == 0xFF0000  # Red for high priority
        
        # Cleanup
        event_manager.unsubscribe("notification_sent", on_notification)

@pytest.mark.asyncio
async def test_error_handling(notification_manager):
    """Test error handling in notifications"""
    # Create an event to store notifications
    notifications_sent = []
    
    async def on_notification(event):
        notifications_sent.append(event.data)
    
    event_manager.subscribe("notification_sent", on_notification)
    
    # Test with invalid webhook URL
    notification_manager.discord_webhook_url = "invalid_url"
    
    content = {"title": "Error Test"}
    success = await notification_manager.send_discord_notification(content)
    
    # Wait for events to process
    await asyncio.sleep(0.1)
    
    assert success == False
    assert len(notifications_sent) == 0
    
    # Cleanup
    event_manager.unsubscribe("notification_sent", on_notification)

def test_alert_rule_management(notification_manager):
    """Test alert rule CRUD operations"""
    # Test adding new rule
    new_rule = {
        "conditions": [
            {
                "field": "whale_movement",
                "operator": "greater_than",
                "value": "1000000"
            }
        ],
        "priority": "high"
    }
    
    # Add rule
    rule_id = notification_manager.add_alert_rule(new_rule)
    assert rule_id is not None
    
    # Get rule
    rule = notification_manager.get_alert_rule(rule_id)
    assert rule is not None
    assert rule["conditions"][0]["field"] == "whale_movement"
    assert rule["priority"] == "high"
    
    # Update rule
    updated_rule = {
        "conditions": [
            {
                "field": "whale_movement",
                "operator": "greater_than",
                "value": "2000000"
            }
        ],
        "priority": "medium"
    }
    success = notification_manager.update_alert_rule(rule_id, updated_rule)
    assert success == True
    
    # Delete rule
    success = notification_manager.delete_alert_rule(rule_id)
    assert success == True
    
    # Verify deletion
    rule = notification_manager.get_alert_rule(rule_id)
    assert rule is None

@pytest.mark.asyncio
async def test_event_integration(notification_manager, mock_aiohttp_session):
    """Test integration with event system"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        # Create an event to store notifications
        notifications_sent = []
        
        # Create an async event handler
        async def on_notification(event):
            notifications_sent.append(event.data)
        
        # Subscribe to events
        event_manager.subscribe("notification_sent", on_notification)
        
        # Add alert rule for testing
        test_rule = {
            "conditions": [
                {
                    "field": "price_change",
                    "operator": "greater_than",
                    "value": "10"
                }
            ],
            "priority": "high",
            "enabled": True
        }
        rule_id = notification_manager.add_alert_rule(test_rule)
        
        # Trigger alert that should send notification
        alert_data = {
            "title": "Event Test",
            "description": "Test Event",
            "price_change": "20",
            "volume": "5000"
        }
        
        success = await notification_manager.process_alert(alert_data)
        assert success == True
        
        # Wait for events to process
        await asyncio.sleep(0.5)
        
        # Verify notification was tracked
        assert len(notifications_sent) > 0
        assert notifications_sent[0]["title"] == "Event Test"
        assert notifications_sent[0]["description"] == "Test Event"
        assert notifications_sent[0]["priority"] == "high"
        
        # Cleanup
        event_manager.unsubscribe("notification_sent", on_notification)

@pytest.mark.benchmark(group="notification-performance")
@pytest.mark.asyncio
async def test_notification_performance(benchmark, notification_manager, mock_aiohttp_session):
    """Benchmark notification performance"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        content = {
            "title": "Performance Test",
            "description": "Testing notification performance",
            "fields": {
                "Price": "100",
                "Change": "+10%"
            }
        }
        
        async def run_notification():
            await notification_manager.send_discord_notification(content, "high")
            
        await benchmark(run_notification)

@pytest.mark.benchmark(group="alert-processing")
@pytest.mark.asyncio
async def test_alert_processing_performance(benchmark, notification_manager, mock_aiohttp_session):
    """Benchmark alert processing performance"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        alert_data = {
            "title": "Performance Test",
            "price_change": "15",
            "volume": "2000"
        }
        
        async def process_alert():
            await notification_manager.process_alert(alert_data)
            
        await benchmark(process_alert)

@pytest.mark.benchmark(group="event-handling")
@pytest.mark.asyncio
async def test_event_handling_performance(benchmark, notification_manager, mock_aiohttp_session):
    """Benchmark event handling performance"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        notifications_sent = []
        
        async def on_notification(event):
            notifications_sent.append(event.data)
            
        event_manager.subscribe("notification_sent", on_notification)
        
        content = {
            "title": "Event Performance Test",
            "description": "Testing event handling performance"
        }
        
        async def emit_and_handle():
            await notification_manager.send_discord_notification(content)
            await asyncio.sleep(0.1)  # Wait for event processing
            
        await benchmark(emit_and_handle)
        
        event_manager.unsubscribe("notification_sent", on_notification)

@pytest.mark.benchmark(group="alert-rule-matching")
def test_alert_rule_matching_performance(benchmark, notification_manager):
    """Benchmark alert rule matching performance"""
    alert_data = {
        "price_change": "15",
        "volume": "2000"
    }
    
    def match_rules():
        return notification_manager._matches_conditions(
            alert_data,
            TEST_ALERT_RULES["1"]["conditions"]
        )
        
    benchmark(match_rules)

@pytest.mark.benchmark(group="memory-usage")
@pytest.mark.asyncio
async def test_memory_usage(benchmark, notification_manager, mock_aiohttp_session):
    """Test memory usage under load"""
    with patch("aiohttp.ClientSession", return_value=mock_aiohttp_session):
        content = {
            "title": "Memory Test",
            "description": "Testing memory usage"
        }
        
        async def run_notifications():
            tasks = []
            for _ in range(100):  # Send 100 notifications
                task = notification_manager.send_discord_notification(content)
                tasks.append(task)
            await asyncio.gather(*tasks)
            
        # Monitor memory before and after
        import psutil
        import os
        
        def get_memory_usage():
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB
            
        memory_before = get_memory_usage()
        await benchmark(run_notifications)
        memory_after = get_memory_usage()
        
        print(f"Memory usage: Before={memory_before:.2f}MB, After={memory_after:.2f}MB, Delta={memory_after-memory_before:.2f}MB")
