import logging
import os
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text
import asyncio
from contextlib import asynccontextmanager
import backoff
from datetime import datetime, timedelta

from .models import Base, Token, TokenPrice, TokenHolder, TokenTransaction, WalletAnalysis, Alert, SystemMetric

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """Initialize database connection with Supabase configuration"""
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
            
        # Convert Supabase connection string if needed
        if "supabase" in self.database_url:
            self.database_url = self.database_url.replace(
                "postgres://", "postgresql+asyncpg://"
            )
            
        # Configure connection pool
        self.pool_size = int(os.getenv("DATABASE_POOL_SIZE", "20"))
        self.max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
        self.pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
        
        # Initialize engine with pool configuration
        self.engine = create_async_engine(
            self.database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_pre_ping=True,  # Enable connection health checks
            echo=False  # Set to True for SQL query logging
        )
        
        # Create session factory
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Track pool statistics
        self.pool_stats = {
            "created_at": datetime.now(),
            "total_connections": 0,
            "active_connections": 0,
            "errors": 0,
            "last_error": None
        }
        
    async def initialize(self):
        """Initialize database schema and verify connection"""
        try:
            async with self.engine.begin() as conn:
                # Create tables if they don't exist
                await conn.run_sync(Base.metadata.create_all)
                
            # Verify connection and schema
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            self.pool_stats["errors"] += 1
            self.pool_stats["last_error"] = str(e)
            raise
            
    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """Get a database session with automatic retry on connection errors"""
        session = self.async_session()
        try:
            self.pool_stats["total_connections"] += 1
            self.pool_stats["active_connections"] += 1
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            self.pool_stats["errors"] += 1
            self.pool_stats["last_error"] = str(e)
            raise
        finally:
            self.pool_stats["active_connections"] -= 1
            await session.close()
            
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        max_time=30
    )
    async def execute_with_retry(self, session: AsyncSession, query: Any, params: Optional[Dict] = None):
        """Execute a query with retry logic"""
        try:
            if params:
                result = await session.execute(query, params)
            else:
                result = await session.execute(query)
            return result
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            self.pool_stats["errors"] += 1
            self.pool_stats["last_error"] = str(e)
            raise
            
    async def get_pool_stats(self) -> Dict:
        """Get current connection pool statistics"""
        return {
            **self.pool_stats,
            "uptime": str(datetime.now() - self.pool_stats["created_at"]),
            "error_rate": self.pool_stats["errors"] / max(self.pool_stats["total_connections"], 1),
            "connection_utilization": self.pool_stats["active_connections"] / self.pool_size
        }
        
    async def cleanup_pool(self):
        """Cleanup connection pool"""
        if self.engine:
            await self.engine.dispose()
            
    async def health_check(self) -> Dict:
        """Perform a health check on the database"""
        try:
            start_time = datetime.now()
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                
            response_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "status": "healthy",
                "response_time": response_time,
                "pool_stats": await self.get_pool_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "pool_stats": await self.get_pool_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
    async def vacuum_analyze(self):
        """Perform database maintenance"""
        try:
            async with self.engine.begin() as conn:
                # Analyze all tables
                await conn.execute(text("ANALYZE VERBOSE"))
                
                # Vacuum analyze each table
                for table in [Token, TokenPrice, TokenHolder, TokenTransaction,
                            WalletAnalysis, Alert, SystemMetric]:
                    await conn.execute(
                        text(f"VACUUM ANALYZE {table.__tablename__}")
                    )
                    
            logger.info("Database maintenance completed successfully")
            
        except Exception as e:
            logger.error(f"Database maintenance failed: {str(e)}")
            raise
