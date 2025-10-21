"""
Unified Error Handling Service for Confida

This service consolidates all error handling functionality from multiple
error handling utilities into a single, comprehensive error handling service.
"""
import functools
import time
from typing import Any, Callable, Dict
from fastapi import HTTPException
from app.exceptions import ConfidaException, ServiceUnavailableError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class UnifiedErrorHandlingService:
    """Unified error handling service that consolidates all error handling functionality."""
    
    def __init__(self):
        self.error_contexts = {}
    
    # Decorator-based Error Handling
    def with_fallback(self, fallback_value: Any = None):
        """Simple fallback decorator."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {e}")
                    return fallback_value
            return wrapper
        return decorator
    
    def with_retry(self, max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
        """Enhanced retry decorator with exponential backoff."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            delay_time = delay * (backoff_factor ** attempt)
                            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay_time:.2f}s...")
                            time.sleep(delay_time)
                        else:
                            logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                
                raise last_exception
            return wrapper
        return decorator
    
    def with_logging(self, log_level: str = "info", log_args: bool = False, log_result: bool = False):
        """Decorator for consistent function logging."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                log_func = getattr(logger, log_level.lower(), logger.info)
                
                # Log function start
                if log_args:
                    log_func(f"Starting {func.__name__} with args={args}, kwargs={kwargs}")
                else:
                    log_func(f"Starting {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Log function success
                    if log_result:
                        log_func(f"Completed {func.__name__} with result={result}")
                    else:
                        log_func(f"Completed {func.__name__}")
                    
                    return result
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {e}")
                    raise
            return wrapper
        return decorator
    
    def with_validation(self, validator_func: Callable[[Any], bool], error_message: str = "Validation failed"):
        """Decorator for input validation."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if args and not validator_func(args[0]):
                    raise ValueError(error_message)
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def with_service_errors(self, operation_name: str = None, service_type: str = "ai"):
        """Unified decorator factory for handling service errors."""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    op_name = operation_name or func.__name__
                    logger.error(f"Error in {op_name}: {e}")
                    raise HTTPException(status_code=500, detail=f"Error in {op_name}: {str(e)}")
            return wrapper
        return decorator
    
    # Error Context Management
    def add_context(self, error: Exception, context: Dict[str, Any]) -> ConfidaException:
        """Add context information to an error."""
        if isinstance(error, ConfidaException):
            error.context = context
        return error
    
    def create_service_error(self, service: str, operation: str, original_error: Exception) -> ServiceUnavailableError:
        """Create a service error with context."""
        error = ServiceUnavailableError(f"{service} {operation} failed: {str(original_error)}")
        error.context = {
            "service": service,
            "operation": operation,
            "original_error": str(original_error)
        }
        return error
    
    def create_validation_error(self, field: str, value: Any, reason: str) -> ConfidaException:
        """Create a validation error with context."""
        error = ConfidaException(f"Validation failed for {field}: {reason}")
        error.context = {
            "field": field,
            "value": str(value),
            "reason": reason
        }
        return error
    
    # Error Classification
    def classify_error(self, error: Exception) -> str:
        """Classify error type for appropriate handling."""
        error_str = str(error).lower()
        
        if any(kw in error_str for kw in ["timeout", "connection", "network", "rate limit"]):
            return "transient"
        elif any(kw in error_str for kw in ["503", "502", "504", "server error"]):
            return "service_unavailable"
        elif any(kw in error_str for kw in ["quota", "429", "too many requests"]):
            return "quota_exceeded"
        elif any(kw in error_str for kw in ["unauthorized", "forbidden", "400", "401", "403"]):
            return "permanent"
        else:
            return "unknown"
    
    # Fallback Management
    def get_fallback_response(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Get appropriate fallback response based on operation and error."""
        error_type = self.classify_error(error)
        
        fallback_responses = {
            "question_generation": {
                "questions": [
                    "Tell me about your experience with Python programming.",
                    "How do you approach debugging complex issues?",
                    "Describe a challenging project you've worked on.",
                    "What's your experience with database design?",
                    "How do you ensure code quality in your projects?"
                ],
                "metadata": {"source": "fallback", "reason": "service_unavailable"}
            },
            "answer_analysis": {
                "analysis": "Analysis temporarily unavailable. Please try again later.",
                "score": {"clarity": 7.0, "confidence": 7.0, "technical": 7.0, "overall": 7.0},
                "suggestions": ["Analysis service is temporarily unavailable", "Please try again in a few moments"],
                "metadata": {"source": "fallback", "reason": "service_unavailable"}
            },
            "file_upload": {
                "success": False,
                "error": "File upload service temporarily unavailable",
                "suggestion": "Please try again later"
            }
        }
        
        return fallback_responses.get(operation, {
            "error": f"Service temporarily unavailable for {operation}",
            "message": "Please try again later"
        })
    
    # Circuit Breaker Pattern
    def create_circuit_breaker(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """Create a circuit breaker for service protection."""
        class CircuitBreaker:
            def __init__(self, failure_threshold: int, recovery_timeout: float):
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "closed"  # closed, open, half_open
            
            def can_execute(self) -> bool:
                """Check if operation can be executed."""
                if self.state == "closed":
                    return True
                elif self.state == "open":
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.state = "half_open"
                        return True
                    return False
                else:  # half_open
                    return True
            
            def record_success(self):
                """Record successful operation."""
                self.failure_count = 0
                self.state = "closed"
            
            def record_failure(self):
                """Record failed operation."""
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        
        return CircuitBreaker(failure_threshold, recovery_timeout)

# Convenience functions for backward compatibility
def with_fallback(fallback_value: Any = None):
    """Simple fallback decorator."""
    service = UnifiedErrorHandlingService()
    return service.with_fallback(fallback_value)

def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Simple retry decorator."""
    service = UnifiedErrorHandlingService()
    return service.with_retry(max_retries, delay)

def with_logging(log_level: str = "info", log_args: bool = False, log_result: bool = False):
    """Decorator for consistent function logging."""
    service = UnifiedErrorHandlingService()
    return service.with_logging(log_level, log_args, log_result)

def with_validation(validator_func: Callable[[Any], bool], error_message: str = "Validation failed"):
    """Decorator for input validation."""
    service = UnifiedErrorHandlingService()
    return service.with_validation(validator_func, error_message)

def handle_service_errors(operation_name: str = None, service_type: str = "ai"):
    """Unified decorator factory for handling service errors."""
    service = UnifiedErrorHandlingService()
    return service.with_service_errors(operation_name, service_type)

# Error context functions
def add_context(error: Exception, context: Dict[str, Any]) -> ConfidaException:
    """Add context information to an error."""
    service = UnifiedErrorHandlingService()
    return service.add_context(error, context)

def create_service_error(service: str, operation: str, original_error: Exception) -> ServiceUnavailableError:
    """Create a service error with context."""
    error_handler = UnifiedErrorHandlingService()
    return error_handler.create_service_error(service, operation, original_error)

def create_validation_error(field: str, value: Any, reason: str) -> ConfidaException:
    """Create a validation error with context."""
    error_handler = UnifiedErrorHandlingService()
    return error_handler.create_validation_error(field, value, reason)
