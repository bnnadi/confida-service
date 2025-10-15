from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Callable
from functools import wraps
from app.utils.cache import cache_manager, cache_metrics
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/cache", tags=["cache"])
settings = get_settings()

def require_cache_enabled(func: Callable) -> Callable:
    """Decorator to ensure cache is enabled for cache management endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not settings.CACHE_ENABLED:
            raise HTTPException(status_code=400, detail="Caching is disabled")
        return await func(*args, **kwargs)
    return wrapper

def handle_cache_errors(func: Callable) -> Callable:
    """Decorator to handle common cache operation errors."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to {func.__name__.replace('_', ' ')}: {str(e)}")
    return wrapper

@router.get("/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """Get cache statistics and performance metrics."""
    if not settings.CACHE_ENABLED:
        return {"enabled": False, "message": "Caching is disabled"}
    
    stats = cache_manager.get_stats()
    metrics = cache_metrics.get_metrics()
    
    return {
        "enabled": True,
        "backend": stats["backend"],
        "cache_stats": stats,
        "metrics": metrics,
        "configuration": {
            "cache_backend": settings.CACHE_BACKEND,
            "ttl_config": settings.cache_ttl_config
        }
    }

@router.post("/clear")
@require_cache_enabled
@handle_cache_errors
async def clear_cache(pattern: str = "*"):
    """Clear cache entries matching a pattern."""
    cleared_count = await cache_manager.clear_pattern(pattern)
    return {
        "success": True,
        "pattern": pattern,
        "cleared_entries": cleared_count,
        "message": f"Cleared {cleared_count} cache entries matching pattern: {pattern}"
    }

@router.post("/clear/question-generation")
@require_cache_enabled
@handle_cache_errors
async def clear_question_generation_cache():
    """Clear question generation cache entries."""
    pattern = "ai_cache:*:question_generation:*"
    cleared_count = await cache_manager.clear_pattern(pattern)
    return {
        "success": True,
        "operation": "question_generation",
        "cleared_entries": cleared_count,
        "message": f"Cleared {cleared_count} question generation cache entries"
    }

@router.post("/clear/answer-analysis")
@require_cache_enabled
@handle_cache_errors
async def clear_answer_analysis_cache():
    """Clear answer analysis cache entries."""
    pattern = "ai_cache:*:answer_analysis:*"
    cleared_count = await cache_manager.clear_pattern(pattern)
    return {
        "success": True,
        "operation": "answer_analysis",
        "cleared_entries": cleared_count,
        "message": f"Cleared {cleared_count} answer analysis cache entries"
    }

@router.post("/reset-metrics")
@handle_cache_errors
async def reset_cache_metrics():
    """Reset cache metrics."""
    cache_metrics.reset_metrics()
    cache_manager.reset_stats()
    return {"success": True, "message": "Cache metrics reset successfully"}

@router.get("/health")
async def cache_health_check():
    """Check cache system health."""
    try:
        if not settings.CACHE_ENABLED:
            return {
                "status": "disabled",
                "message": "Caching is disabled"
            }
        
        # Test cache operations
        test_key = "health_check_test"
        test_value = {"test": True, "timestamp": "2024-01-01T00:00:00Z"}
        
        # Test set
        set_success = await cache_manager.set(test_key, test_value, 60)
        if not set_success:
            return {
                "status": "unhealthy",
                "message": "Cache set operation failed"
            }
        
        # Test get
        retrieved_value = await cache_manager.get(test_key)
        if retrieved_value != test_value:
            return {
                "status": "unhealthy",
                "message": "Cache get operation failed or returned incorrect value"
            }
        
        # Test delete
        delete_success = await cache_manager.delete(test_key)
        if not delete_success:
            return {
                "status": "unhealthy",
                "message": "Cache delete operation failed"
            }
        
        return {
            "status": "healthy",
            "backend": cache_manager.get_stats()["backend"],
            "message": "Cache system is working correctly"
        }
        
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Cache health check failed: {str(e)}"
        }
