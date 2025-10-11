from fastapi import APIRouter, HTTPException, status, Depends
from app.config import settings
from app.utils.service_tester import ServiceTester
from app.utils.endpoint_helpers import handle_service_errors
from app.exceptions import ServiceNotInitializedError, ConfigurationRetrievalError, StatisticsRetrievalError
from app.dependencies import get_ai_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/services/status")
async def get_services_status(ai_service=Depends(get_ai_service)):
    """
    Get detailed status of all AI services.
    """
    if ai_service is None:
        logger.warning("AI service not initialized when getting service status")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not initialized"
        )
    
    try:
        return {
            "available_services": ai_service.get_available_services(),
            "service_priority": ai_service.get_service_priority(),
            "configuration": {
                "ollama_url": settings.OLLAMA_BASE_URL,
                "ollama_model": settings.OLLAMA_MODEL,
                "openai_configured": settings.is_openai_configured,
                "openai_model": settings.OPENAI_MODEL,
                "anthropic_configured": settings.is_anthropic_configured,
                "anthropic_model": settings.ANTHROPIC_MODEL
            }
        }
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve service status"
        )

@router.post("/services/test")
async def test_services(ai_service=Depends(get_ai_service)):
    """
    Test all configured AI services.
    """
    if ai_service is None:
        logger.warning("AI service not initialized when testing services")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not initialized"
        )
    
    try:
        tester = ServiceTester(ai_service, settings)
        test_results = tester.test_all_services()
        return {"test_results": test_results}
    except Exception as e:
        logger.error(f"Error testing services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test services"
        )


@router.get("/health")
async def get_admin_health():
    """
    Get admin health status.
    """
    try:
        return {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00Z",
            "admin_available": True
        }
    except Exception as e:
        logger.error(f"Error getting admin health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve admin health status"
        )


@router.get("/config")
async def get_configuration():
    """
    Get system configuration (non-sensitive settings only).
    """
    try:
        return {
            "environment": "development",  # This would come from settings
            "version": "1.0.0",  # This would come from settings
            "features": {
                "ai_services": {
                    "ollama_enabled": bool(settings.OLLAMA_BASE_URL),
                    "openai_enabled": settings.is_openai_configured,
                    "anthropic_enabled": settings.is_anthropic_configured
                },
                "database_enabled": bool(settings.DATABASE_URL),
                "rate_limiting_enabled": getattr(settings, 'RATE_LIMIT_ENABLED', False)
            },
            "limits": {
                "max_tokens": getattr(settings, 'MAX_TOKENS', 4000),
                "temperature": getattr(settings, 'TEMPERATURE', 0.7)
            }
        }
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@router.get("/stats")
async def get_system_stats():
    """
    Get system statistics.
    """
    try:
        # This would typically query the database for real stats
        return {
            "total_users": 0,  # Would be calculated from database
            "total_sessions": 0,  # Would be calculated from database
            "total_questions": 0,  # Would be calculated from database
            "uptime": "0 days, 0 hours, 0 minutes",  # Would be calculated
            "last_updated": "2024-01-15T10:30:00Z"
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system statistics"
        )

@router.get("/config/validation")
async def get_config_validation():
    """
    Get comprehensive configuration validation results.
    """
    try:
        validation_result = settings.validate_configuration_with_warnings()
        return {
            "validation": validation_result,
            "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
        }
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate configuration"
        )

@router.get("/config/validation/summary")
async def get_config_validation_summary():
    """
    Get a summary of configuration validation results.
    """
    try:
        summary = settings.get_validation_summary()
        return {
            "summary": summary,
            "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
        }
    except Exception as e:
        logger.error(f"Error getting validation summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get validation summary"
        )

@router.get("/config/validation/{setting_name}")
async def validate_specific_setting(setting_name: str):
    """
    Validate a specific configuration setting.
    """
    try:
        is_valid, errors = settings.validate_specific_setting(setting_name)
        return {
            "setting": setting_name,
            "is_valid": is_valid,
            "errors": errors,
            "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
        }
    except Exception as e:
        logger.error(f"Error validating setting {setting_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate setting {setting_name}"
        )

@router.get("/rate-limits")
async def get_rate_limits():
    """
    Get current rate limit configuration.
    """
    try:
        return {
            "enabled": settings.RATE_LIMIT_ENABLED,
            "backend": settings.RATE_LIMIT_BACKEND,
            "default_limits": {
                "requests": settings.RATE_LIMIT_DEFAULT_REQUESTS,
                "window": settings.RATE_LIMIT_DEFAULT_WINDOW
            },
            "endpoint_limits": settings.rate_limit_per_endpoint,
            "user_type_limits": settings.rate_limit_per_user_type,
            "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
        }
    except Exception as e:
        logger.error(f"Error getting rate limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit configuration"
        )

@router.get("/rate-limits/status/{client_id}")
async def get_rate_limit_status(client_id: str, user_type: str = "free"):
    """
    Get rate limit status for a specific client.
    """
    try:
        from app.middleware.enhanced_rate_limiter import EnhancedRateLimiter
        
        rate_limiter = EnhancedRateLimiter()
        status = rate_limiter.get_rate_limit_status(client_id, user_type)
        
        return {
            "client_id": client_id,
            "user_type": user_type,
            "status": status,
            "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
        }
    except Exception as e:
        logger.error(f"Error getting rate limit status for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rate limit status for client {client_id}"
        )

@router.post("/rate-limits/reset/{client_id}")
async def reset_rate_limits(client_id: str, user_type: str = "free"):
    """
    Reset rate limits for a specific client.
    """
    try:
        from app.middleware.enhanced_rate_limiter import EnhancedRateLimiter
        
        rate_limiter = EnhancedRateLimiter()
        success = rate_limiter.reset_rate_limit(client_id, user_type)
        
        if success:
            return {
                "message": f"Rate limits reset successfully for client {client_id}",
                "client_id": client_id,
                "user_type": user_type,
                "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to reset rate limits for client {client_id}"
            )
    except Exception as e:
        logger.error(f"Error resetting rate limits for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset rate limits for client {client_id}"
        )

@router.get("/rate-limits/test")
async def test_rate_limits():
    """
    Test rate limiting configuration.
    """
    try:
        from app.middleware.enhanced_rate_limiter import EnhancedRateLimiter
        from fastapi import Request
        
        # Create a mock request for testing
        class MockRequest:
            def __init__(self):
                self.url = type('obj', (object,), {'path': '/api/v1/test'})()
                self.client = type('obj', (object,), {'host': '127.0.0.1'})()
                self.state = type('obj', (object,), {'user_type': 'free'})()
        
        rate_limiter = EnhancedRateLimiter()
        mock_request = MockRequest()
        
        # Test rate limit check
        result = rate_limiter.check_rate_limit(mock_request, "test_client", "free")
        
        return {
            "test_result": result,
            "configuration": {
                "enabled": settings.RATE_LIMIT_ENABLED,
                "backend": settings.RATE_LIMIT_BACKEND,
                "endpoint_limits": settings.rate_limit_per_endpoint,
                "user_type_limits": settings.rate_limit_per_user_type
            },
            "timestamp": "2024-01-15T10:30:00Z"  # Would be current timestamp
        }
    except Exception as e:
        logger.error(f"Error testing rate limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test rate limit configuration"
        ) 