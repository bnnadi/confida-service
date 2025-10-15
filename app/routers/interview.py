from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.models.schemas import ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse
from app.utils.endpoint_helpers import handle_service_errors
from app.utils.validators import InputValidator, create_service_query_param
from app.database.connection import get_db
from app.services.session_service import SessionService
from app.middleware.auth_middleware import get_current_user_required
from app.dependencies import get_ai_service, get_ai_service_dependency

router = APIRouter(prefix="/api/v1", tags=["interview"])

@router.post("/parse-jd", response_model=ParseJDResponse)
async def parse_job_description(
    request: ParseJDRequest,
    service: Optional[str] = create_service_query_param(),
    current_user: dict = Depends(get_current_user_required)
):
    """Parse job description and generate relevant interview questions using AI."""
    validated_service = InputValidator.validate_service(service)
    
    # Use sync database operations
    db = next(get_db())
    ai_service = get_ai_service(db)
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not available")
    
    return await _handle_sync_parse_jd(ai_service, db, request, validated_service, current_user)

@router.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
async def analyze_answer(
    request: AnalyzeAnswerRequest,
    service: Optional[str] = create_service_query_param(),
    question_id: int = Query(..., description="Question ID to store the answer"),
    current_user: dict = Depends(get_current_user_required)
):
    """Analyze user's answer and provide feedback using AI."""
    validated_service = InputValidator.validate_service(service)
    
    # Use sync database operations
    db = next(get_db())
    ai_service = get_ai_service(db)
    if not ai_service:
        raise HTTPException(status_code=500, detail="AI service not available")
    
    return await _handle_sync_analyze_answer(ai_service, db, request, validated_service, current_user, question_id)

@router.get("/services")
async def get_available_services():
    """
    Get status of available AI services.
    """
    settings = get_settings()
    
    if settings.ASYNC_DATABASE_ENABLED:
        # Use async database operations
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            
            services = await ai_service.get_available_services()
            return services
    else:
        # Use synchronous database operations
        db = next(get_db())
        ai_service = get_ai_service(db)
        if not ai_service:
            raise HTTPException(status_code=500, detail="AI service not available")
        
        return {
            "available_services": ai_service.get_available_services(),
            "service_priority": ai_service.get_service_priority(),
            "question_bank_stats": ai_service.get_question_bank_stats()
        }

@router.get("/models")
async def list_models():
    """
    List available Ollama models.
    """
    settings = get_settings()
    
    if settings.ASYNC_DATABASE_ENABLED:
        # Use async database operations
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            
            models = await ai_service.list_models("ollama")
            return {"models": models}
    else:
        # Use synchronous database operations
        db = next(get_db())
        ai_service = get_ai_service(db)
        if not ai_service:
            raise HTTPException(status_code=500, detail="AI service not available")
        
        models = ai_service.ollama_service.list_available_models()
        return {"models": models}

@router.post("/models/{model_name}/pull")
async def pull_model(model_name: str):
    """
    Pull a model to Ollama.
    """
    settings = get_settings()
    
    if settings.ASYNC_DATABASE_ENABLED:
        # Use async database operations
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            
            result = await ai_service.pull_model("ollama", model_name)
            if result.get("success"):
                return {"message": f"Model {model_name} pulled successfully"}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}")
    else:
        # Use synchronous database operations
        db = next(get_db())
        ai_service = get_ai_service(db)
        if not ai_service:
            raise HTTPException(status_code=500, detail="AI service not available")
        
        success = ai_service.ollama_service.pull_model(model_name)
        if success:
            return {"message": f"Model {model_name} pulled successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}")


# Sync Database Operation Handlers
async def _handle_sync_parse_jd(ai_service, db, request, validated_service, current_user):
    """Handle sync parse JD operation with atomic transaction management."""
    from app.utils.logger import get_logger
    from app.exceptions import AIServiceError
    
    logger = get_logger(__name__)
    
    try:
        # Generate questions using AI
        response = ai_service.generate_interview_questions(
            request.role, 
            request.jobDescription, 
            preferred_service=validated_service
        )
        
        # Create session and store questions in database atomically
        session_service = SessionService(db)
        session, questions = session_service.create_session_with_questions_atomic(
            user_id=current_user["id"],
            role=request.role,
            job_description=request.jobDescription,
            questions=response.questions
        )
        
        logger.info(f"Successfully created session {session.id} with {len(questions)} questions")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to create session with questions: {e}")
        raise AIServiceError(f"Failed to create interview session: {e}")


async def _handle_sync_analyze_answer(ai_service, db, request, validated_service, current_user, question_id):
    """Handle sync analyze answer operation."""
    # Analyze answer using AI
    response = ai_service.analyze_answer(
        request.jobDescription, 
        request.answer,
        preferred_service=validated_service
    )
    
    # Store answer and analysis in database
    session_service = SessionService(db)
    
    # Verify question exists and belongs to user using generic validation
    question = _validate_question_access(db, question_id, current_user["id"])
    
    # Store answer with analysis
    session_service.add_answer(
        question_id=question_id,
        answer_text=request.answer,
        analysis_result=response.dict(),
        score={"clarity": response.score.clarity, "confidence": response.score.confidence}
    )
    
    return response


def _validate_question_access(db, question_id: int, user_id: str):
    """Sync question validation with consistent error handling."""
    from app.database.models import Question, InterviewSession
    
    question = db.query(Question).join(InterviewSession).filter(
        Question.id == question_id,
        InterviewSession.user_id == user_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return question 