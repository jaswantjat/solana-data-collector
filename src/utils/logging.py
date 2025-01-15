"""Logging configuration module."""
import logging
import logging.config
import sys
import json
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
import traceback
import uuid
from contextlib import contextmanager

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, **kwargs):
        """Initialize formatter with optional fields."""
        self.default_fields = kwargs
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Base log data
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "location": f"{record.filename}:{record.lineno}",
            "function": record.funcName
        }
        
        # Add traceback for errors
        if record.exc_info:
            log_data["traceback"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add default fields
        log_data.update(self.default_fields)
        
        # Add request_id if available
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id
        
        return json.dumps(log_data)

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format: str = "json",
    env: str = "development"
) -> None:
    """Setup global logging configuration.
    
    Args:
        level: Logging level
        log_file: Path to log file
        format: Log format ('json' or 'text')
        env: Environment ('development' or 'production')
    """
    # Create logs directory if needed
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Base config
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JsonFormatter,
                "environment": env
            },
            "text": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": format,
                "stream": sys.stdout
            }
        },
        "root": {
            "level": level,
            "handlers": ["console"]
        }
    }
    
    # Add file handler if log_file is specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": format,
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        config["root"]["handlers"].append("file")
    
    # Apply configuration
    logging.config.dictConfig(config)

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Add request_id to context if not present
    if not hasattr(logger, "request_id"):
        logger.request_id = str(uuid.uuid4())
    
    return logger

@contextmanager
def LogContext(logger: logging.Logger, **context):
    """Context manager for adding context to logs.
    
    Args:
        logger: Logger instance
        **context: Context key-value pairs
    """
    old_context = {}
    
    # Save old context
    if hasattr(logger, "extra"):
        old_context = logger.extra
    
    # Add new context
    logger.extra = {
        **(getattr(logger, "extra", {})),
        **context
    }
    
    try:
        yield logger
    finally:
        # Restore old context
        if old_context:
            logger.extra = old_context
        else:
            delattr(logger, "extra")

def log_error(
    logger: logging.Logger,
    error: Exception,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Log an error with context.
    
    Args:
        logger: Logger instance
        error: Exception to log
        message: Error message
        context: Additional context
    """
    error_context = {
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    if context:
        error_context.update(context)
    
    logger.error(
        message,
        extra=error_context,
        exc_info=True
    )
