from fastapi import APIRouter, HTTPException
from app.config import settings
from app.utils.service_tester import ServiceTester
from app.dependencies import get_ai_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/services/status")
async def get_services_status():
    """
    Get detailed status of all AI services.
    """
    try:
        ai_service = get_ai_service()
        if ai_service is None:
            return {
                "error": "AI service not initialized",
                "available_services": {"ollama": False, "openai": False, "anthropic": False},
                "service_priority": ["ollama"]
            }
        
        return {
            "available_services": ai_service.get_available_services(),
            "service_priority": ai_service.get_service_priority(),
            "configuration": {
                "ollama_url": settings.OLLAMA_BASE_URL,
                "ollama_model": settings.OLLAMA_MODEL,
                "openai_configured": settings.is_openai_configured,
                "openai_model": settings.OPENAI_MODEL,
                "anthropic_configured": settings.is_anthropic_configured,
                "anthropic_model": settings.ANTHROPIC_MODEL
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")

@router.post("/services/test")
async def test_services():
    """
    Test all configured AI services.
    """
    try:
        ai_service = get_ai_service()
        if ai_service is None:
            return {"error": "AI service not initialized"}
        
        tester = ServiceTester(ai_service, settings)
        return {"test_results": tester.test_all_services()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing services: {str(e)}") 