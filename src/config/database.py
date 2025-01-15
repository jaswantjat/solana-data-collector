"""Database configuration."""
import os
from urllib.parse import quote_plus

def get_connection_string() -> str:
    """Get database connection string."""
    # Get environment variables
    user = os.environ.get('PGUSER', 'postgres')
    password = quote_plus(os.environ.get('PGPASSWORD', ''))  # URL encode password
    host = os.environ.get('PGHOST', 'localhost')
    port = os.environ.get('PGPORT', '6543')  # Supabase connection pooler port
    database = os.environ.get('PGDATABASE', 'postgres')
    
    # Use connection pooler for production
    if os.environ.get('RENDER'):
        # Remove 'db.' prefix if present
        if host.startswith('db.'):
            host = host[3:]
        # Use connection pooler port
        port = '6543'
    
    # Construct connection string
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"
