"""Application settings and configuration."""
import os
from pathlib import Path
import urllib.parse
import logging

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

# Database Settings
def get_database_url():
    """Get database URL with proper configuration"""
    # Check for individual components first
    if all(os.environ.get(key) for key in ['PGUSER', 'PGPASSWORD', 'PGHOST', 'PGPORT', 'PGDATABASE']):
        return f"postgresql://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}@{os.environ['PGHOST']}:{os.environ['PGPORT']}/{os.environ['PGDATABASE']}"
    
    # Fallback to DATABASE_URL
    url = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost:5432/dbname')
    
    try:
        # Parse the URL to validate it
        parsed = urllib.parse.urlparse(url)
        if not all([parsed.scheme, parsed.hostname, parsed.path]):
            raise ValueError("Invalid database URL format")
        
        return url
    except Exception as e:
        logger.error(f"Failed to parse DATABASE_URL: {e}")
        raise

DATABASE_URL = get_database_url()

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
API_KEY_HEADER = os.environ.get('API_KEY_HEADER', 'X-API-Key')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

# Monitoring Settings
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', '8000'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
