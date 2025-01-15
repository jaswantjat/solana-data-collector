"""Database connection management."""
import os
import time
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import asyncio

from src.utils.logging import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        """Initialize the database manager."""
        self.engine = None
        self.Session = None
        self._init_engine()

    def _init_engine(self):
        """Initialize the database engine with connection pooling."""
        try:
            # Get database configuration from environment
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'solana_data')
            db_user = os.getenv('DB_USER', 'postgres')
            db_pass = os.getenv('DB_PASSWORD', 'postgres')
            
            # Construct database URL
            db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
            
            # Create engine with connection pooling
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True,
                pool_recycle=300,  # Recycle connections every 5 minutes
                echo=False
            )
            
            # Create session factory
            self.Session = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {str(e)}")
            raise

    async def check_connection(self) -> bool:
        """Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            # Try to get a connection from the pool
            with self.engine.connect() as conn:
                # Execute a simple query
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            return False

    def get_session(self) -> Session:
        """Get a new database session.
        
        Returns:
            Session: A new SQLAlchemy session
            
        Raises:
            SQLAlchemyError: If session creation fails
        """
        try:
            return self.Session()
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database session: {str(e)}")
            raise

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations.
        
        Yields:
            Session: Database session
            
        Raises:
            Exception: If any database operation fails
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

    async def execute_with_retry(self, operation, max_retries: int = 3, retry_delay: int = 1):
        """Execute a database operation with retry logic.
        
        Args:
            operation: Database operation to execute
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: If operation fails after all retries
        """
        for attempt in range(max_retries):
            try:
                return operation()
            except SQLAlchemyError as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Operation failed after {max_retries} attempts: {str(e)}"
                    )
                    raise
                
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                
                # Exponential backoff
                await asyncio.sleep(retry_delay * (2 ** attempt))
                
                # Try to reconnect
                self._init_engine()

    async def cleanup(self):
        """Cleanup database connections."""
        try:
            if self.engine:
                self.engine.dispose()
                logger.info("Database connections cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up database connections: {str(e)}")
            raise

# Create global database manager instance
db_manager = DatabaseManager()
