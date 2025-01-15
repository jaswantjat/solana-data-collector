"""Database connection management."""
import logging
import time
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, Session
import backoff

from ..config import (
    PGUSER,
    PGPASSWORD,
    PGHOST,
    PGPORT,
    PGDATABASE,
    PGSSLMODE,
    CONNECT_TIMEOUT,
    SQLALCHEMY_POOL_SIZE,
    SQLALCHEMY_MAX_OVERFLOW,
    SQLALCHEMY_POOL_TIMEOUT,
    SQLALCHEMY_POOL_RECYCLE,
    USE_MOCK_DATA
)

from .mock_db import mock_db

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
                db_url = URL.create(
                    "postgresql",
                    username=PGUSER,
                    password=PGPASSWORD,
                    host=PGHOST,
                    port=PGPORT,
                    database=PGDATABASE,
                    query={
                        "sslmode": PGSSLMODE,
                        "connect_timeout": str(CONNECT_TIMEOUT)
                    }
                )
                self.engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_size=SQLALCHEMY_POOL_SIZE,
                    max_overflow=SQLALCHEMY_MAX_OVERFLOW,
                    pool_timeout=SQLALCHEMY_POOL_TIMEOUT,
                    pool_recycle=SQLALCHEMY_POOL_RECYCLE
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
                self.use_mock = True
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
