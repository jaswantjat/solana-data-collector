"""Application settings and configuration."""
import os
from pathlib import Path
import urllib.parse
import logging
import socket

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = os.environ.get('DATA_DIR', str(PROJECT_ROOT / 'data'))
STATIC_DIR = os.environ.get('STATIC_DIR', str(PROJECT_ROOT / 'static'))
TEMPLATES_DIR = os.environ.get('TEMPLATES_DIR', str(PROJECT_ROOT / 'templates'))

# API Settings
API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', '10'))  # requests per window
API_RATE_LIMIT_WINDOW = int(os.environ.get('API_RATE_LIMIT_WINDOW', '1'))  # seconds
API_TIMEOUT = int(os.environ.get('API_TIMEOUT', '30'))  # seconds
API_MAX_RETRIES = int(os.environ.get('API_MAX_RETRIES', '3'))
API_RETRY_DELAY = int(os.environ.get('API_RETRY_DELAY', '1'))  # seconds

# Helius API Settings
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY', '')
HELIUS_API_URL = os.environ.get('HELIUS_API_URL', 'https://api.helius.xyz')

# Redis Settings
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

def resolve_host_ipv4(hostname):
    """Resolve hostname to IPv4 address."""
    try:
        # Force IPv4
        addrinfo = socket.getaddrinfo(
            hostname,
            None,
            family=socket.AF_INET,  # IPv4 only
            type=socket.SOCK_STREAM
        )
        if addrinfo:
            return addrinfo[0][4][0]  # Return the first IPv4 address
    except Exception as e:
        logger.error(f"Failed to resolve {hostname} to IPv4: {e}")
    return hostname

# Database Settings
def get_database_url():
    """Get database URL with proper configuration"""
    # Get database components
    db_user = os.environ.get('PGUSER', 'postgres')
    db_password = os.environ.get('PGPASSWORD', 'password')
    db_host = os.environ.get('PGHOST', 'localhost')
    db_port = os.environ.get('PGPORT', '5432')  # Default to standard port
    db_name = os.environ.get('PGDATABASE', 'postgres')
    
    # Resolve hostname to IPv4
    if not db_host.startswith(('127.0.0.1', 'localhost')):
        db_host = resolve_host_ipv4(db_host)
        logger.info(f"Resolved database host to: {db_host}")
    
    # Build connection URL
    url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Add connection parameters
    params = {
        'sslmode': os.environ.get('PGSSLMODE', 'require'),
        'connect_timeout': os.environ.get('CONNECT_TIMEOUT', '30'),
        'application_name': 'solana_data_collector',
        'keepalives': '1',
        'keepalives_idle': '30',
        'keepalives_interval': '10',
        'keepalives_count': '5',
        'client_encoding': 'utf8',
    }
    
    # Add SQLAlchemy specific pool settings
    params.update({
        'pool_size': os.environ.get('POOL_SIZE', '5'),
        'max_overflow': os.environ.get('MAX_OVERFLOW', '10'),
        'pool_timeout': os.environ.get('POOL_TIMEOUT', '30'),
        'pool_pre_ping': 'true',
        'pool_recycle': '3600',
    })
    
    # Build the final URL with parameters
    final_url = f"{url}?{urllib.parse.urlencode(params)}"
    logger.info(f"Database connection configured with host {db_host}")
    return final_url

DATABASE_URL = get_database_url()

# Supabase Settings
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://oxptysjmxpndgyfmjoge.supabase.co')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
SUPABASE_API_KEY = os.environ.get('SUPABASE_API_KEY', '')

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
API_KEY_HEADER = os.environ.get('API_KEY_HEADER', 'X-API-Key')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

# Monitoring Settings
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', '8000'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
