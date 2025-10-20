"""
Error handling utilities and decorators for consistent error management across services.
"""

import functools
from typing import Callable, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


def with_fallback(fallback_value: Any = None):
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


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Simple retry decorator."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        raise e
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


