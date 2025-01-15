"""Error handling for the API."""
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from src.utils.logging import get_logger

logger = get_logger(__name__)

class APIError(Exception):
    """Base class for API errors."""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class DatabaseError(APIError):
    """Database-related errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )

class ValidationAPIError(APIError):
    """Validation errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

class NotFoundError(APIError):
    """Resource not found errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle API errors."""
    error_response = {
        "error": exc.message,
        "status_code": exc.status_code,
        "path": request.url.path
    }
    
    if exc.details:
        error_response["details"] = exc.details
        
    if hasattr(request.state, "request_id"):
        error_response["request_id"] = request.state.request_id
        
    logger.error(
        f"API Error: {exc.message}",
        extra={
            "error_details": exc.details,
            "status_code": exc.status_code,
            "path": request.url.path,
            "request_id": getattr(request.state, "request_id", None)
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle pydantic validation errors."""
    details = []
    for error in exc.errors():
        details.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
        
    return await api_error_handler(
        request,
        ValidationAPIError(
            message="Validation error",
            details={"validation_errors": details}
        )
    )

async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors."""
    return await api_error_handler(
        request,
        DatabaseError(
            message="Database error",
            details={"error": str(exc)}
        )
    )

def setup_error_handlers(app: FastAPI) -> None:
    """Set up error handlers for the application."""
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
