"""
Error handling utilities and decorators for consistent error management across services.
"""

import functools
from typing import Callable, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


def with_fallback(fallback_func: Optional[Callable] = None, fallback_value: Any = None):
    """
    Decorator for consistent error handling with fallback.
    
    Args:
        fallback_func: Function to call on error (receives same args as original)
        fallback_value: Static value to return on error (if no fallback_func)
    
    Usage:
        @with_fallback(fallback_value=[])
        def get_questions():
            # risky operation
            return questions
        
        @with_fallback(fallback_func=lambda role, count: get_default_questions(role, count))
        def get_questions_for_role(role: str, count: int):
            # risky operation
            return questions
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                
                if fallback_func:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function also failed: {fallback_error}")
                        return fallback_value
                else:
                    return fallback_value
        
        return wrapper
    return decorator


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
    
    Usage:
        @with_retry(max_retries=3, delay=1.0)
        def api_call():
            # operation that might fail
            return result
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        
        return wrapper
    return decorator


def with_logging(log_level: str = "info", log_args: bool = False, log_result: bool = False):
    """
    Decorator for consistent function logging.
    
    Args:
        log_level: Logging level ('debug', 'info', 'warning', 'error')
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    
    Usage:
        @with_logging(log_level="info", log_args=True)
        def process_data(data):
            return processed_data
    """
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


def with_validation(validator_func: Callable[[Any], bool], error_message: str = "Validation failed"):
    """
    Decorator for input validation.
    
    Args:
        validator_func: Function that takes the first argument and returns bool
        error_message: Error message to raise if validation fails
    
    Usage:
        @with_validation(lambda x: x > 0, "Value must be positive")
        def process_positive_number(value):
            return value * 2
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args and not validator_func(args[0]):
                raise ValueError(error_message)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class ErrorHandler:
    """Context manager for handling errors in code blocks."""
    
    def __init__(self, fallback_value: Any = None, log_error: bool = True):
        self.fallback_value = fallback_value
        self.log_error = log_error
        self.error_occurred = False
        self.last_error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_occurred = True
            self.last_error = exc_val
            
            if self.log_error:
                logger.error(f"Error in context: {exc_val}")
            
            # Suppress the exception if we have a fallback
            if self.fallback_value is not None:
                return True  # Suppress the exception
        
        return False  # Don't suppress if no fallback


# Example usage patterns for common service methods
def service_method_with_fallback(fallback_value: Any = None):
    """Convenience decorator for service methods that should return fallback on error."""
    return with_fallback(fallback_value=fallback_value)


def database_operation_with_retry(max_retries: int = 3):
    """Convenience decorator for database operations that should be retried."""
    return with_retry(max_retries=max_retries, delay=0.5, backoff_factor=1.5)


def api_call_with_logging():
    """Convenience decorator for API calls that should be logged."""
    return with_logging(log_level="info", log_args=True)
