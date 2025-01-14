"""Configuration settings for the Solana token monitoring system"""
import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

# Database Configuration
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite or postgresql
if DB_TYPE == "sqlite":
    DATABASE_URL = "sqlite:///solana_data_collector.db"
else:
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "solana_data_collector")
    DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# API Keys and URLs
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")

# API Rate Limits (requests per second)
API_RATE_LIMIT = {
    "helius": float(os.getenv("HELIUS_RATE_LIMIT", "10")),
    "twitter": float(os.getenv("TWITTER_RATE_LIMIT", "1")),
    "solscan": float(os.getenv("SOLSCAN_RATE_LIMIT", "5")),
    "shyft": float(os.getenv("SHYFT_RATE_LIMIT", "5")),
    "default": float(os.getenv("DEFAULT_RATE_LIMIT", "2"))
}

# API Rate Limit Window (seconds)
API_RATE_LIMIT_WINDOW = int(os.getenv("API_RATE_LIMIT_WINDOW", "60"))

# API Timeout Settings (seconds)
API_TIMEOUT = {
    "connect": float(os.getenv("API_CONNECT_TIMEOUT", "5.0")),
    "read": float(os.getenv("API_READ_TIMEOUT", "30.0")),
    "write": float(os.getenv("API_WRITE_TIMEOUT", "30.0")),
    "pool": float(os.getenv("API_POOL_TIMEOUT", "60.0"))
}

# API Retry Settings
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
API_RETRY_DELAY = float(os.getenv("API_RETRY_DELAY", "1.0"))
API_RETRY_BACKOFF = float(os.getenv("API_RETRY_BACKOFF", "2.0"))

# API Burst Limits
API_BURST_LIMIT = {
    "helius": int(os.getenv("HELIUS_BURST_LIMIT", "50")),
    "twitter": int(os.getenv("TWITTER_BURST_LIMIT", "5")),
    "solscan": int(os.getenv("SOLSCAN_BURST_LIMIT", "20")),
    "shyft": int(os.getenv("SHYFT_BURST_LIMIT", "20")),
    "default": int(os.getenv("DEFAULT_BURST_LIMIT", "10"))
}

# Monitoring Settings
MONITORING_INTERVAL = int(os.getenv("MONITORING_INTERVAL", "10"))  # seconds
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))  # seconds
MIN_MARKET_CAP = float(os.getenv("MIN_MARKET_CAP", "1000"))  # USD
CONFIDENCE_SCORE_THRESHOLD = float(os.getenv("CONFIDENCE_SCORE_THRESHOLD", "70"))  # percentage

# Holder Analysis Settings
MAX_WHALE_COUNT = int(os.getenv("MAX_WHALE_COUNT", "10"))
HOLDER_ANALYSIS_LIMIT = int(os.getenv("HOLDER_ANALYSIS_LIMIT", "1000"))
MIN_HOLDER_BALANCE = float(os.getenv("MIN_HOLDER_BALANCE", "100"))  # USD
MAX_HOLDER_CONCENTRATION = float(os.getenv("MAX_HOLDER_CONCENTRATION", "0.5"))  # 50% of supply

# Whale Analysis Settings
MIN_WHALE_BALANCE = float(os.getenv("MIN_WHALE_BALANCE", "100000"))  # USD
MAX_WHALE_THRESHOLD = float(os.getenv("MAX_WHALE_THRESHOLD", "0.1"))  # 10% of supply
WHALE_CONCENTRATION_THRESHOLD = float(os.getenv("WHALE_CONCENTRATION_THRESHOLD", "0.5"))  # 50% of supply
MIN_WHALE_TRANSACTION = float(os.getenv("MIN_WHALE_TRANSACTION", "50000"))  # USD
WHALE_MOVEMENT_WINDOW = int(os.getenv("WHALE_MOVEMENT_WINDOW", "3600"))  # seconds

# Rate Limits
RATE_LIMITS = {
    "helius": {
        "requests_per_second": float(os.getenv("HELIUS_RATE_LIMIT", "10")),
        "burst_limit": int(os.getenv("HELIUS_BURST_LIMIT", "50"))
    },
    "twitter": {
        "requests_per_second": float(os.getenv("TWITTER_RATE_LIMIT", "1")),
        "burst_limit": int(os.getenv("TWITTER_BURST_LIMIT", "5"))
    },
    "solscan": {
        "requests_per_second": float(os.getenv("SOLSCAN_RATE_LIMIT", "5")),
        "burst_limit": int(os.getenv("SOLSCAN_BURST_LIMIT", "20"))
    }
}

# Alert Thresholds
ALERT_THRESHOLDS = {
    "suspicious_activity": float(os.getenv("SUSPICIOUS_ACTIVITY_THRESHOLD", "0.8")),
    "whale_holders": int(os.getenv("WHALE_HOLDERS_THRESHOLD", "3")),
    "price_change": float(os.getenv("PRICE_CHANGE_THRESHOLD", "20")),  # percentage
    "volume_spike": float(os.getenv("VOLUME_SPIKE_THRESHOLD", "200")),  # percentage
    "holder_change": float(os.getenv("HOLDER_CHANGE_THRESHOLD", "10")),  # percentage
    "deployer_risk": float(os.getenv("DEPLOYER_RISK_THRESHOLD", "0.7"))
}

# Cache Settings
CACHE_SETTINGS = {
    "token_ttl": int(os.getenv("TOKEN_CACHE_TTL", "300")),  # seconds
    "holder_ttl": int(os.getenv("HOLDER_CACHE_TTL", "600")),  # seconds
    "analysis_ttl": int(os.getenv("ANALYSIS_CACHE_TTL", "1800")),  # seconds
    "max_size": int(os.getenv("CACHE_MAX_SIZE", "1000"))
}

