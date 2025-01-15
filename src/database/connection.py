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
        # Try to get both IPv4 and IPv6 addresses
        addrinfo = socket.getaddrinfo(host, None)
        
        # Prefer IPv4 addresses
        for info in addrinfo:
            if info[0] == socket.AF_INET:  # IPv4
                return info[4][0]
        
        # If no IPv4 found, use the first address
        return addrinfo[0][4][0]
    except socket.gaierror as e:
        logger.error(f"Failed to resolve host {host}: {e}")
        return host

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
    
    def _resolve_database_url(self):
        """Resolve database URL with IP address"""
        parsed = urllib.parse.urlparse(self.database_url)
        host = parsed.hostname
        if host:
            ip = resolve_host(host)
            netloc = parsed.netloc.replace(host, ip)
            self.database_url = self.database_url.replace(parsed.netloc, netloc)
            logger.info(f"Resolved database host {host} to {ip}")
    
    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=5,
        giveup=handle_db_error
    )
    def _setup_engine(self):
        """Initialize database engine with retries"""
        try:
            # Resolve hostname to IP
            self._resolve_database_url()
            
            self.engine = create_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,  # Enable connection health checks
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
