"""Custom error classes for the API."""
from typing import Dict, Optional, Any
from fastapi import HTTPException, status
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class APIError(HTTPException):
    """Base class for API errors."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """Initialize API error.
        
        Args:
            message: Error message
            details: Additional error details
            status_code: HTTP status code
        """
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "error_type": self.__class__.__name__,
                "details": details
            }
        )

class ValidationError(APIError):
    """Raised when request validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

class NotFoundError(APIError):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_404_NOT_FOUND
        )

class DatabaseError(APIError):
    """Raised when a database operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

class ConfigError(APIError):
    """Raised when there is a configuration error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

class AuthenticationError(APIError):
    """Raised when authentication fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class AuthorizationError(APIError):
    """Raised when authorization fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )

class ExternalAPIError(APIError):
    """Raised when an external API call fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_502_BAD_GATEWAY
        )

class ServiceUnavailableError(APIError):
    """Raised when a required service is unavailable."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            details=details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

def setup_error_handlers(app):
    """Setup error handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(APIError)
    async def api_error_handler(request, exc):
        """Handle API errors."""
        return {
            "status": "error",
            "message": exc.detail["message"],
            "error_type": exc.detail["error_type"],
            "details": exc.detail["details"],
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        """Handle request validation errors."""
        return {
            "status": "error",
            "message": "Request validation failed",
            "error_type": "ValidationError",
            "details": {
                "errors": [
                    {
                        "loc": err["loc"],
                        "msg": err["msg"],
                        "type": err["type"]
                    }
                    for err in exc.errors()
                ]
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.exception_handler(Exception)
    async def general_error_handler(request, exc):
        """Handle unexpected errors."""
        logger.exception("Unexpected error occurred")
        return {
            "status": "error",
            "message": "An unexpected error occurred",
            "error_type": "InternalServerError",
            "details": {
                "type": type(exc).__name__,
                "message": str(exc)
            } if app.debug else None,
            "timestamp": datetime.utcnow().isoformat()
        }
