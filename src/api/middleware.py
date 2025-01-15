"""API middleware for request tracking and error handling."""
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from src.utils.logging import get_logger
from src.api.errors import APIError, ValidationError

logger = get_logger(__name__)

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and performance monitoring."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request, adding tracing headers.
        
        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The response with added tracing headers
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add tracing headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = str(int((time.time() - start_time) * 1000))
            
            return response
            
        except Exception as e:
            # Log error with request context
            logger.exception(
                f"Error processing request: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                }
            )
            
            # Convert to API error if needed
            if not isinstance(e, APIError):
                e = APIError(
                    message="Internal server error",
                    details={"error": str(e)}
                )
            
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )

def setup_middleware(app: FastAPI):
    """Set up all middleware for the application.
    
    Args:
        app: The FastAPI application instance
    """
    # Add request tracing
    app.add_middleware(RequestTracingMiddleware)
    
    # Add other middleware as needed
