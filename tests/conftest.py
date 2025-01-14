"""Test configuration and fixtures for the Solana token monitoring system"""
import os
import pytest
import asyncio
from typing import Dict, Generator, List
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.system_integrator import SystemIntegrator
from src.database.connection import db_manager
from src.database.models import Base
from src.events.event_manager import event_manager
from src.test.mock_data import (
    get_mock_token,
    get_mock_holders,
    get_mock_transactions
)

# Load test environment variables
load_dotenv(".env.test")

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    """Create test database and tables"""
    # Create test database
    db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///test.db")
    engine = create_async_engine(db_url, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Set up database manager
    db_manager.engine = engine
    db_manager.session_factory = async_session
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def test_system(test_db):
    """Initialize system with test configuration"""
    # Reset event manager
    event_manager.clear_handlers()
    event_manager.immediate_mode = True
    
    # Create system instance
    system = SystemIntegrator()
    
    # Initialize system and wait for completion
    await system.initialize()
    
    # Verify initialization
    assert system.is_initialized, "System failed to initialize"
    assert system.token_monitor is not None, "Token monitor not initialized"
    assert system.token_analyzer is not None, "Token analyzer not initialized"
    assert system.holder_analyzer is not None, "Holder analyzer not initialized"
    assert system.deployer_analyzer is not None, "Deployer analyzer not initialized"
    
    # Start components
    await system.token_monitor.start()
    await system.token_analyzer.start()
    await system.holder_analyzer.start()
    await system.deployer_analyzer.start()
    
    # Return initialized components
    components = {
        "token_monitor": system.token_monitor,
        "token_analyzer": system.token_analyzer,
        "holder_analyzer": system.holder_analyzer,
        "deployer_analyzer": system.deployer_analyzer,
        "notification_manager": system.notification_manager
    }
    
    yield components
    
    # Cleanup
    for component in components.values():
        if hasattr(component, 'shutdown'):
            await component.shutdown()
    event_manager.clear_handlers()

@pytest.fixture
def mock_token() -> Dict:
    """Get mock token data"""
    return get_mock_token()

@pytest.fixture
def mock_holders() -> Dict:
    """Get mock holder data"""
    return get_mock_holders()

@pytest.fixture
def mock_transactions() -> List[Dict]:
    """Get mock transaction data"""
    return get_mock_transactions()
