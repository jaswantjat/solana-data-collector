"""Custom error classes for the API."""
from typing import Dict, Optional, Any, List
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI, Request
from pydantic import ValidationError as PydanticValidationError

from src.utils.logging import get_logger

logger = get_logger(__name__)

class APIError(HTTPException):
    """Base class for API errors."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """Initialize API error.
        
        Args:
            message: Error message
            details: Additional error details
            status_code: HTTP status code
            error_type: Optional error type override
            error_code: Optional error code for client reference
        """
        self.timestamp = datetime.utcnow()
        self.error_type = error_type or self.__class__.__name__
        self.error_code = error_code or f"ERR_{status_code}"
        
        error_detail = {
            "message": message,
            "error_type": self.error_type,
            "error_code": self.error_code,
            "details": details or {},
            "timestamp": self.timestamp.isoformat()
        }
        
        super().__init__(
            status_code=status_code,
            detail=error_detail
        )
        
        # Log the error with context
        logger.error(
            f"{self.error_type} ({self.error_code}): {message}",
            extra={
                "error_type": self.error_type,
                "error_code": self.error_code,
                "details": details,
                "status_code": status_code,
                "timestamp": self.timestamp.isoformat()
            }
        )

class ValidationError(APIError):
    """Raised when request validation fails."""
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        field_errors: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize validation error.
        
        Args:
            message: Error message
            details: Additional error details
            field_errors: List of field-specific validation errors
        """
        error_details = details or {}
        if field_errors:
            error_details["field_errors"] = field_errors
            
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="ERR_VALIDATION"
        )

class NotFoundError(APIError):
    """Raised when a requested resource is not found."""
    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource that was not found
            resource_id: ID of resource that was not found
            details: Additional error details
        """
        error_details = details or {}
        error_details.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ERR_NOT_FOUND"
        )

class DatabaseError(APIError):
    """Raised when a database operation fails."""
    def __init__(
        self,
        message: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize database error.
        
        Args:
            message: Error message
            operation: Database operation that failed
            details: Additional error details
        """
        error_details = details or {}
        error_details["operation"] = operation
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="ERR_DATABASE"
        )

class ConfigError(APIError):
    """Raised when there is a configuration error."""
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Key of the configuration that failed
            details: Additional error details
        """
        error_details = details or {}
        if config_key:
            error_details["config_key"] = config_key
            
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ERR_CONFIG"
        )

class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    def __init__(
        self,
        message: str,
        limit: int,
        window: int,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            limit: Rate limit that was exceeded
            window: Time window in seconds
            details: Additional error details
        """
        error_details = details or {}
        error_details.update({
            "limit": limit,
            "window": window
        })
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="ERR_RATE_LIMIT"
        )

class AuthenticationError(APIError):
    """Raised when authentication fails."""
    def __init__(
        self,
        message: str,
        auth_type: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize authentication error.
        
        Args:
            message: Error message
            auth_type: Type of authentication that failed
            details: Additional error details
        """
        error_details = details or {}
        error_details["auth_type"] = auth_type
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="ERR_AUTH"
        )

class AuthorizationError(APIError):
    """Raised when authorization fails."""
    def __init__(
        self,
        message: str,
        required_permission: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize authorization error.
        
        Args:
            message: Error message
            required_permission: Permission that was required
            details: Additional error details
        """
        error_details = details or {}
        error_details["required_permission"] = required_permission
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ERR_FORBIDDEN"
        )

class ExternalAPIError(APIError):
    """Raised when an external API call fails."""
    def __init__(
        self,
        message: str,
        service: str,
        endpoint: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize external API error.
        
        Args:
            message: Error message
            service: External service that failed
            endpoint: Endpoint that was called
            details: Additional error details
        """
        error_details = details or {}
        error_details.update({
            "service": service,
            "endpoint": endpoint
        })
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="ERR_EXTERNAL_API"
        )

class ServiceUnavailableError(APIError):
    """Raised when a required service is unavailable."""
    def __init__(
        self,
        message: str,
        service: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize service unavailable error.
        
        Args:
            message: Error message
            service: Service that is unavailable
            details: Additional error details
        """
        error_details = details or {}
        error_details["service"] = service
        
        super().__init__(
            message=message,
            details=error_details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="ERR_SERVICE_UNAVAILABLE"
        )

def setup_error_handlers(app: FastAPI):
    """Setup error handlers for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        field_errors = []
        for error in exc.errors():
            field_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "type": error["type"],
                "message": error["msg"]
            })
            
        error = ValidationError(
            message="Request validation failed",
            field_errors=field_errors
        )
        
        return JSONResponse(
            status_code=error.status_code,
            content=error.detail
        )
        
    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
        """Handle Pydantic validation errors."""
        field_errors = []
        for error in exc.errors():
            field_errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "type": error["type"],
                "message": error["msg"]
            })
            
        error = ValidationError(
            message="Data validation failed",
            field_errors=field_errors
        )
        
        return JSONResponse(
            status_code=error.status_code,
            content=error.detail
        )
        
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        """Handle API errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
        
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        logger.exception("Unexpected error occurred")
        
        error = APIError(
            message="An unexpected error occurred",
            details={"error": str(exc)},
            error_code="ERR_INTERNAL"
        )
        
        return JSONResponse(
            status_code=error.status_code,
            content=error.detail
        )
