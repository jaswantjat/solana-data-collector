"""Custom error classes for the API."""
from typing import Dict, Optional, Any
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request

from src.utils.logging import get_logger

logger = get_logger(__name__)

class APIError(HTTPException):
    """Base class for API errors."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: Optional[str] = None
    ):
        """Initialize API error.
        
        Args:
            message: Error message
            details: Additional error details
            status_code: HTTP status code
            error_type: Optional error type override
        """
        self.timestamp = datetime.utcnow()
        self.error_type = error_type or self.__class__.__name__
        
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "error_type": self.error_type,
                "details": details,
                "timestamp": self.timestamp.isoformat()
            }
        )
        
        # Log the error
        logger.error(
            f"{self.error_type}: {message}",
            extra={
                "error_type": self.error_type,
                "details": details,
                "status_code": status_code
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

def setup_error_handlers(app: FastAPI):
    """Setup error handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors from FastAPI/Pydantic."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "message": "Request validation failed",
                "error_type": "ValidationError",
                "details": {"errors": exc.errors()},
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle custom API errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle any unhandled exceptions."""
        logger.exception("Unhandled exception occurred", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An unexpected error occurred",
                "error_type": "InternalServerError",
                "details": {"error": str(exc)},
                "timestamp": datetime.utcnow().isoformat()
            }
        )
