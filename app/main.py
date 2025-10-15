from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from app.logging_config import setup_logging
from app.middleware.logging_middleware import log_requests
from app.middleware.rate_limiter import RateLimiter
from app.middleware.redis_rate_limiter import RedisRateLimiter
from app.middleware.file_upload_middleware import create_file_upload_middleware_stack
from app.exceptions import RateLimitExceededError
from app.config import settings

# Setup logging
logger = setup_logging()

app = FastAPI(
    title="InterviewIQ API",
    description="AI-powered interview coaching with intelligent feedback and analysis",
    version="1.0.0"
)

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

# Add security headers middleware
from app.middleware.security_middleware import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# Include routers with simplified error handling
def load_routers():
    """Load routers with simplified error handling."""
    from app.routers import interview, sessions, auth, files, speech, vector_search, cache
    
    # Core routers (always enabled)
    routers = [
        ("auth", auth.router),
        ("interview", interview.router),
        ("sessions", sessions.router),
        ("files", files.router),
        ("speech", speech.router),
        ("vector_search", vector_search.router),
        ("cache", cache.router)
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
from app.database.connection import init_db, check_db_connection
from app.database.async_connection import init_async_db, async_db_manager

# Initialize database
init_db()

# Check database connection
if not check_db_connection():
    logger.error("❌ Database connection failed")
    raise RuntimeError("Database connection failed")

# Async database will be initialized in startup event handler

validate_startup()
log_environment_status()

# Startup and shutdown event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize async database on startup."""
    if settings.ASYNC_DATABASE_ENABLED:
        try:
            await init_async_db()
            logger.info("✅ Async database initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize async database: {e}")
            raise

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
        "message": "InterviewIQ API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": "AI-powered interview coaching with hybrid AI services"
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check that verifies all dependencies with actual connectivity tests."""
    from app.services.health_service import HealthService
    from app.database.async_connection import get_db_health
    
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
        from app.services.vector_service import vector_service
        
        health = await vector_service.health_check()
        stats = await vector_service.get_collection_stats()
        
        return {
            "health_status": health,
            "collection_stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting vector monitoring data: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 