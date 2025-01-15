"""Configuration module for the Solana Data Collector."""
import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load all configuration variables."""
    return {
        # Logging Configuration
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',

        # API Settings
        'API_RATE_LIMIT': int(os.getenv('API_RATE_LIMIT', '10')),
        'API_RATE_LIMIT_WINDOW': int(os.getenv('API_RATE_LIMIT_WINDOW', '1')),
        'API_TIMEOUT': int(os.getenv('API_TIMEOUT', '30')),
        'API_MAX_RETRIES': int(os.getenv('API_MAX_RETRIES', '3')),
        'API_RETRY_DELAY': int(os.getenv('API_RETRY_DELAY', '1')),

        # Twitter API Settings
        'TWITTER_CLIENT_ID': os.getenv('TWITTER_CLIENT_ID', ''),
        'TWITTER_CLIENT_SECRET': os.getenv('TWITTER_CLIENT_SECRET', ''),
        'TWITTER_API_KEY': os.getenv('TWITTER_API_KEY', ''),
        'TWITTER_API_SECRET': os.getenv('TWITTER_API_SECRET', ''),
        'TWITTER_BEARER_TOKEN': os.getenv('TWITTER_BEARER_TOKEN', ''),
        'TWITTER_ACCESS_TOKEN': os.getenv('TWITTER_ACCESS_TOKEN', ''),
        'TWITTER_ACCESS_TOKEN_SECRET': os.getenv('TWITTER_ACCESS_TOKEN_SECRET', ''),

        # Blockchain API Settings
        'HELIUS_API_KEY': os.getenv('HELIUS_API_KEY', ''),
        'HELIUS_ENDPOINT': os.getenv('HELIUS_API_URL', 'https://api.helius.xyz'),
        'SHYFT_API_KEY': os.getenv('SHYFT_API_KEY', ''),
        'SHYFT_ENDPOINT': os.getenv('SHYFT_ENDPOINT', 'https://api.shyft.to'),
        'BITQUERY_API_KEY': os.getenv('BITQUERY_API_KEY', ''),
        'BITQUERY_ENDPOINT': 'https://graphql.bitquery.io',
        'BIRDEYE_API_KEY': os.getenv('BIRDEYE_API_KEY', ''),
        'BIRDEYE_ENDPOINT': os.getenv('BIRDEYE_ENDPOINT', 'https://public-api.birdeye.so'),
        'JUPITER_API_KEY': os.getenv('JUPITER_API_KEY', ''),
        'JUPITER_ENDPOINT': os.getenv('JUPITER_ENDPOINT', 'https://quote-api.jup.ag'),
        'SOLSCAN_API_KEY': os.getenv('SOLSCAN_API_KEY', ''),
        'SOLSCAN_ENDPOINT': os.getenv('SOLSCAN_ENDPOINT', 'https://public-api.solscan.io'),

        # Program IDs
        'PUMP_FUN_PROGRAM_ID': os.getenv('PUMP_FUN_PROGRAM_ID', ''),

        # Discord Settings
        'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL', ''),

        # Rate Limiting Settings
        'MAX_REQUESTS_PER_SECOND': int(os.getenv('MAX_REQUESTS_PER_SECOND', '10')),
        'RATE_LIMIT_WINDOW_MS': int(os.getenv('RATE_LIMIT_WINDOW_MS', '1000')),
        'RETRY_DELAY_MS': int(os.getenv('RETRY_DELAY_MS', '1000')),
        'MAX_RETRIES': int(os.getenv('MAX_RETRIES', '3')),

        # Cache Settings
        'CACHE_TTL_SECONDS': int(os.getenv('CACHE_TTL_SECONDS', '300')),
        'MAX_CACHE_ITEMS': int(os.getenv('MAX_CACHE_ITEMS', '1000')),

        # Network Settings
        'NETWORK': os.getenv('NETWORK', 'mainnet-beta'),
        'RPC_URL': os.getenv('RPC_URL', 'https://api.mainnet-beta.solana.com'),
        'CONNECTION_TIMEOUT_MS': int(os.getenv('CONNECTION_TIMEOUT_MS', '5000')),

        # Test Settings
        'USE_MOCK_DATA': os.getenv('USE_MOCK_DATA', 'true').lower() == 'true',
        'TEST_MODE': os.getenv('TEST_MODE', 'true').lower() == 'true',

        # Database Settings
        'PGUSER': os.getenv('PGUSER', 'postgres'),
        'PGPASSWORD': os.getenv('PGPASSWORD', ''),
        'PGHOST': os.getenv('PGHOST', 'localhost'),
        'PGPORT': int(os.getenv('PGPORT', '5432')),
        'PGDATABASE': os.getenv('PGDATABASE', 'solana_data'),
        'PGSSLMODE': os.getenv('PGSSLMODE', 'prefer'),
        'CONNECT_TIMEOUT': int(os.getenv('CONNECT_TIMEOUT', '10')),

        # SQLAlchemy Pool Settings
        'SQLALCHEMY_POOL_SIZE': int(os.getenv('SQLALCHEMY_POOL_SIZE', '5')),
        'SQLALCHEMY_MAX_OVERFLOW': int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', '10')),
        'SQLALCHEMY_POOL_TIMEOUT': int(os.getenv('SQLALCHEMY_POOL_TIMEOUT', '30')),
        'SQLALCHEMY_POOL_RECYCLE': int(os.getenv('SQLALCHEMY_POOL_RECYCLE', '1800')),

        # Supabase Settings
        'SUPABASE_URL': os.getenv('SUPABASE_URL', ''),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY', ''),
        'SUPABASE_API_KEY': os.getenv('SUPABASE_API_KEY', ''),

        # Project paths
        'PROJECT_ROOT': os.getenv('PROJECT_ROOT', '/Users/masterjaswant/CascadeProjects/solana_data_collector'),
        'DATA_DIR': os.getenv('DATA_DIR', '/Users/masterjaswant/CascadeProjects/solana_data_collector/data'),
        'STATIC_DIR': os.getenv('STATIC_DIR', '/Users/masterjaswant/CascadeProjects/solana_data_collector/static'),
        'TEMPLATES_DIR': os.getenv('TEMPLATES_DIR', '/Users/masterjaswant/CascadeProjects/solana_data_collector/templates'),

        # Redis Settings
        'REDIS_URL': os.getenv('REDIS_URL', ''),
        'REDIS_DB': os.getenv('REDIS_DB', ''),

        # Security Settings
        'SECRET_KEY': os.getenv('SECRET_KEY', ''),
        'API_KEY_HEADER': os.getenv('API_KEY_HEADER', ''),
        'ACCESS_TOKEN_EXPIRE_MINUTES': os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', ''),

        # Monitoring Settings
        'PROMETHEUS_PORT': os.getenv('PROMETHEUS_PORT', ''),

        # Mock database configuration
        'USE_MOCK_DATA': os.getenv("USE_MOCK_DATA", "true").lower() == "true",

        # API Keys and Endpoints
        'HELIUS_API_KEY': os.getenv("HELIUS_API_KEY", ""),
        'HELIUS_ENDPOINT': os.getenv("HELIUS_ENDPOINT", "https://api.helius.xyz/v0"),

        'SHYFT_API_KEY': os.getenv("SHYFT_API_KEY", ""),
        'SHYFT_ENDPOINT': os.getenv("SHYFT_ENDPOINT", "https://api.shyft.to/sol/v1"),

        'BITQUERY_API_KEY': os.getenv("BITQUERY_API_KEY", ""),
        'BITQUERY_ENDPOINT': os.getenv("BITQUERY_ENDPOINT", "https://graphql.bitquery.io"),

        # Monitoring configuration
        'POLLING_INTERVAL': int(os.getenv("POLLING_INTERVAL", "60")),  # seconds
        'MIN_MARKET_CAP': float(os.getenv("MIN_MARKET_CAP", "1000")),  # USD
        'CONFIDENCE_SCORE_THRESHOLD': float(os.getenv("CONFIDENCE_SCORE_THRESHOLD", "0.8")),

        # Notification configuration
        'DISCORD_WEBHOOK_URL': os.getenv("DISCORD_WEBHOOK_URL", ""),

        # Logging configuration
        'LOG_LEVEL': os.getenv("LOG_LEVEL", "INFO").upper(),
        'LOG_FORMAT': "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    }

# Load configuration
config = load_config()

# Export all config variables
globals().update(config)
