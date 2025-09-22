"""
Custom exception hierarchy for InterviewIQ application.
"""

class InterviewIQException(Exception):
    """Base exception for InterviewIQ application."""
    pass

class AIServiceError(InterviewIQException):
    """Base exception for AI service errors."""
    pass

class ServiceUnavailableError(AIServiceError):
    """Raised when a service is unavailable."""
    pass

class InvalidResponseError(AIServiceError):
    """Raised when AI response cannot be parsed."""
    pass

class RateLimitExceededError(InterviewIQException):
    """Raised when rate limit is exceeded."""
    pass

class ConfigurationError(InterviewIQException):
    """Raised when there are configuration issues."""
    pass
