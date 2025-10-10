from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging
from app.middleware.logging_middleware import log_requests
from app.middleware.rate_limiter import rate_limiter
from app.exceptions import RateLimitExceededError

# Setup logging
logger = setup_logging()

app = FastAPI(
    title="InterviewIQ API",
    description="AI-powered interview coaching with intelligent feedback and analysis",
    version="1.0.0"
)

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

# Include routers with simplified error handling
def load_routers():
    """Load routers with simplified error handling."""
    from app.routers import interview, admin, speech
    
    routers = [
        ("interview", interview.router),
        ("admin", admin.router),
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
    try:
        rate_limiter.check_rate_limit()
    except RateLimitExceededError:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
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
    """Enhanced health check that verifies all dependencies."""
    from app.config import settings
    
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {},
        "configuration_issues": settings.validate_configuration()
    }
    
    # Check each service individually
    for service_name, is_configured in settings.configured_services.items():
        health_status["services"][service_name] = check_service_health(service_name, is_configured)
    
    # Determine overall status
    if any("error" in status for status in health_status["services"].values()):
        health_status["status"] = "degraded"
    elif health_status["configuration_issues"]:
        health_status["status"] = "warning"
    
    return health_status

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes-style deployments."""
    return {"ready": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 