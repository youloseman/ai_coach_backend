"""
Custom exceptions for better error handling
"""


class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(AppException):
    """Validation error"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class NotFoundError(AppException):
    """Resource not found"""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class UnauthorizedError(AppException):
    """Unauthorized access"""
    def __init__(self, message: str):
        super().__init__(message, status_code=401)


class DatabaseError(AppException):
    """Database operation error"""
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class ExternalAPIError(AppException):
    """External API error (Strava, OpenAI, etc)"""
    def __init__(self, message: str, service: str):
        self.service = service
        super().__init__(f"{service} error: {message}", status_code=502)


class RateLimitError(AppException):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)
