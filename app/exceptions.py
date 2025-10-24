"""
Custom exception hierarchy for Confida application.
"""

from typing import Dict, Any

class ConfidaException(Exception):
    """Base exception for Confida application."""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        super().__init__(message)
        self.context = context or {}

class AIServiceError(ConfidaException):
    """Base exception for AI service errors."""
    pass

class ServiceUnavailableError(AIServiceError):
    """Raised when a service is unavailable."""
    pass

class InvalidResponseError(AIServiceError):
    """Raised when AI response cannot be parsed."""
    pass

class RateLimitExceededError(ConfidaException):
    """Raised when rate limit is exceeded."""
    pass

class ConfigurationError(ConfidaException):
    """Raised when there are configuration issues."""
    pass

class AdminError(ConfidaException):
    """Base exception for admin-related errors."""
    pass

class ServiceNotInitializedError(AdminError):
    """Raised when a service is not initialized."""
    pass

class ConfigurationRetrievalError(AdminError):
    """Raised when configuration cannot be retrieved."""
    pass

class StatisticsRetrievalError(AdminError):
    """Raised when statistics cannot be retrieved."""
    pass
