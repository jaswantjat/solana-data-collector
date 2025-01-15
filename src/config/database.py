"""Database configuration."""
import os
import logging
from urllib.parse import quote_plus
from sqlalchemy.engine import URL

logger = logging.getLogger(__name__)

def get_database_url() -> URL:
    """Get database URL object."""
    try:
        # Get environment variables
        user = os.environ.get('PGUSER', 'postgres')
        password = quote_plus(os.environ.get('PGPASSWORD', ''))  # URL encode password
        host = os.environ.get('PGHOST', 'localhost')
        port = os.environ.get('PGPORT', '5432')  # Default PostgreSQL port
        database = os.environ.get('PGDATABASE', 'postgres')
        
        # Use connection pooler for production
        if os.environ.get('RENDER') == '1':
            logger.info("Running in Render environment, using connection pooler")
            # Remove 'db.' prefix if present
            if host.startswith('db.'):
                host = host[3:]
            # Use connection pooler port
            port = '6543'
        
        # Create URL object
        url = URL.create(
            'postgresql+psycopg2',
            username=user,
            password=password,
            host=host,
            port=int(port),
            database=database,
            query={
                'application_name': 'solana_data_collector',
                'client_encoding': 'utf8',
                'sslmode': 'require',
                'target_session_attrs': 'read-write',
                'keepalives': '1',
                'keepalives_idle': '30',
                'keepalives_interval': '10',
                'keepalives_count': '5'
            }
        )
        
        logger.info(f"Created database URL with host {host} and port {port}")
        return url
        
    except Exception as e:
        logger.error(f"Failed to create database URL: {str(e)}")
        raise
