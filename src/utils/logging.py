"""Logging utility for the application."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from src.config import config

def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """Set up a logger with proper configuration.
    
    Args:
        name: The name of the logger
        log_file: Optional path to log file. If not provided, logs only go to stdout
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
        
    # Get log level from config, default to INFO
    log_level = getattr(logging, config.get('LOG_LEVEL', 'INFO').upper())
    logger.setLevel(log_level)
    
    # Create formatters and handlers
    formatter = logging.Formatter(
        config.get(
            'LOG_FORMAT',
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if log file is specified
    if log_file:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        # Rotating file handler - 10MB max size, keep 5 backups
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance. If it doesn't exist, create it.
    
    Args:
        name: The name of the logger
        
    Returns:
        Logger instance
    """
    # Default log file path
    log_file = os.path.join('logs', f'{name}.log')
    
    return setup_logger(name, log_file)
