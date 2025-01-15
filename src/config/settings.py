"""Application settings and configuration."""
import os
from pathlib import Path
import urllib.parse

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
    """Get database URL with proper SSL and connection settings"""
    url = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/dbname')
    
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Add SSL and connection parameters
    params = {
        'sslmode': 'require',
        'connect_timeout': '30',
        'application_name': 'solana_data_collector'
    }
    
    # If there are existing params, update them
    existing_params = urllib.parse.parse_qs(parsed.query)
    for key, value in existing_params.items():
        params[key] = value[0]
    
    # Reconstruct the URL with parameters
    new_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urllib.parse.urlencode(params)}"
    return new_url

DATABASE_URL = get_database_url()

# Security Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
API_KEY_HEADER = os.environ.get('API_KEY_HEADER', 'X-API-Key')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

# Monitoring Settings
PROMETHEUS_PORT = int(os.environ.get('PROMETHEUS_PORT', '8000'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
