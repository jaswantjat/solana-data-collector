"""Database connection manager"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError, OperationalError
import logging
from typing import Generator
import time
import backoff
import socket
import urllib.parse

from ..config import DATABASE_URL

logger = logging.getLogger(__name__)

def resolve_host(host):
    """Resolve hostname to IP address, preferring IPv4"""
    try:
        # Force IPv4
        addrinfo = socket.getaddrinfo(
            host, 
            None,
            socket.AF_INET,  # Force IPv4
            socket.SOCK_STREAM,
            0,
            socket.AI_ADDRCONFIG | socket.AI_V4MAPPED
        )
        return addrinfo[0][4][0]  # Return the first IPv4 address
    except socket.gaierror as e:
        logger.error(f"Failed to resolve host {host}: {e}")
        return host

def handle_db_error(e: Exception) -> bool:
    """Determine if error should trigger a retry"""
    if isinstance(e, (OperationalError, ValueError)):
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
    
    def _parse_database_url(self):
        """Parse and validate database URL"""
        try:
            # Parse the URL
            parsed = urllib.parse.urlparse(self.database_url)
            
            # Extract components
            username = parsed.username
            password = parsed.password
            host = parsed.hostname
            port = parsed.port or 5432
            database = parsed.path.lstrip('/')
            
            # Resolve hostname to IPv4
            if host:
                host = resolve_host(host)
            
            # Reconstruct URL with resolved host
            netloc = f"{username}:{password}@{host}:{port}" if username and password else f"{host}:{port}"
            
            # Add query parameters
            query = dict(urllib.parse.parse_qsl(parsed.query))
            query.update({
                'sslmode': 'require',
                'connect_timeout': '30',
                'application_name': 'solana_data_collector'
            })
            query_string = urllib.parse.urlencode(query)
            
            # Build final URL
            self.database_url = f"{parsed.scheme}://{netloc}/{database}?{query_string}"
            logger.info(f"Database URL parsed successfully with host {host}")
            
        except Exception as e:
            logger.error(f"Failed to parse database URL: {e}")
            raise
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        giveup=handle_db_error
    )
    def _setup_engine(self):
        """Initialize database engine with retries"""
        try:
            # Parse and validate URL
            self._parse_database_url()
            
            # Create engine
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True
            )
            
            # Add event listeners for connection debugging
            @event.listens_for(self.engine, 'connect')
            def receive_connect(dbapi_connection, connection_record):
                logger.info("Database connection established")
            
            @event.listens_for(self.engine, 'checkout')
            def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                logger.debug("Database connection checked out from pool")
            
            # Test the connection
            with self.engine.connect() as conn:
                result = conn.execute("SELECT 1")
                result.scalar()
            
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
