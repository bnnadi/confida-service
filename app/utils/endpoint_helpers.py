"""
Endpoint helper utilities for common patterns and error handling.
"""

from functools import wraps
from fastapi import HTTPException
from app.dependencies import get_ai_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


def handle_ai_service_errors(func):
    """Decorator to handle common AI service errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        ai_service = get_ai_service()
        if not ai_service:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        try:
            return await func(ai_service, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=f"Error in {func.__name__}: {str(e)}")
    return wrapper


def handle_service_errors(operation_name: str):
    """Decorator factory for handling service errors with custom operation names."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ai_service = get_ai_service()
            if not ai_service:
                raise HTTPException(status_code=503, detail="AI service not available")
            
            try:
                return await func(ai_service, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}")
                raise HTTPException(status_code=500, detail=f"Error in {operation_name}: {str(e)}")
        return wrapper
    return decorator
