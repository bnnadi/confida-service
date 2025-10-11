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

# Initialize rate limiter based on configuration
def get_rate_limiter():
    """Get rate limiter instance based on configuration."""
    if not settings.RATE_LIMIT_ENABLED:
        return None
    
    if settings.RATE_LIMIT_BACKEND == "redis":
        return RedisRateLimiter(
            redis_url=settings.RATE_LIMIT_REDIS_URL,
            max_requests=settings.RATE_LIMIT_DEFAULT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_DEFAULT_WINDOW
        )
    else:
        return RateLimiter(
            max_requests=settings.RATE_LIMIT_DEFAULT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_DEFAULT_WINDOW
        )

# Global rate limiter instance
rate_limiter = get_rate_limiter()
logger.info("Rate limiter initialized: %s", type(rate_limiter) if rate_limiter else "None")

# Store rate limiters per endpoint to maintain state
endpoint_limiters = {}

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

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Rate limiting middleware with per-endpoint configuration."""
    if not rate_limiter:
        return await call_next(request)
    
    try:
        # Get client identifier (IP address or user ID if available)
        client_id = request.client.host if request.client else "unknown"
        
        # Get rate limit configuration for this endpoint
        endpoint = request.url.path
        rate_limit_config = settings.get_rate_limit_for_endpoint(endpoint)
        
        # Rate limiting check for client on endpoint
        
        # Get or create endpoint-specific rate limiter
        endpoint_key = f"{endpoint}_{rate_limit_config['requests']}_{rate_limit_config['window']}"
        
        if endpoint_key not in endpoint_limiters:
            if isinstance(rate_limiter, RateLimiter):
                # Create a new rate limiter instance for this endpoint
                endpoint_limiters[endpoint_key] = RateLimiter(
                    max_requests=rate_limit_config["requests"],
                    window_seconds=rate_limit_config["window"]
                )
            else:
                # For Redis rate limiter, create a new instance
                endpoint_limiters[endpoint_key] = RedisRateLimiter(
                    redis_url=settings.RATE_LIMIT_REDIS_URL,
                    max_requests=rate_limit_config["requests"],
                    window_seconds=rate_limit_config["window"]
                )
        
        endpoint_limiter = endpoint_limiters[endpoint_key]
        endpoint_limiter.check_rate_limit(client_id)
            
    except RateLimitExceededError:
        logger.warning("Rate limit exceeded for client %s on endpoint %s", client_id, endpoint)
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. Try again in {rate_limit_config['window']} seconds."
        )
    except Exception as e:
        logger.error("Rate limiting error: %s", e)
        # Don't block requests on rate limiting errors
    
    return await call_next(request)

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