# Recovery Settings
RECOVERY_SETTINGS = {
    "max_retries": int(os.getenv("RECOVERY_MAX_RETRIES", "3")),
    "retry_delay": int(os.getenv("RECOVERY_RETRY_DELAY", "5")),  # seconds
    "backoff_factor": float(os.getenv("RECOVERY_BACKOFF_FACTOR", "2.0")),
    "timeout": int(os.getenv("RECOVERY_TIMEOUT", "30"))  # seconds
}

# Security Settings
SECURITY_SETTINGS = {
    "rate_limit_window": int(os.getenv("RATE_LIMIT_WINDOW", "60")),  # seconds
    "max_requests_per_window": int(os.getenv("MAX_REQUESTS_PER_WINDOW", "100")),
    "jwt_secret": os.getenv("JWT_SECRET", "your-secret-key"),
    "jwt_algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
    "jwt_expiry": int(os.getenv("JWT_EXPIRY", "3600"))  # seconds
}

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "solana_monitor.log")

# Performance Monitoring
PERFORMANCE_SETTINGS = {
    "metrics_interval": int(os.getenv("METRICS_INTERVAL", "60")),  # seconds
    "health_check_interval": int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),  # seconds
    "alert_on_high_cpu": float(os.getenv("CPU_ALERT_THRESHOLD", "80")),  # percentage
    "alert_on_high_memory": float(os.getenv("MEMORY_ALERT_THRESHOLD", "80")),  # percentage
    "slow_query_threshold": float(os.getenv("SLOW_QUERY_THRESHOLD", "1.0"))  # seconds
}

# Analysis Settings
ANALYSIS_SETTINGS = {
    "min_holder_count": int(os.getenv("MIN_HOLDER_COUNT", "100")),
    "whale_threshold": float(os.getenv("WHALE_THRESHOLD", "0.05")),  # 5% of supply
    "max_whale_concentration": float(os.getenv("MAX_WHALE_CONCENTRATION", "0.5")),  # 50% of supply
    "min_liquidity": float(os.getenv("MIN_LIQUIDITY", "10000")),  # USD
    "sentiment_threshold": float(os.getenv("SENTIMENT_THRESHOLD", "0.6")),
    "social_impact_threshold": float(os.getenv("SOCIAL_IMPACT_THRESHOLD", "0.7")),
    "market_impact_threshold": float(os.getenv("MARKET_IMPACT_THRESHOLD", "0.4"))
}

# Monitoring Configuration
MONITOR_SETTINGS = {
    "poll_interval": int(os.getenv("MONITOR_POLL_INTERVAL", "60")),  # seconds
    "batch_size": int(os.getenv("MONITOR_BATCH_SIZE", "100")),
    "max_retries": int(os.getenv("MONITOR_MAX_RETRIES", "3")),
    "retry_delay": int(os.getenv("MONITOR_RETRY_DELAY", "5")),  # seconds
    "timeout": int(os.getenv("MONITOR_TIMEOUT", "30"))  # seconds
}

# Analysis Configuration
ANALYSIS_CONFIG = {
    "holder_threshold": int(os.getenv("ANALYSIS_HOLDER_THRESHOLD", "100")),
    "volume_threshold": float(os.getenv("ANALYSIS_VOLUME_THRESHOLD", "10000")),
    "price_change_threshold": float(os.getenv("ANALYSIS_PRICE_CHANGE_THRESHOLD", "0.1")),
    "risk_score_threshold": float(os.getenv("ANALYSIS_RISK_SCORE_THRESHOLD", "0.7")),
    "max_analysis_time": int(os.getenv("ANALYSIS_MAX_TIME", "300"))  # seconds
}

# Notification Configuration
NOTIFICATION_SETTINGS = {
    "enabled": os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true",
    "batch_size": int(os.getenv("NOTIFICATION_BATCH_SIZE", "10")),
    "interval": int(os.getenv("NOTIFICATION_INTERVAL", "300")),  # seconds
    "channels": os.getenv("NOTIFICATION_CHANNELS", "discord,twitter").split(","),
    "priority_levels": {
        "high": float(os.getenv("NOTIFICATION_PRIORITY_HIGH", "0.8")),
        "medium": float(os.getenv("NOTIFICATION_PRIORITY_MEDIUM", "0.5")),
        "low": float(os.getenv("NOTIFICATION_PRIORITY_LOW", "0.2"))
    }
}

# Cache Configuration
CACHE_CONFIG = {
    "enabled": os.getenv("CACHE_ENABLED", "true").lower() == "true",
    "ttl": int(os.getenv("CACHE_TTL", "3600")),  # seconds
    "max_size": int(os.getenv("CACHE_MAX_SIZE", "1000")),
    "cleanup_interval": int(os.getenv("CACHE_CLEANUP_INTERVAL", "300"))  # seconds
}

# Recovery Configuration
RECOVERY_CONFIG = {
    "max_retries": int(os.getenv("RECOVERY_MAX_RETRIES", "3")),
    "retry_delay": int(os.getenv("RECOVERY_RETRY_DELAY", "5")),  # seconds
    "backoff_factor": float(os.getenv("RECOVERY_BACKOFF_FACTOR", "2.0")),
    "timeout": int(os.getenv("RECOVERY_TIMEOUT", "30"))  # seconds
}

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Create logger
logger = logging.getLogger(__name__)
