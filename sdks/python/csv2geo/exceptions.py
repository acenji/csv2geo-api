"""Custom exceptions for CSV2GEO SDK."""


class CSV2GEOError(Exception):
    """Base exception for CSV2GEO SDK."""

    def __init__(self, message: str, code: str = None, status: int = None):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(self.message)


class AuthenticationError(CSV2GEOError):
    """Raised when API key is missing, invalid, or revoked."""
    pass


class RateLimitError(CSV2GEOError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class InvalidRequestError(CSV2GEOError):
    """Raised when request parameters are invalid."""
    pass


class PermissionError(CSV2GEOError):
    """Raised when API key lacks required permission."""
    pass


class APIError(CSV2GEOError):
    """Raised for general API errors."""
    pass
