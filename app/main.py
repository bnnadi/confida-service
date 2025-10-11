from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# CORS middleware configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://frontend:80",
        "http://frontend:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add file upload middleware
app = create_file_upload_middleware_stack(app)

# Include routers with simplified error handling
def load_routers():
    """Load routers with simplified error handling."""
    from app.routers import interview, admin, sessions, auth, files, speech

    routers = [
        ("auth", auth.router),
        ("interview", interview.router),
        ("admin", admin.router),
        ("sessions", sessions.router),
        ("files", files.router),
        ("speech", speech.router)
    ]
    
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

validate_startup()

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
    
    health_service = HealthService()
    return await health_service.get_comprehensive_health()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 