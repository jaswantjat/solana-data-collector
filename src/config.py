import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY")
SHYFT_API_KEY = os.getenv("SHYFT_API_KEY")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Twitter API Keys
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Program IDs
PUMP_FUN_PROGRAM_ID = "PFund789PhwUhpz3J1h7PJPGMkunwP5nhxz7xKBjFx"  # pump.fun program ID

# Analysis Thresholds
MIN_MARKET_CAP = 30_000  # $30k
MIN_SUCCESSFUL_MCAP = 3_000_000  # $3M
MIN_FAILED_MCAP = 200_000  # $200k
MAX_SNIPER_COUNT = 2
MAX_INSIDER_COUNT = 2
MAX_BUY_RATIO = 0.7
MAX_WHALE_THRESHOLD = 0.08  # 8% of supply
MAX_WHALE_COUNT = 2
MIN_DEPLOYER_SUCCESS_RATE = 0.03  # 3% success rate required

# Monitoring Settings
POLLING_INTERVAL = 60  # seconds
ANALYSIS_LOOKBACK_DAYS = 14  # days to look back for analysis
HOLDER_ANALYSIS_LIMIT = 30  # number of top holders to analyze
CONFIDENCE_SCORE_THRESHOLD = 70  # minimum score to trigger notification

# API Endpoints
BITQUERY_ENDPOINT = os.getenv('BITQUERY_ENDPOINT', 'https://graphql.bitquery.io')
SHYFT_ENDPOINT = os.getenv('SHYFT_ENDPOINT', 'https://api.shyft.to/sol/v1')
HELIUS_ENDPOINT = os.getenv('HELIUS_ENDPOINT', 'https://api.helius.xyz/v0')
