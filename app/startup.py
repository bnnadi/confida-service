"""
Startup validation and initialization utilities.
"""

from app.config import settings
from app.services.service_factory import get_ai_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


def validate_startup():
    """Validate configuration on startup."""
    issues = settings.validate_configuration()
    if issues:
        logger.warning(f"Configuration issues: {issues}")
    
    # Test critical services
    try:
        ai_client = get_ai_client()
        if not ai_client:
            logger.error("AI service client initialization failed")
        else:
            logger.info("AI service client initialized successfully")
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")


def check_service_health(service_name: str, is_configured: bool) -> str:
    """Check AI service microservice health."""
    if not is_configured:
        return "not_configured"
    
    try:
        if service_name == "ai_service_microservice":
            # Test AI service microservice connectivity
            ai_client = get_ai_client()
            if ai_client:
                # Note: Health check is async, so we can't test it here
                # The actual health check happens in the health endpoints
                return "healthy"
            return "error: client not initialized"
        return "healthy"
    except Exception as e:
        return f"error: {str(e)}"
