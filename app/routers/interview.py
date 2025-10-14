from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.models.schemas import ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse
from app.utils.endpoint_helpers import handle_service_errors
from app.utils.validators import InputValidator, create_service_query_param
from app.database.connection import get_db
from app.services.session_service import SessionService
from app.middleware.auth_middleware import get_current_user_required
from app.dependencies import get_ai_service

router = APIRouter(prefix="/api/v1", tags=["interview"])

@router.post("/parse-jd", response_model=ParseJDResponse)
async def parse_job_description(
    request: ParseJDRequest,
    ai_service=Depends(get_ai_service),
    service: Optional[str] = create_service_query_param(),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Parse job description and generate relevant interview questions using AI.
    Supports multiple AI services with automatic fallback.
    Creates a new interview session and stores the questions in the database.
    """
    # Validate service parameter
    validated_service = InputValidator.validate_service(service)
    
    # Generate questions using AI
    response = ai_service.generate_interview_questions(
        request.role, 
        request.jobDescription, 
        preferred_service=validated_service
    )
    
    # Create session and store questions in database
    session_service = SessionService(db)
    session = session_service.create_session(
        user_id=current_user["id"],
        role=request.role,
        job_description=request.jobDescription
    )
    
    # Add questions to the session
    session_service.add_questions_to_session(session.id, response.questions)
    
    return response

@router.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
async def analyze_answer(
    request: AnalyzeAnswerRequest,
    ai_service=Depends(get_ai_service),
    service: Optional[str] = create_service_query_param(),
    question_id: int = Query(..., description="Question ID to store the answer"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Analyze a candidate's answer against the job description using AI.
    Supports multiple AI services with automatic fallback.
    Stores the answer and analysis in the database.
    """
    # Validate input parameters
    validated_service = InputValidator.validate_service(service)
    validated_question_id = InputValidator.validate_question_id(question_id)
    
    # Analyze answer using AI
    response = ai_service.analyze_answer(
        request.jobDescription, 
        request.answer,
        preferred_service=validated_service
    )
    
    # Store answer and analysis in database
    session_service = SessionService(db)
    
    # Verify question exists and belongs to user
    from app.database.models import Question, InterviewSession
    question = db.query(Question).join(InterviewSession).filter(
        Question.id == validated_question_id,
        InterviewSession.user_id == current_user["id"]
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Store answer with analysis
    session_service.add_answer(
        question_id=validated_question_id,
        answer_text=request.answer,
        analysis_result=response.dict(),
        score={"clarity": response.score.clarity, "confidence": response.score.confidence}
    )
    
    return response

@router.get("/services")
async def get_available_services(ai_service=Depends(get_ai_service)):
    """
    Get status of available AI services.
    """
    return {
        "available_services": ai_service.get_available_services(),
        "service_priority": ai_service.get_service_priority()
    }

@router.get("/models")
async def list_models(ai_service=Depends(get_ai_service)):
    """
    List available Ollama models.
    """
    models = ai_service.ollama_service.list_available_models()
    return {"models": models}

@router.post("/models/{model_name}/pull")
async def pull_model(model_name: str, ai_service=Depends(get_ai_service)):
    """
    Pull a model to Ollama.
    """
    success = ai_service.ollama_service.pull_model(model_name)
    if success:
        return {"message": f"Model {model_name} pulled successfully"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}") 