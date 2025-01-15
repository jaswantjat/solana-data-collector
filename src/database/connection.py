"""Database connection manager"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import logging
from typing import Generator
import time
import backoff

from ..config import DATABASE_URL

logger = logging.getLogger(__name__)

def handle_db_error(e: Exception) -> bool:
    """Determine if error should trigger a retry"""
    if isinstance(e, OperationalError):
        logger.warning(f"Database connection error: {e}. Retrying...")
        return True
    logger.error(f"Unhandled database error: {e}")
    return False

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.Session = None
        self._setup_engine()
        
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        giveup=handle_db_error
    )
    def _setup_engine(self):
        """Initialize database engine with retries"""
        try:
            # Add connect_args for SSL mode if needed
            connect_args = {}
            if 'sslmode' not in self.database_url:
                connect_args['sslmode'] = 'require'
            
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args=connect_args
            )
            
            # Test the connection
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            
            self.Session = scoped_session(
                sessionmaker(
                    autocommit=False,
                    autoflush=False,
                    bind=self.engine
                )
            )
            logger.info("Database connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup database engine: {e}")
            raise
    
    @contextmanager
    def session(self) -> Generator:
        """Get a database session"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()
