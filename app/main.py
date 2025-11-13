from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from datetime import datetime
from app.utils.logging_config import setup_logging
from app.utils.logger import get_logger
from app.middleware.logging_middleware import log_requests
from app.middleware.rate_limiter import RateLimiter
from app.middleware.redis_rate_limiter import RedisRateLimiter
from app.middleware.file_upload_middleware import create_file_upload_middleware_stack
from app.exceptions import RateLimitExceededError
from app.config import settings

# Setup logging configuration
setup_logging()
# Get logger instance
logger = get_logger(__name__)

# Set custom OpenAPI schema using simplified documentation builder
from app.utils.api_documentation import APIDocumentationBuilder

app = FastAPI(
    title="Confida API",
    description="""
    ## 🎯 Confida API Documentation
    
    A comprehensive API for AI-powered interview coaching and question generation.
    
    ### ✨ Key Features
    - **AI-Powered Question Generation**: Generate interview questions based on job descriptions
    - **Answer Analysis**: Get detailed feedback on interview answers
    - **Session Management**: Track interview sessions and progress
    - **File Upload Support**: Upload job descriptions and documents
    - **Real-time Analytics**: Monitor performance and improvement trends
    - **Vector Search**: Semantic search through question banks
    
    ### 🚀 Getting Started
    1. **Authentication**: Use the `/auth` endpoints to get API tokens
    2. **Parse Job Description**: Use `/parse-jd` to generate questions
    3. **Analyze Answers**: Use `/analyze-answer` for feedback
    4. **View Analytics**: Use `/analytics` endpoints for insights
    
    ### 📊 API Status
    - **Version**: 1.0.0
    - **Status**: Production Ready
    - **Rate Limits**: 100 requests/minute per user
    - **Authentication**: Bearer Token
    
    ### 🔗 Useful Links
    - [GitHub Repository](https://github.com/your-org/confida)
    - [Support Documentation](https://docs.confida.com)
    - [Status Page](https://status.confida.com)
    """,
    version="1.0.0",
    contact={
        "name": "Confida Support",
        "url": "https://docs.confida.com",
        "email": "support@confida.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "https://api.confida.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.confida.com",
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
)

def create_custom_openapi():
    """Create custom OpenAPI schema with enhanced documentation."""
    builder = APIDocumentationBuilder(app)
    return builder.build_openapi_schema()

app.openapi = create_custom_openapi

# Rate limiting is now handled by the enhanced middleware

# Enhanced CORS middleware configuration for HTTPS
from app.config import get_settings
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.cors_config["allow_credentials"],
    allow_methods=settings.cors_config["allow_methods"],
    allow_headers=settings.cors_config["allow_headers"],
    expose_headers=settings.cors_config["expose_headers"],
    max_age=settings.cors_config["max_age"]
)

# Add file upload middleware
app = create_file_upload_middleware_stack(app)

# Add monitoring middleware (if enabled)
if settings.MONITORING_ENABLED:
    from app.middleware.monitoring_middleware import MonitoringMiddleware
    app.add_middleware(MonitoringMiddleware)

# Add security headers middleware
from app.middleware.security_middleware import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# Include routers with simplified error handling
def load_routers():
    """Load routers with simplified error handling."""
    from app.routers import interview, sessions, auth, files, speech, cache, health, analytics, scoring, dashboard, websocket
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    
    # Core routers (always enabled)
    routers = [
        ("auth", auth.router),
        ("interview", interview.router),
        ("sessions", sessions.router),
        ("files", files.router),
        ("speech", speech.router),
        # Note: vector_search router removed - services deleted
        ("cache", cache.router),
        ("health", health.router),
        ("analytics", analytics.router),
        ("scoring", scoring.router),
        ("dashboard", dashboard.router),
        ("websocket", websocket.router)
    ]
    
    # Conditional routers based on environment variables
    if settings.ENABLE_ADMIN_ROUTES:
        from app.routers import admin
        routers.append(("admin", admin.router))
        logger.info("✅ Admin routes enabled")
    else:
        logger.info("⚠️ Admin routes disabled (ENABLE_ADMIN_ROUTES=false)")
    
    if settings.ENABLE_SECURITY_ROUTES:
        from app.routers import security
        routers.append(("security", security.router))
        logger.info("✅ Security routes enabled")
    else:
        logger.info("⚠️ Security routes disabled (ENABLE_SECURITY_ROUTES=false)")
    
    if settings.ENABLE_DEBUG_ROUTES:
        # Add any debug-specific routers here in the future
        logger.info("✅ Debug routes enabled")
    else:
        logger.info("⚠️ Debug routes disabled (ENABLE_DEBUG_ROUTES=false)")
    
    loaded_routers = []
    for router_name, router in routers:
        try:
            app.include_router(router)
            loaded_routers.append(router_name)
            logger.info(f"✅ Loaded {router_name} router")
        except Exception as e:
            logger.warning(f"⚠️ Could not load {router_name} router: {e}")
    
    if not loaded_routers:
        raise RuntimeError("No routers could be loaded")
    
    logger.info(f"Successfully loaded routers: {', '.join(loaded_routers)}")

