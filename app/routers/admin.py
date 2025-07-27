from fastapi import APIRouter, HTTPException
from app.services.hybrid_ai_service import HybridAIService
from app.config import settings

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# Initialize AI service with error handling
try:
    ai_service = HybridAIService()
except Exception as e:
    print(f"Warning: Could not initialize HybridAIService: {e}")
    ai_service = None

@router.get("/services/status")
async def get_services_status():
    """
    Get detailed status of all AI services.
    """
    try:
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
        if ai_service is None:
            return {"error": "AI service not initialized"}
        
        results = {}
        
        # Test Ollama
        if settings.is_ollama_configured:
            try:
                test_response = ai_service.generate_interview_questions(
                    "Software Engineer", 
                    "We are looking for a software engineer with Python experience."
                )
                results["ollama"] = {"status": "success", "questions_count": len(test_response.questions)}
            except Exception as e:
                results["ollama"] = {"status": "error", "error": str(e)}
        
        # Test OpenAI
        if settings.is_openai_configured:
            try:
                test_response = ai_service.generate_interview_questions(
                    "Software Engineer", 
                    "We are looking for a software engineer with Python experience.",
                    preferred_service="openai"
                )
                results["openai"] = {"status": "success", "questions_count": len(test_response.questions)}
            except Exception as e:
                results["openai"] = {"status": "error", "error": str(e)}
        
        # Test Anthropic
        if settings.is_anthropic_configured:
            try:
                test_response = ai_service.generate_interview_questions(
                    "Software Engineer", 
                    "We are looking for a software engineer with Python experience.",
                    preferred_service="anthropic"
                )
                results["anthropic"] = {"status": "success", "questions_count": len(test_response.questions)}
            except Exception as e:
                results["anthropic"] = {"status": "error", "error": str(e)}
        
        return {"test_results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing services: {str(e)}") 