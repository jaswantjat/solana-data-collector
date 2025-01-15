"""Database connection management."""
import logging
import time
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, Session
import backoff

from ..config.database import get_database_url
from .mock_db import mock_db

# Get environment variables
USE_MOCK_DATA = os.getenv('USE_MOCK_DATA', 'true').lower() == 'true'

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self.use_mock = USE_MOCK_DATA
        self._setup_retries = 0
        self._max_retries = 5
        self._retry_delay = 2  # seconds
        
    def get_session(self) -> Session:
        """Get a database session."""
        if self.use_mock:
            return mock_db
        if not self.SessionLocal:
            self._setup_engine()
        return self.SessionLocal()
        
    @backoff.on_exception(
        backoff.expo,
        (SQLAlchemyError, OperationalError),
        max_tries=5,
        jitter=backoff.full_jitter
    )
    def _setup_engine(self) -> None:
        """Set up the database engine with retries."""
        try:
            if not self.engine:
                url = get_database_url()
                self.engine = create_engine(
                    url,
                    pool_pre_ping=True,
                    pool_size=int(os.getenv("SQLALCHEMY_POOL_SIZE", "5")),
                    max_overflow=int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "10")),
                    pool_timeout=int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", "30")),
                    pool_recycle=int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "1800"))
                )
                self.SessionLocal = sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )
                
                # Test the connection
                with self.SessionLocal() as session:
                    result = session.execute(text("SELECT 1")).scalar()
                    if result != 1:
                        raise ValueError("Database connection test failed")
                logger.info("Database connection established successfully")
                
        except Exception as e:
            logger.error(f"Failed to setup database engine: {str(e)}")
            self._setup_retries += 1
            if self._setup_retries >= self._max_retries:
                logger.error("Max retries reached for database setup")
                raise
            time.sleep(self._retry_delay)
            raise  # Re-raise for backoff to handle
            
    def dispose(self) -> None:
        """Dispose of the database engine."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None

# Create a global instance
db_manager = DatabaseManager()
