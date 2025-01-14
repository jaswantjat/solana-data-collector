#!/usr/bin/env python3
"""Database backup script"""
import os
import sys
import shutil
import logging
from datetime import datetime
import sqlite3
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATABASE_URL, DB_TYPE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def backup_sqlite():
    """Backup SQLite database"""
    try:
        # Extract database path from URL
        db_path = DATABASE_URL.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return False

        # Create backup directory if it doesn't exist
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"backup_{timestamp}.db"

        # Copy database file
        shutil.copy2(db_path, backup_path)
        logger.info(f"Successfully created backup at: {backup_path}")

        # Remove old backups (keep last 5)
        backups = sorted(backup_dir.glob('*.db'))
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")

        return True

    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def backup_postgresql():
    """Backup PostgreSQL database"""
    try:
        # Parse database URL
        db_params = DATABASE_URL.replace('postgresql://', '').split('/')
        db_name = db_params[1]
        host_port = db_params[0].split('@')[1].split(':')
        host = host_port[0]
        port = host_port[1]
        user_pass = db_params[0].split('@')[0].split(':')
        user = user_pass[0]
        password = user_pass[1]

        # Create backup directory if it doesn't exist
        backup_dir = Path('backups')
        backup_dir.mkdir(exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"backup_{timestamp}.sql"

        # Set environment variables for pg_dump
        os.environ['PGPASSWORD'] = password

        # Run pg_dump
        cmd = f"pg_dump -h {host} -p {port} -U {user} -F c -b -v -f {backup_path} {db_name}"
        result = os.system(cmd)

        if result == 0:
            logger.info(f"Successfully created backup at: {backup_path}")

            # Remove old backups (keep last 5)
            backups = sorted(backup_dir.glob('*.sql'))
            if len(backups) > 5:
                for old_backup in backups[:-5]:
                    old_backup.unlink()
                    logger.info(f"Removed old backup: {old_backup}")
            return True
        else:
            logger.error("Backup failed")
            return False

    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return False

def main():
    """Main backup function"""
    if DB_TYPE == "sqlite":
        success = backup_sqlite()
    else:
        success = backup_postgresql()

    if success:
        logger.info("Backup completed successfully")
        sys.exit(0)
    else:
        logger.error("Backup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
