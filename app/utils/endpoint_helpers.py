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
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get appropriate service based on type
            if service_type == "ai":
                service = get_ai_service()
            else:
                # For future extension to other service types
                service = get_service_by_type(service_type) if hasattr(globals(), 'get_service_by_type') else None
            
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
