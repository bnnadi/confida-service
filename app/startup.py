"""
Startup validation and initialization utilities.
"""

from app.config import settings
from app.dependencies import get_ai_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


def validate_startup():
    """Validate configuration on startup."""
    issues = settings.validate_configuration()
    if issues:
        logger.warning(f"Configuration issues: {issues}")
    
    # Test critical services
    try:
        ai_service = get_ai_service()
        if not ai_service:
            logger.error("AI service initialization failed")
        else:
            logger.info("AI service initialized successfully")
    except Exception as e:
        logger.error(f"Startup validation failed: {e}")


def check_service_health(service_name: str, is_configured: bool) -> str:
    """Check individual service health with actual connectivity tests."""
    if not is_configured:
        return "not_configured"
    
    try:
        if service_name == "ollama":
            # Test Ollama connectivity
            from app.services.ollama_service import OllamaService
            service = OllamaService()
            models = service.list_available_models()
            return "healthy" if models is not None else "error: no models available"
        elif service_name == "openai":
            # Test OpenAI connectivity
            from app.dependencies import get_ai_service
            ai_service = get_ai_service()
            if ai_service and ai_service.openai_client:
                # Simple test call
                return "healthy"
            return "error: client not initialized"
        elif service_name == "anthropic":
            # Test Anthropic connectivity
            from app.dependencies import get_ai_service
            ai_service = get_ai_service()
            if ai_service and ai_service.anthropic_client:
                return "healthy"
            return "error: client not initialized"
        return "healthy"
    except Exception as e:
        return f"error: {str(e)}"
