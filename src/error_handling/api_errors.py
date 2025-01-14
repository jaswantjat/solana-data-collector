from typing import Optional, Dict, Any
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class APIErrorType(Enum):
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    SERIALIZATION = "serialization"
    VALIDATION = "validation"
    UNKNOWN = "unknown"

class APIError(Exception):
    """Custom exception for API-related errors"""
    def __init__(
        self,
        message: str,
        error_type: APIErrorType,
        status_code: Optional[int] = None,
        response_data: Optional[Dict] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.response_data = response_data
        self.original_error = original_error
        super().__init__(self.message)

class APIKeyError(APIError):
    """Error for missing or invalid API keys"""
    def __init__(self, api_name: str, message: Optional[str] = None):
        super().__init__(
            message or f"Missing or invalid API key for {api_name}",
            APIErrorType.AUTHENTICATION
        )

class RateLimitError(APIError):
    """Error for rate limit exceeded"""
    def __init__(self, api_name: str, retry_after: Optional[int] = None):
        super().__init__(
            f"Rate limit exceeded for {api_name}",
            APIErrorType.RATE_LIMIT,
            response_data={"retry_after": retry_after} if retry_after else None
        )

class NotFoundError(APIError):
    """Error for resource not found"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} not found: {resource_id}",
            APIErrorType.NOT_FOUND
        )

class SerializationError(APIError):
    """Error for data serialization/deserialization issues"""
    def __init__(self, message: str, data: Any = None):
        super().__init__(
            message,
            APIErrorType.SERIALIZATION,
            response_data={"data": str(data)} if data else None
        )

def handle_api_error(
    error: Exception,
    api_name: str,
    endpoint: str,
    status_code: Optional[int] = None,
    response_data: Optional[Dict] = None
) -> APIError:
    """Convert various exceptions into appropriate APIError types"""
    
    # Handle aiohttp specific errors
    if str(error.__class__.__name__) == "ClientConnectorError":
        return APIError(
            f"Network error connecting to {api_name}: {str(error)}",
            APIErrorType.NETWORK_ERROR
        )
        
    # Handle common HTTP status codes
    if status_code:
        if status_code == 401:
            return APIKeyError(api_name)
        elif status_code == 403:
            return APIError(
                f"Access forbidden to {api_name} {endpoint}",
                APIErrorType.AUTHENTICATION,
                status_code
            )
        elif status_code == 404:
            return NotFoundError(endpoint, str(response_data) if response_data else "unknown")
        elif status_code == 429:
            retry_after = response_data.get("retry_after") if response_data else None
            return RateLimitError(api_name, retry_after)
        elif 500 <= status_code < 600:
            return APIError(
                f"{api_name} server error: {response_data}",
                APIErrorType.SERVER_ERROR,
                status_code
            )
            
    # Handle serialization errors
    if isinstance(error, (TypeError, ValueError)) and "serialize" in str(error).lower():
        return SerializationError(str(error))
        
    # Default to unknown error
    return APIError(
        f"Unknown error in {api_name} {endpoint}: {str(error)}",
        APIErrorType.UNKNOWN,
        original_error=error
    )

def should_retry(error: APIError, retry_count: int, max_retries: int = 3) -> bool:
    """Determine if an API call should be retried based on the error type"""
    if retry_count >= max_retries:
        return False
        
    retriable_errors = {
        APIErrorType.RATE_LIMIT,
        APIErrorType.SERVER_ERROR,
        APIErrorType.NETWORK_ERROR
    }
    
    return error.error_type in retriable_errors
