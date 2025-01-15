"""Database connection manager."""
import logging
from contextlib import contextmanager
from typing import Generator
import urllib.parse
import socket

import backoff
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.config.database import get_connection_string

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        """Initialize the database manager."""
        self.engine = None
        self._setup_engine()

    def _create_connection_url(self) -> URL:
        """Create SQLAlchemy URL object for database connection."""
        try:
            # Get the connection string from config
            connection_string = get_connection_string()
            logger.info("Created database connection string")
            
            # Create URL object
            url = URL.create(
                'postgresql+psycopg2',
                query={
                    'application_name': 'solana_data_collector',
                    'client_encoding': 'utf8',
                    'keepalives': '1',
                    'keepalives_idle': '30',
                    'keepalives_interval': '10',
                    'keepalives_count': '5'
                }
            ).set(connection_string)
            
            logger.info("Created database URL object")
            return url
            
        except Exception as e:
            logger.error(f"Failed to create connection URL: {str(e)}")
            raise

    @backoff.on_exception(
        backoff.expo,
        (SQLAlchemyError, DBAPIError),
        max_tries=5,
        jitter=None,
    )
    def _setup_engine(self) -> None:
        """Set up the database engine with retries on failure."""
        try:
            # Create the URL object
            url = self._create_connection_url()
            
            # Create engine with SQLAlchemy-specific parameters
            self.engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=settings.SQLALCHEMY_POOL_SIZE,
                max_overflow=settings.SQLALCHEMY_MAX_OVERFLOW,
                pool_timeout=settings.SQLALCHEMY_POOL_TIMEOUT,
                pool_recycle=settings.SQLALCHEMY_POOL_RECYCLE,
                echo=True  # Enable SQL logging for debugging
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
                result = conn.execute("SELECT version()").scalar()
                logger.info(f"Database connection test successful. Version: {result}")
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            raise

    def _on_connect(self, dbapi_connection, connection_record):
        """Log when a connection is created."""
        logger.info("New database connection established")

    def _on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        """Log when a connection is checked out from the pool."""
        logger.debug("Database connection checked out from pool")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session."""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")

        session_factory = sessionmaker(bind=self.engine)
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()
