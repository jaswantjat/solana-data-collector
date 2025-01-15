"""API middleware for request tracking and error handling."""
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from src.utils.logging import get_logger

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
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add tracing headers
            response.headers["X-Request-ID"] = request_id
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id
                }
            )

def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application.
    
    Args:
        app: The FastAPI application instance
    """
    # Add request tracing middleware
    app.add_middleware(RequestTracingMiddleware)
    
    # Add other middleware as needed
    # app.add_middleware(AuthenticationMiddleware)
    # app.add_middleware(RateLimitingMiddleware)
