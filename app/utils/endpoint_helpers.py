"""
Endpoint helper utilities for common patterns and error handling.
"""

from functools import wraps
from fastapi import HTTPException
from app.dependencies import get_ai_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


def handle_service_errors(operation_name: str = None, service_type: str = "ai"):
    """Unified decorator factory for handling service errors."""
    service_getters = {
        "ai": get_ai_service,
        # Add other service types as needed
    }
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            service_getter = service_getters.get(service_type)
            if not service_getter:
                raise HTTPException(status_code=503, detail=f"Unknown service type: {service_type}")
            
            service = service_getter()
            if not service:
                raise HTTPException(status_code=503, detail=f"{service_type.title()} service not available")
            
            try:
                return await func(service, *args, **kwargs)
            except Exception as e:
                op_name = operation_name or func.__name__
                logger.error(f"Error in {op_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Error in {op_name}: {str(e)}")
        return wrapper
    return decorator


# Convenience decorators for backward compatibility
def handle_ai_service_errors(func):
    """Decorator to handle common AI service errors."""
    return handle_service_errors(service_type="ai")(func)
