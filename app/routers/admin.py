from fastapi import APIRouter, HTTPException
from app.config import settings
from app.utils.service_tester import ServiceTester
from app.utils.endpoint_helpers import handle_service_errors

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/services/status")
@handle_service_errors("getting service status")
async def get_services_status(ai_service):
    """
    Get detailed status of all AI services.
    """
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

@router.post("/services/test")
@handle_service_errors("testing services")
async def test_services(ai_service):
    """
    Test all configured AI services.
    """
    if ai_service is None:
        return {"error": "AI service not initialized"}
    
    tester = ServiceTester(ai_service, settings)
    return {"test_results": tester.test_all_services()} 