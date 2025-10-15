"""
Metrics decorator for automatic performance tracking.
Simplifies repetitive metrics recording across AI services.
"""

import time
import functools
from typing import Callable, Any, Optional
from app.utils.metrics import metrics
from app.utils.logger import get_logger

logger = get_logger(__name__)

def with_metrics(operation: str, service_param: str = "preferred_service"):
    """
    Decorator to automatically record metrics for AI service operations.
    
    Args:
        operation: The operation name for metrics
        service_param: The parameter name that contains the service type
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            service_name = kwargs.get(service_param, "auto")
            
            try:
                result = func(*args, **kwargs)
                
                # Record success metrics
                duration = time.time() - start_time
                metrics.record_ai_service_request(
                    service=service_name,
                    operation=operation,
                    status="success",
                    duration=duration
                )
                
                return result
                
            except Exception as e:
                # Record error metrics
                duration = time.time() - start_time
                metrics.record_ai_service_request(
                    service=service_name,
                    operation=operation,
                    status="error",
                    duration=duration
                )
                raise
                
        return wrapper
    return decorator

def with_error_handling(fallback_func: Optional[Callable] = None, log_errors: bool = True):
    """
    Decorator to handle errors with optional fallback.
    
    Args:
        fallback_func: Function to call on error
        log_errors: Whether to log errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {e}")
                
                if fallback_func:
                    return fallback_func(*args, **kwargs)
                raise
                
        return wrapper
    return decorator
