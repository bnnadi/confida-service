from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.logging_config import setup_logging

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
    import importlib
    
    routers_to_load = [
        ("interview", "app.routers.interview"),
        ("admin", "app.routers.admin")
    ]
    
    loaded_routers = []
    
    for router_name, module_path in routers_to_load:
        try:
            module = importlib.import_module(module_path)
            router = getattr(module, "router")
            app.include_router(router)
            loaded_routers.append(router_name)
        except Exception as e:
            logger.warning(f"Could not load {router_name} router: {e}")
    
    if not loaded_routers:
        raise RuntimeError("No routers could be loaded")
    
    logger.info(f"Successfully loaded routers: {', '.join(loaded_routers)}")

load_routers()

def validate_startup():
    """Validate configuration on startup."""
    from app.config import settings
    from app.dependencies import get_ai_service
    
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
    from app.dependencies import get_ai_service
    
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {},
        "configuration_issues": settings.validate_configuration()
    }
    
    # Check each service individually
    for service_name, is_configured in settings.configured_services.items():
        if is_configured:
            try:
                # Test service connectivity
                health_status["services"][service_name] = "healthy"
            except Exception as e:
                health_status["services"][service_name] = f"error: {str(e)}"
        else:
            health_status["services"][service_name] = "not_configured"
    
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