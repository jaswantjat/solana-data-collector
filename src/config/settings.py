"""Application settings and configuration."""
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = os.environ.get('DATA_DIR', str(PROJECT_ROOT / 'data'))
STATIC_DIR = os.environ.get('STATIC_DIR', str(PROJECT_ROOT / 'static'))
TEMPLATES_DIR = os.environ.get('TEMPLATES_DIR', str(PROJECT_ROOT / 'templates'))

# API Settings
API_RATE_LIMIT = int(os.environ.get('API_RATE_LIMIT', '10'))
API_RATE_LIMIT_WINDOW = int(os.environ.get('API_RATE_LIMIT_WINDOW', '1'))
API_TIMEOUT = int(os.environ.get('API_TIMEOUT', '30'))
API_MAX_RETRIES = int(os.environ.get('API_MAX_RETRIES', '3'))
API_RETRY_DELAY = int(os.environ.get('API_RETRY_DELAY', '1'))

# Helius API Settings
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY', '')
HELIUS_API_URL = os.environ.get('HELIUS_API_URL', 'https://api.helius.xyz')

# Redis Settings
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
REDIS_DB = int(os.environ.get('REDIS_DB', '0'))

# Database Settings
PGUSER = os.environ.get('PGUSER', 'postgres')
PGPASSWORD = os.environ.get('PGPASSWORD', 'password')
PGHOST = os.environ.get('PGHOST', 'localhost')
PGPORT = int(os.environ.get('PGPORT', '5432'))
PGDATABASE = os.environ.get('PGDATABASE', 'postgres')
PGSSLMODE = os.environ.get('PGSSLMODE', 'require')
CONNECT_TIMEOUT = int(os.environ.get('CONNECT_TIMEOUT', '30'))

# SQLAlchemy Settings
SQLALCHEMY_POOL_SIZE = int(os.environ.get('POOL_SIZE', '5'))
SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get('MAX_OVERFLOW', '10'))
SQLALCHEMY_POOL_TIMEOUT = int(os.environ.get('POOL_TIMEOUT', '30'))
SQLALCHEMY_POOL_RECYCLE = int(os.environ.get('POOL_RECYCLE', '1800'))

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
