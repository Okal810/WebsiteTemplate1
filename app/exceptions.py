"""
Centralized Exception Classes for API Error Handling

Provides consistent, structured error responses across all endpoints.
Usage:
    from app.exceptions import ValidationError, AuthenticationError
    raise ValidationError("Invalid email format")
"""


class APIException(Exception):
    """Base exception for all API errors with structured JSON response."""
    status_code = 400
    
    def __init__(self, message: str, status_code: int = None, payload: dict = None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self) -> dict:
        """Convert exception to JSON-serializable dictionary."""
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv


class ValidationError(APIException):
    """Raised when input validation fails (400 Bad Request)."""
    status_code = 400


class AuthenticationError(APIException):
    """Raised when authentication fails (401 Unauthorized)."""
    status_code = 401


class ForbiddenError(APIException):
    """Raised when user lacks permission (403 Forbidden)."""
    status_code = 403


class NotFoundError(APIException):
    """Raised when resource is not found (404 Not Found)."""
    status_code = 404


class RateLimitError(APIException):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""
    status_code = 429
    
    def __init__(self, message: str = "Rate limit exceeded. Please try again later.", 
                 retry_after: int = None):
        super().__init__(message)
        if retry_after:
            self.payload = {'retry_after': retry_after}


class ConflictError(APIException):
    """Raised when there's a conflict with current state (409 Conflict)."""
    status_code = 409


class ServerError(APIException):
    """Raised for internal server errors (500 Internal Server Error)."""
    status_code = 500
