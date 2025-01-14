"""Database connection manager"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Generator

from ..config import DATABASE_URL

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or DATABASE_URL
        self.engine = None
        self.Session = None
        self._setup_engine()
        
    def _setup_engine(self):
        """Initialize database engine"""
        try:
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            logger.info("Database engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise
            
    @contextmanager
    def get_session(self) -> Generator:
        """Get a database session"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in database session: {str(e)}")
            raise
        finally:
            session.close()
            
    def check_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False
            
    def create_tables(self):
        """Create all database tables"""
        from .models import Base
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise

# Global database manager instance
db_manager = DatabaseManager()
