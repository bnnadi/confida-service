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