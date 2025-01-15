"""Database connection manager."""
import logging
from contextlib import contextmanager
from typing import Generator

import backoff
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from src.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        """Initialize database manager."""
        self.engine = None
        self.SessionLocal = None
        self._setup_engine()
    
    def _get_database_url(self) -> str:
        """Get database URL from config."""
        return (
            f"postgresql://{config.get('PGUSER')}:{config.get('PGPASSWORD')}"
            f"@{config.get('PGHOST')}:{config.get('PGPORT')}"
            f"/{config.get('PGDATABASE')}"
            f"?sslmode={config.get('PGSSLMODE', 'prefer')}"
        )
    
    def _setup_engine(self) -> None:
        """Set up SQLAlchemy engine with connection pooling."""
        try:
            self.engine = create_engine(
                self._get_database_url(),
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True,  # Enable connection health checks
                pool_recycle=3600,   # Recycle connections after 1 hour
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            logger.info("Database engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        (SQLAlchemyError, OperationalError),
        max_tries=5,
        jitter=backoff.full_jitter,
        logger=logger
    )
    def get_session(self) -> Session:
        """Get a database session with retry logic.
        
        Returns:
            SQLAlchemy Session object
        
        Raises:
            SQLAlchemyError: If unable to create session after retries
        """
        if not self.SessionLocal:
            self._setup_engine()
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations.
        
        Yields:
            SQLAlchemy Session object
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Error in database session: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def check_connection(self) -> bool:
        """Check if database connection is alive.
        
        Returns:
            bool: True if connection is alive, False otherwise
        """
        try:
            with self.session_scope() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False

# Global instance
db_manager = DatabaseManager()
