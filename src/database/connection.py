"""Database connection manager."""
import logging
from contextlib import contextmanager
from typing import Generator

import backoff
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        """Initialize the database manager."""
        self.engine = None
        self._setup_engine()

    @backoff.on_exception(
        backoff.expo,
        (SQLAlchemyError, DBAPIError),
        max_tries=5,
        jitter=None,
    )
    def _setup_engine(self) -> None:
        """Set up the database engine with retries on failure."""
        try:
            # Create engine with SQLAlchemy-specific parameters
            self.engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=settings.SQLALCHEMY_POOL_SIZE,
                max_overflow=settings.SQLALCHEMY_MAX_OVERFLOW,
                pool_timeout=settings.SQLALCHEMY_POOL_TIMEOUT,
                pool_recycle=settings.SQLALCHEMY_POOL_RECYCLE
            )

            # Set up connection debugging
            event.listen(self.engine, 'connect', self._on_connect)
            event.listen(self.engine, 'checkout', self._on_checkout)

            # Test the connection
            self._test_connection()
            logger.info("Database engine setup successful")

        except Exception as e:
            logger.error(f"Failed to setup database engine: {str(e)}")
            raise

    def _test_connection(self) -> None:
        """Test the database connection by executing a simple query."""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1").scalar()
                logger.info("Database connection test successful")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise

    def _on_connect(self, dbapi_connection, connection_record):
        """Log when a connection is created."""
        logger.debug("New database connection established")

    def _on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        """Log when a connection is checked out from the pool."""
        logger.debug("Database connection checked out from pool")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session.

        Yields:
            Session: A SQLAlchemy session object.
        """
        session_factory = sessionmaker(bind=self.engine)
        session = session_factory()

        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()