load_routers()

# Add middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    return await log_requests(request, call_next)

# Enhanced rate limiting middleware
from app.middleware.rate_limiting_middleware import RateLimitingMiddleware

# Add enhanced rate limiting middleware
app.add_middleware(RateLimitingMiddleware)

from app.startup import validate_startup, check_service_health
from app.utils.env_config import log_environment_status
from app.services.database_service import init_database, init_async_database, init_async_db, get_db_health, database_service
from app.database.async_connection import async_db_manager

# Initialize database
init_database()

# Check database connection
try:
    health_check = database_service.health_check_sync()
    if health_check["status"] != "healthy":
        logger.error("❌ Database connection failed")
        raise RuntimeError("Database connection failed")
except Exception as e:
    logger.error(f"❌ Database connection failed: {e}")
    raise RuntimeError("Database connection failed")

# Async database will be initialized in startup event handler

validate_startup()
log_environment_status()

# Startup and shutdown event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize async database and monitoring on startup."""
    if settings.ASYNC_DATABASE_ENABLED:
        try:
            await init_async_db()
            logger.info("✅ Async database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize async database: {e}")
            raise
    
    # Start monitoring server if enabled
    if settings.MONITORING_ENABLED:
        try:
            from app.utils.metrics import start_metrics_server
            start_metrics_server()
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring server: {e}")
            # Don't raise - monitoring is not critical for startup

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup async database connections on shutdown."""
    if settings.ASYNC_DATABASE_ENABLED:
        try:
            # Stop monitoring
            from app.services.async_database_monitor import async_db_monitor
            await async_db_monitor.stop_monitoring()
            
            # Close database connections
            await async_db_manager.close()
            logger.info("✅ Async database connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing async database connections: {e}")

@app.get("/")
async def root():
    return {
        "message": "Confida API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": "AI-powered interview coaching with hybrid AI services"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check that verifies all dependencies with actual connectivity tests."""
    from app.services.health_service import HealthService
    # Use unified database service for health checks
    
    health_service = HealthService()
    health_data = await health_service.get_comprehensive_health()
    
    # Add async database health if enabled
    if settings.ASYNC_DATABASE_ENABLED:
        try:
            async_db_health = await get_db_health()
            health_data["async_database"] = async_db_health
            
            # Add detailed monitoring data
            from app.services.async_database_monitor import async_db_monitor
            monitoring_data = await async_db_monitor.get_health_summary()
            health_data["async_database"]["monitoring"] = monitoring_data
            
        except Exception as e:
            health_data["async_database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Add vector database health
    try:
        from app.services.semantic_search_service import semantic_search_service
        vector_health = await semantic_search_service.health_check()
        health_data["vector_database"] = vector_health
    except Exception as e:
        health_data["vector_database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    return health_data

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes-style deployments."""
    from app.services.health_service import HealthService
    
    health_service = HealthService()
    db_health = await health_service.check_database_health()
    
    # Service is ready if database is healthy
    is_ready = db_health.get("status") == "healthy"
    
    return {
        "ready": is_ready,
        "database": db_health.get("status", "unknown"),
        "timestamp": db_health.get("details", {}).get("timestamp")
    }

@app.get("/monitoring/database")
async def database_monitoring():
    """Get detailed database monitoring information."""
    if not settings.ASYNC_DATABASE_ENABLED:
        return {"error": "Async database monitoring is not enabled"}
    
    try:
        from app.services.async_database_monitor import async_db_monitor
        
        return {
            "health_status": await async_db_monitor.get_health_status(),
            "connection_pool_status": await async_db_monitor.get_connection_pool_status(),
            "performance_metrics": await async_db_monitor.get_performance_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting database monitoring data: {e}")
        return {"error": str(e)}

@app.get("/monitoring/vector")
async def vector_monitoring():
    """Get detailed vector database monitoring information."""
    try:
        from app.services.unified_vector_service import unified_vector_service
        
        health = await unified_vector_service.health_check()
        stats = await unified_vector_service.get_collection_stats()
        
        return {
            "health_status": health,
            "collection_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting vector monitoring data: {e}")
        return {"error": str(e)}

# Add documentation guides endpoint
@app.get("/docs/guides", tags=["Documentation"])
async def get_usage_guides():
    """Get comprehensive usage guides and code examples."""
    from app.utils.api_documentation import get_usage_guides
    return get_usage_guides()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 