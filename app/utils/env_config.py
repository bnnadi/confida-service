"""
Environment configuration utilities for production vs development settings.
"""
import os
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

def get_environment_config() -> dict:
    """Get current environment configuration status."""
    settings = get_settings()
    
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug_routes_enabled": settings.ENABLE_DEBUG_ROUTES,
        "security_routes_enabled": settings.ENABLE_SECURITY_ROUTES,
        "admin_routes_enabled": settings.ENABLE_ADMIN_ROUTES,
        "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED,
        "rate_limiting_enabled": settings.RATE_LIMIT_ENABLED,
        "cors_origins_count": len(settings.CORS_ORIGINS),
        "production_ready": _is_production_ready(settings)
    }

def _is_production_ready(settings) -> bool:
    """Check if the application is configured for production."""
    return (
        not settings.ENABLE_DEBUG_ROUTES and
        not settings.ENABLE_SECURITY_ROUTES and
        settings.SECURITY_HEADERS_ENABLED and
        settings.RATE_LIMIT_ENABLED and
        len(settings.CORS_ORIGINS) > 0 and
        "https://" in settings.CORS_ORIGINS[0]  # HTTPS origins
    )

def log_environment_status():
    """Log current environment configuration status."""
    config = get_environment_config()
    
    logger.info("🔧 Environment Configuration:")
    logger.info(f"   Environment: {config['environment']}")
    logger.info(f"   Debug routes: {'✅' if config['debug_routes_enabled'] else '❌'}")
    logger.info(f"   Security routes: {'✅' if config['security_routes_enabled'] else '❌'}")
    logger.info(f"   Admin routes: {'✅' if config['admin_routes_enabled'] else '❌'}")
    logger.info(f"   Security headers: {'✅' if config['security_headers_enabled'] else '❌'}")
    logger.info(f"   Rate limiting: {'✅' if config['rate_limiting_enabled'] else '❌'}")
    logger.info(f"   CORS origins: {config['cors_origins_count']} configured")
    logger.info(f"   Production ready: {'✅' if config['production_ready'] else '❌'}")
    
    if not config['production_ready']:
        logger.warning("⚠️ Application is not configured for production deployment")
        logger.warning("   Consider setting ENABLE_DEBUG_ROUTES=false and ENABLE_SECURITY_ROUTES=false")
