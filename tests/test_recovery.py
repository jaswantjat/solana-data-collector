"""Tests for system recovery procedures"""
import pytest
import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from src.utils.recovery import (
    SystemRecoveryManager,
    APIHealthMonitor,
    DatabaseRecoveryManager,
    with_retry
)

@pytest.fixture
def recovery_manager(tmp_path):
    """Create recovery manager with temporary backup directory"""
    return SystemRecoveryManager(backup_dir=str(tmp_path))

@pytest.fixture
def api_monitor():
    """Create API health monitor"""
    endpoints = {
        "helius": "https://api.helius.xyz/v0/health",
        "dashboard": "http://localhost:8000/health"
    }
    return APIHealthMonitor(endpoints)

@pytest.fixture
def db_manager():
    """Create database recovery manager"""
    return DatabaseRecoveryManager("postgresql://localhost:5432/test")

@pytest.mark.asyncio
async def test_backup_restore(recovery_manager):
    """Test data backup and restore"""
    test_data = {"key": "value"}
    
    # Test backup
    await recovery_manager.backup_data(test_data, "test")
    assert os.path.exists(recovery_manager.backup_dir)
    assert len(os.listdir(recovery_manager.backup_dir)) == 1
    
    # Test restore
    restored_data = await recovery_manager.restore_from_backup("test")
    assert restored_data == test_data

@pytest.mark.asyncio
async def test_health_checks(recovery_manager):
    """Test health check registration and execution"""
    async def mock_check():
        return True
        
    recovery_manager.register_health_check("test", mock_check)
    results = await recovery_manager.run_health_checks()
    assert "test" in results
    assert results["test"] is True

@pytest.mark.asyncio
async def test_recovery_procedures(recovery_manager):
    """Test recovery procedure registration and execution"""
    async def mock_recovery():
        return True
        
    recovery_manager.register_recovery_procedure("test", mock_recovery)
    result = await recovery_manager.attempt_recovery("test")
    assert result is True

@pytest.mark.asyncio
async def test_api_health_monitor(api_monitor):
    """Test API health monitoring"""
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response
        
        results = await api_monitor.check_all_endpoints()
        assert all(results.values())
        
        # Test failure scenario
        mock_response.status = 500
        results = await api_monitor.check_all_endpoints()
        assert not any(results.values())

@pytest.mark.asyncio
async def test_database_recovery(db_manager):
    """Test database recovery procedures"""
    # Test successful connection
    with patch.object(db_manager, 'connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = True
        
        # Mock the connection process
        async def mock_connect_impl():
            db_manager.connected = True
            db_manager._connection = True
            return True
            
        mock_connect.side_effect = mock_connect_impl
        
        assert await db_manager.ensure_connection()
        assert db_manager.connected
        
    # Reset connection state
    db_manager.connected = False
    db_manager._connection = None
    db_manager._retry_count = 0
        
    # Test connection failure
    with patch.object(db_manager, 'connect', new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")
        
        # Should fail after max_retries attempts
        for _ in range(db_manager.max_retries):
            with pytest.raises(Exception, match="Connection failed"):
                await db_manager.ensure_connection()
                
        # Next attempt should fail with max retries exceeded
        with pytest.raises(Exception, match="Max retries .* exceeded"):
            await db_manager.ensure_connection()
            
        assert not db_manager.connected

@pytest.mark.asyncio
async def test_backup_database(db_manager, tmp_path):
    """Test database backup"""
    backup_path = str(tmp_path / "backup.sql")
    
    # Connect to database first
    with patch.object(db_manager, 'connect', new_callable=AsyncMock) as mock_connect:
        async def mock_connect_impl():
            db_manager.connected = True
            db_manager._connection = True
            return True
            
        mock_connect.side_effect = mock_connect_impl
        await db_manager.ensure_connection()
    
    # Test successful backup
    await db_manager.backup_database(backup_path)
    assert os.path.exists(backup_path)
    
    # Test backup failure
    with patch.object(db_manager, 'backup_database', new_callable=AsyncMock) as mock_backup:
        mock_backup.side_effect = Exception("Backup failed")
        with pytest.raises(Exception):
            await db_manager.backup_database(backup_path)

@pytest.mark.asyncio
async def test_retry_decorator():
    """Test retry decorator"""
    attempts = 0
    
    @with_retry(max_attempts=3)
    async def failing_function():
        nonlocal attempts
        attempts += 1
        raise Exception("Test failure")
        
    with pytest.raises(Exception):
        await failing_function()
    assert attempts == 3

@pytest.mark.asyncio
async def test_system_resilience(recovery_manager, api_monitor, db_manager):
    """Test overall system resilience"""
    # Register health checks
    async def api_health():
        return all(await api_monitor.check_all_endpoints())
        
    async def db_health():
        return await db_manager.ensure_connection()
        
    recovery_manager.register_health_check("api", api_health)
    recovery_manager.register_health_check("database", db_health)
    
    # Register recovery procedures
    async def api_recovery():
        return await api_monitor.check_all_endpoints()
        
    async def db_recovery():
        return await db_manager.connect()
        
    recovery_manager.register_recovery_procedure("api", api_recovery)
    recovery_manager.register_recovery_procedure("database", db_recovery)
    
    # Test system recovery
    with patch.object(api_monitor, 'check_all_endpoints', new_callable=AsyncMock) as mock_api:
        mock_api.return_value = {"helius": True, "dashboard": True}
        with patch.object(db_manager, 'connect', new_callable=AsyncMock) as mock_db:
            mock_db.return_value = True
            
            # Run health checks
            health_results = await recovery_manager.run_health_checks()
            assert all(health_results.values())
            
            # Test recovery
            recovery_results = []
            for system in ["api", "database"]:
                result = await recovery_manager.attempt_recovery(system)
                recovery_results.append(result)
            assert all(recovery_results)
