from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.schemas import ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse
from app.dependencies import get_ai_service

router = APIRouter(prefix="/api/v1", tags=["interview"])

@router.post("/parse-jd", response_model=ParseJDResponse)
async def parse_job_description(
    request: ParseJDRequest,
    service: Optional[str] = Query(None, description="Preferred AI service: ollama, openai, or anthropic")
):
    """
    Parse job description and generate relevant interview questions using AI.
    Supports multiple AI services with automatic fallback.
    """
    ai_service = get_ai_service()
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        return ai_service.generate_interview_questions(
            request.role, 
            request.jobDescription, 
            preferred_service=service
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing job description: {str(e)}")

@router.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
async def analyze_answer(
    request: AnalyzeAnswerRequest,
    service: Optional[str] = Query(None, description="Preferred AI service: ollama, openai, or anthropic")
):
    """
    Analyze a candidate's answer against the job description using AI.
    Supports multiple AI services with automatic fallback.
    """
    ai_service = get_ai_service()
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        return ai_service.analyze_answer(
            request.jobDescription, 
            request.question, 
            request.answer,
            preferred_service=service
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing answer: {str(e)}")

@router.get("/services")
async def get_available_services():
    """
    Get status of available AI services.
    """
    ai_service = get_ai_service()
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        return {
            "available_services": ai_service.get_available_services(),
            "service_priority": ai_service.get_service_priority()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")

@router.get("/models")
async def list_models():
    """
    List available Ollama models.
    """
    ai_service = get_ai_service()
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        models = ai_service.ollama_service.list_available_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing models: {str(e)}")

@router.post("/models/{model_name}/pull")
async def pull_model(model_name: str):
    """
    Pull a model to Ollama.
    """
    ai_service = get_ai_service()
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")
    
    try:
        success = ai_service.ollama_service.pull_model(model_name)
        if success:
            return {"message": f"Model {model_name} pulled successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error pulling model: {str(e)}") 