"""Path configuration for the application."""
import os
from pathlib import Path

# Get the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Data directory path
DATA_DIR = os.environ.get('DATA_DIR', str(PROJECT_ROOT / 'data'))

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Wallet data file
WALLETS_FILE = os.path.join(DATA_DIR, 'wallets.json')

# Other data files can be added here
