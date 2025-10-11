from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.schemas import ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse
from app.utils.endpoint_helpers import handle_service_errors

router = APIRouter(prefix="/api/v1", tags=["interview"])

@router.post("/parse-jd", response_model=ParseJDResponse)
@handle_service_errors("parsing job description")
async def parse_job_description(
    ai_service,
    request: ParseJDRequest,
    service: Optional[str] = Query(None, description="Preferred AI service: ollama, openai, or anthropic")
):
    """
    Parse job description and generate relevant interview questions using AI.
    Supports multiple AI services with automatic fallback.
    """
    return ai_service.generate_interview_questions(
        request.role, 
        request.jobDescription, 
        preferred_service=service
    )

@router.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
@handle_service_errors("analyzing answer")
async def analyze_answer(
    ai_service,
    request: AnalyzeAnswerRequest,
    service: Optional[str] = Query(None, description="Preferred AI service: ollama, openai, or anthropic")
):
    """
    Analyze a candidate's answer against the job description using AI.
    Supports multiple AI services with automatic fallback.
    """
    return ai_service.analyze_answer(
        request.jobDescription, 
        request.question, 
        request.answer,
        preferred_service=service
    )

@router.get("/services")
@handle_service_errors("getting service status")
async def get_available_services(ai_service):
    """
    Get status of available AI services.
    """
    return {
        "available_services": ai_service.get_available_services(),
        "service_priority": ai_service.get_service_priority()
    }

@router.get("/models")
@handle_service_errors("listing models")
async def list_models(ai_service):
    """
    List available Ollama models.
    """
    models = ai_service.ollama_service.list_available_models()
    return {"models": models}

@router.post("/models/{model_name}/pull")
@handle_service_errors("pulling model")
async def pull_model(ai_service, model_name: str):
    """
    Pull a model to Ollama.
    """
    success = ai_service.ollama_service.pull_model(model_name)
    if success:
        return {"message": f"Model {model_name} pulled successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}") 