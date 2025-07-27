from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="JD-Aware AI Interview Coach",
    description="A FastAPI backend for AI-powered interview coaching with hybrid AI services",
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

# Include routers with error handling
try:
    from app.routers import interview, admin
    app.include_router(interview.router)
    app.include_router(admin.router)
except Exception as e:
    print(f"Warning: Could not load all routers: {e}")
    # Try to load just the interview router
    try:
        from app.routers import interview
        app.include_router(interview.router)
    except Exception as e2:
        print(f"Error: Could not load interview router: {e2}")

@app.get("/")
async def root():
    return {
        "message": "JD-Aware AI Interview Coach API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": "Hybrid AI Services (Ollama + OpenAI + Anthropic)"
    }

@app.get("/health")
async def health_check():
    """Enhanced health check that verifies all dependencies."""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "services": {}
    }
    
    # Check Ollama connection
    try:
        import requests
        import os
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            health_status["services"]["ollama"] = "healthy"
        else:
            health_status["services"]["ollama"] = "unhealthy"
    except Exception as e:
        health_status["services"]["ollama"] = f"error: {str(e)}"
    
    # Check if any critical services are unhealthy
    if any(status != "healthy" for status in health_status["services"].values()):
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes-style deployments."""
    return {"ready": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 