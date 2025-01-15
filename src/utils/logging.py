"""Logging configuration module."""
import logging
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    log_format: Optional[str] = None
) -> logging.Logger:
    """Configure and return a logger instance.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        log_file: Optional log file path
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        log_format: Optional custom log format
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set level
    logger.setLevel(level)

    # Default formats
    default_console_format = '%(asctime)s - %(levelname)s - %(message)s'
    default_file_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

    # Create formatters
    console_formatter = logging.Formatter(
        log_format or default_console_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_formatter = logging.Formatter(
        log_format or default_file_format,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            # Create rotating file handler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to setup file logging: {str(e)}")

    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    This is the main function to get a logger. It sets up a logger with both
    console and file output, with the file being in the 'logs' directory.
    
    Args:
        name: Name of the logger (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory in the project root
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    log_file = os.path.join(log_dir, f'{name}.log')
    
    return setup_logger(
        name=name,
        level=logging.INFO,
        log_file=log_file
    )
