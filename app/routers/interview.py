from fastapi import APIRouter, HTTPException, Query, Depends
# SQLAlchemy imports removed as they were unused
from typing import Optional
from app.models.schemas import ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse
# handle_service_errors import removed as it was unused
from app.utils.validators import InputValidator, create_service_query_param
from app.utils.database_operation_handler import DatabaseOperationHandler
from app.database.connection import get_db
from app.database.async_connection import get_async_db
from app.services.unified_session_service import UnifiedSessionService
from app.middleware.auth_middleware import get_current_user_required
from app.dependencies import get_ai_service, get_async_ai_service
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
        return await handler(is_async=True, **kwargs)
    else:
        return await handler(is_async=False, **kwargs)

async def _handle_parse_jd_operation(is_async: bool, **kwargs):
    """Unified parse JD handler for both async and sync."""
    if is_async:
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            if not ai_service:
                raise HTTPException(status_code=500, detail="AI service not available")
            return await _handle_parse_jd_unified(ai_service, db, **kwargs)
    else:
        db = next(get_db())
        ai_service = get_ai_service(db)
        if not ai_service:
            raise HTTPException(status_code=500, detail="AI service not available")
        return await _handle_parse_jd_unified(ai_service, db, **kwargs)

async def _handle_analyze_answer_operation(is_async: bool, **kwargs):
    """Unified analyze answer handler for both async and sync."""
    if is_async:
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


async def _handle_parse_jd_unified(ai_service, db, request, validated_service, current_user):
    """Unified handler for parse JD operation (works for both async and sync)."""
    from app.utils.logger import get_logger
    from app.exceptions import AIServiceError
    from app.services.question_service import QuestionService
    
    logger = get_logger(__name__)
    
    try:
        # Use intelligent question service
        question_service = QuestionService(db)
        user_context = {
            'user_id': str(current_user["id"]),
            'previous_questions': [],  # TODO: Get from user history
            'preferred_difficulty': None,  # TODO: Get from user preferences
            'weak_areas': [],  # TODO: Get from user analytics
            'strong_areas': []  # TODO: Get from user analytics
        }
        
        questions = question_service.generate_questions(
            role=request.role,
            job_description=request.jobDescription,
            count=10,
            user_context=user_context
        )
        
        # Create session and store questions in database atomically
        session_service = UnifiedSessionService(db)
        session, session_questions = await session_service.create_session_with_questions_atomic(
            user_id=current_user["id"],
            role=request.role,
            job_description=request.jobDescription,
            questions=[q["text"] for q in questions]
        )
        
        logger.info(f"Successfully created session {session.id} with {len(session_questions)} questions")
        
        # Count database vs AI questions
        db_count = sum(1 for q in questions if q["source"] == "database")
        ai_count = sum(1 for q in questions if q["source"] != "database")
        
        return ParseJDResponse(
            questions=[q["text"] for q in questions],
            role=request.role,
            jobDescription=request.jobDescription,
            service_used=validated_service,
            question_bank_count=db_count,
            ai_generated_count=ai_count
        )
        
    except Exception as e:
        logger.error(f"Failed to create session with questions: {e}")
        raise AIServiceError(f"Failed to create interview session: {e}")


async def _handle_async_analyze_answer(ai_service, db, request, validated_service, current_user, question_id):
    """Handle async analyze answer operation."""
    from app.routers.analysis_helpers import perform_analysis_with_fallback
    
    # Verify question exists and belongs to user using generic validation
    question = await _validate_question_access(db, question_id, current_user["id"])
    
    # Get question text and role for multi-agent analysis
    question_text = question.question_text if hasattr(question, 'question_text') else "Interview question"
    role = getattr(question, 'role', '') if hasattr(question, 'role') else ""
    
    # Perform analysis with fallback
    response = await perform_analysis_with_fallback(ai_service, request, question_text, role)
    
    # Store answer and analysis in database
    session_service = AsyncSessionService(db)
    
    # Store answer with analysis
    await session_service.add_answer(
        question_id=question_id,
        answer_text=request.answer,
        analysis_result=response,
        score={"clarity": response.get("score", {}).get("clarity", 0), 
              "confidence": response.get("score", {}).get("confidence", 0)},
        multi_agent_scores=response.get("multi_agent_analysis")
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
    from app.routers.analysis_helpers import perform_analysis_with_fallback
    
    # Verify question exists and belongs to user using generic validation
    question = await _validate_question_access(db, question_id, current_user["id"])
    
    # Get question text and role for multi-agent analysis
    question_text = question.question_text if hasattr(question, 'question_text') else "Interview question"
    role = getattr(question, 'role', '') if hasattr(question, 'role') else ""
    
    # Perform analysis with fallback
    response_dict = await perform_analysis_with_fallback(ai_service, request, question_text, role)
    
    # Store answer and analysis in database
    session_service = SessionService(db)
    
    # Store answer with analysis
    session_service.add_answer(
        question_id=question_id,
        answer_text=request.answer,
        analysis_result=response_dict,
        score={"clarity": response_dict.get("score", {}).get("clarity", 0), 
              "confidence": response_dict.get("score", {}).get("confidence", 0)},
        multi_agent_scores=response_dict.get("multi_agent_analysis")
    )
    
    # Return in the expected format
    if 'multi_agent_analysis' in response_dict:
        # Create proper response object using Pydantic model
        return AnalyzeAnswerResponse(
            analysis=response_dict.get("analysis", ""),
            score=response_dict.get("score", {}),
            suggestions=response_dict.get("suggestions", []),
            jobDescription=request.jobDescription,
            answer=request.answer,
            service_used=validated_service,
            multi_agent_analysis=response_dict.get("multi_agent_analysis")
        )
    else:
        # Return original response if it's not a dict
        return response_dict


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