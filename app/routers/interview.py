from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.models.schemas import ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse
from app.utils.endpoint_helpers import handle_service_errors
from app.utils.validators import InputValidator, create_service_query_param
from app.utils.database_operation_handler import DatabaseOperationHandler
from app.database.connection import get_db
from app.database.async_connection import get_async_db
from app.services.session_service import SessionService
from app.services.async_session_service import AsyncSessionService
from app.middleware.auth_middleware import get_current_user_required
from app.dependencies import get_ai_service, get_async_ai_service, get_ai_service_dependency
from app.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["interview"])

@router.post("/parse-jd", response_model=ParseJDResponse)
async def parse_job_description(
    request: ParseJDRequest,
    service: Optional[str] = create_service_query_param(),
    current_user: dict = Depends(get_current_user_required)
):
    """Parse job description and generate relevant interview questions using AI."""
    validated_service = InputValidator.validate_service(service)
    
    # Use unified database operation handler
    handler = DatabaseOperationHandler()
    return await handler.handle_operation(
        operation_type="parse_jd",
        request=request,
        validated_service=validated_service,
        current_user=current_user
    )

@router.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
async def analyze_answer(
    request: AnalyzeAnswerRequest,
    service: Optional[str] = create_service_query_param(),
    question_id: int = Query(..., description="Question ID to store the answer"),
    current_user: dict = Depends(get_current_user_required)
):
    """Analyze user's answer and provide feedback using AI."""
    validated_service = InputValidator.validate_service(service)
    
    # Use unified database operation handler
    handler = DatabaseOperationHandler()
    return await handler.handle_operation(
        operation_type="analyze_answer",
        request=request,
        validated_service=validated_service,
        current_user=current_user,
        question_id=question_id
    )

@router.get("/services")
async def get_available_services():
    """
    Get status of available AI services.
    """
    handler = DatabaseOperationHandler()
    return await handler.handle_operation(operation_type="get_services")

@router.get("/models")
async def list_models():
    """
    List available Ollama models.
    """
    handler = DatabaseOperationHandler()
    return await handler.handle_operation(operation_type="list_models")

@router.post("/models/{model_name}/pull")
async def pull_model(model_name: str):
    """
    Pull a model to Ollama.
    """
    handler = DatabaseOperationHandler()
    return await handler.handle_operation(operation_type="pull_model", model_name=model_name)


# Note: Database operation handlers have been moved to DatabaseOperationHandler class
# for better organization and reusability

# Legacy handlers (kept for backward compatibility)
async def _handle_database_operation(operation_type: str, **kwargs):
    """Unified handler for database operations (async/sync)."""
    settings = get_settings()
    
    # Use strategy pattern for operation handling
    operation_handlers = {
        "parse_jd": _handle_parse_jd_operation,
        "analyze_answer": _handle_analyze_answer_operation
    }
    
    handler = operation_handlers.get(operation_type)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown operation type: {operation_type}")
    
    if settings.ASYNC_DATABASE_ENABLED:
        return await handler(async=True, **kwargs)
    else:
        return await handler(async=False, **kwargs)

async def _handle_parse_jd_operation(async: bool, **kwargs):
    """Unified parse JD handler for both async and sync."""
    if async:
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            return await _handle_async_parse_jd(ai_service, db, **kwargs)
    else:
        db = next(get_db())
        ai_service = get_ai_service(db)
        if not ai_service:
            raise HTTPException(status_code=500, detail="AI service not available")
        return await _handle_sync_parse_jd(ai_service, db, **kwargs)

async def _handle_analyze_answer_operation(async: bool, **kwargs):
    """Unified analyze answer handler for both async and sync."""
    if async:
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            return await _handle_async_analyze_answer(ai_service, db, **kwargs)
    else:
        db = next(get_db())
        ai_service = get_ai_service(db)
        if not ai_service:
            raise HTTPException(status_code=500, detail="AI service not available")
        return await _handle_sync_analyze_answer(ai_service, db, **kwargs)


async def _handle_async_parse_jd(ai_service, db, request, validated_service, current_user):
    """Handle async parse JD operation with atomic transaction management."""
    from app.utils.logger import get_logger
    from app.exceptions import AIServiceError
    
    logger = get_logger(__name__)
    
    try:
        # Generate questions using AI
        response = await ai_service.generate_interview_questions(
            request.role, 
            request.jobDescription, 
            count=10,
            difficulty="medium"
        )
        
        # Create session and store questions in database atomically
        session_service = AsyncSessionService(db)
        session, session_questions = await session_service.create_session_with_questions_atomic(
            user_id=current_user["id"],
            role=request.role,
            job_description=request.jobDescription,
            questions=response["questions"]
        )
        
        logger.info(f"Successfully created session {session.id} with {len(session_questions)} questions")
        
        return ParseJDResponse(
            questions=response["questions"],
            role=request.role,
            jobDescription=request.jobDescription,
            service_used=validated_service,
            question_bank_count=response.get("bank_questions_count", 0),
            ai_generated_count=response.get("ai_questions_count", 0)
        )
        
    except Exception as e:
        logger.error(f"Failed to create session with questions: {e}")
        raise AIServiceError(f"Failed to create interview session: {e}")


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


async def _handle_async_analyze_answer(ai_service, db, request, validated_service, current_user, question_id):
    """Handle async analyze answer operation."""
    # Analyze answer using AI
    response = await ai_service.analyze_answer(
        request.jobDescription, 
        request.answer,
        role="",  # TODO: Get role from question context
        job_description=request.jobDescription
    )
    
    # Store answer and analysis in database
    session_service = AsyncSessionService(db)
    
    # Verify question exists and belongs to user using generic validation
    question = await _validate_question_access(db, question_id, current_user["id"])
    
    # Store answer with analysis
    await session_service.add_answer(
        question_id=question_id,
        answer_text=request.answer,
        analysis_result=response,
        score={"clarity": response.get("score", {}).get("clarity", 0), 
              "confidence": response.get("score", {}).get("confidence", 0)}
    )
    
    return AnalyzeAnswerResponse(
        analysis=response.get("analysis", ""),
        score=response.get("score", {}),
        suggestions=response.get("suggestions", []),
        jobDescription=request.jobDescription,
        answer=request.answer,
        service_used=validated_service
    )


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
    question = await _validate_question_access(db, question_id, current_user["id"])
    
    # Store answer with analysis
    session_service.add_answer(
        question_id=question_id,
        answer_text=request.answer,
        analysis_result=response.dict(),
        score={"clarity": response.score.clarity, "confidence": response.score.confidence}
    )
    
    return response


async def _validate_question_access(db, question_id: int, user_id: str):
    """Generic question validation with consistent error handling."""
    from app.database.models import Question, InterviewSession
    from sqlalchemy import select
    
    if hasattr(db, 'execute'):  # Async session
        result = await db.execute(
            select(Question)
            .join(InterviewSession)
            .where(
                Question.id == question_id,
                InterviewSession.user_id == user_id
            )
        )
        question = result.scalar_one_or_none()
    else:  # Sync session
        question = db.query(Question).join(InterviewSession).filter(
            Question.id == question_id,
            InterviewSession.user_id == user_id
        ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return question 