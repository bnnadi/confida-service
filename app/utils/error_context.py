"""
Error context management utility for better debugging and error handling.
"""

from typing import Dict, Any, Optional
from app.exceptions import InterviewIQException, ServiceUnavailableError

class ErrorContext:
    """Utility for adding context to errors."""
    
    @staticmethod
    def add_context(error: Exception, context: Dict[str, Any]) -> InterviewIQException:
        """Add context information to an error."""
        if isinstance(error, InterviewIQException):
            error.context = context
        return error
    
    @staticmethod
    def create_service_error(service: str, operation: str, original_error: Exception) -> ServiceUnavailableError:
        """Create a service error with context."""
        error = ServiceUnavailableError(f"{service} {operation} failed: {str(original_error)}")
        error.context = {
            "service": service,
            "operation": operation,
            "original_error": str(original_error)
        }
        return error
    
    @staticmethod
    def create_validation_error(field: str, value: Any, reason: str) -> InterviewIQException:
        """Create a validation error with context."""
        error = InterviewIQException(f"Validation failed for {field}: {reason}")
        error.context = {
            "field": field,
            "value": str(value),
            "reason": reason
        }
        return error
