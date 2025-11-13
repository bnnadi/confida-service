from fastapi import APIRouter, HTTPException, Query, Depends
# SQLAlchemy imports removed as they were unused
from typing import Optional, List, Dict
from app.models.schemas import (
    ParseJDRequest, ParseJDResponse, AnalyzeAnswerRequest, AnalyzeAnswerResponse,
    JobRequest, StructuredQuestionResponse
)
# handle_service_errors import removed as it was unused
from app.utils.validators import InputValidator, create_service_query_param
# DatabaseOperationHandler removed - using unified database service
from app.services.database_service import get_db, get_async_db
from app.services.question_store import QuestionStoreService
from app.middleware.auth_middleware import get_current_user_required
from app.dependencies import get_ai_client_dependency
from app.services.ai_client import AIServiceUnavailableError
from app.utils.fallback import get_fallback_response

router = APIRouter(prefix="/api/v1", tags=["interview"])

def _map_embedding_vectors(questions_data, persisted_questions, embedding_vectors):
    """
    Maps embeddings from AI service question IDs to persisted DB IDs.
    
    Args:
        questions_data: List of question dicts from AI service
        persisted_questions: List of persisted Question objects
        embedding_vectors: Dict mapping AI service IDs to embeddings
        
    Returns:
        Dict mapping persisted DB IDs to embeddings
    """
    embedding_map = {}
    for q_data, persisted_q in zip(questions_data, persisted_questions):
        ai_id = q_data.get("question_id") or q_data.get("id")
        db_id = str(persisted_q.id)
        
        if ai_id and ai_id in embedding_vectors:
            embedding_map[db_id] = embedding_vectors[ai_id]
        elif db_id in embedding_vectors:  # Fallback: direct DB ID match
            embedding_map[db_id] = embedding_vectors[db_id]
    return embedding_map

async def _persist_and_sync_questions(
    questions_data: List[Dict],
    embedding_vectors: Dict[str, List[float]],
    session_id: Optional[str] = None
) -> List:
    """
    Shared logic for persisting and syncing questions with Qdrant.
    
    This helper consolidates all persistence and sync logic into a single reusable function.
    
    Args:
        questions_data: List of question dictionaries from AI service
        embedding_vectors: Dictionary mapping AI service question_id to embedding vectors
        session_id: Optional session ID for tracking
        
    Returns:
        List of persisted Question objects
    """
    async_db_gen = get_async_db()
    session = await async_db_gen.__anext__()
    try:
        question_store = QuestionStoreService(session)
        persisted = await question_store.persist_and_sync_questions(
            questions=questions_data,
            embeddings_dict=embedding_vectors,
            session_id=session_id
        )
        await session.commit()
        return persisted
    finally:
        await session.close()
        try:
            await async_db_gen.__anext__()  # Trigger cleanup
        except StopAsyncIteration:
            pass

@router.post("/questions/generate", response_model=StructuredQuestionResponse)
async def generate_questions(
    request: JobRequest,
    current_user: dict = Depends(get_current_user_required),
    ai_client = Depends(get_ai_client_dependency),
    db = Depends(get_async_db)
):
    """
    Generate structured interview questions using AI service.
    
    This endpoint:
    1. Calls ai-service /ai/questions/generate
    2. Persists new questions to PostgreSQL
    3. Generates embeddings and syncs to Qdrant
    4. Returns structured response
    """
    if not ai_client:
        raise HTTPException(status_code=503, detail="AI service unavailable")
    
    try:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        
        # Step 1: Call AI service for structured question generation
        try:
            ai_response = await ai_client.generate_questions_structured(
                role_name=request.role_name,
                job_description=request.job_description,
                resume=request.resume
            )
        except AIServiceUnavailableError as e:
            logger.warning(f"AI service unavailable, using enhanced fallback: {e}")
            # Use enhanced fallback that queries database
            db_session = await db.__anext__()
            try:
                fallback_response = await get_fallback_response(
                    operation="question_generation",
                    role=request.role_name,
                    count=10,
                    db_session=db_session,
                    job_description=request.job_description
                )
                ai_response = {
                    "questions": fallback_response.get("questions", []),
                    "identifiers": {
                        "role": request.role_name,
                        "difficulty": "medium",
                        "category": "general"
                    },
                    "embedding_vectors": {}
                }
                logger.info(f"Using fallback questions: {fallback_response.get('metadata', {}).get('source', 'unknown')}")
            finally:
                try:
                    await db.__anext__()
                except StopAsyncIteration:
                    pass
        
        # Validate AI service response structure
        if not isinstance(ai_response, dict):
            raise HTTPException(
                status_code=422,
                detail="Invalid AI service response: expected JSON object"
            )
        
        # Validate required fields
        required_fields = ["questions", "identifiers"]
        missing_required = [f for f in required_fields if f not in ai_response]
        if missing_required:
            raise HTTPException(
                status_code=422,
                detail=f"AI response missing required fields: {', '.join(missing_required)}"
            )
        
        # Check for optional fields (preferred but not required)
        if "embedding_vectors" not in ai_response:
            logger.warning(
                "AI response missing embedding_vectors (optional but preferred). "
                "Will generate embeddings via ai-service as needed."
            )
        
        # Extract questions and identifiers
        questions_data = ai_response.get("questions", [])
        identifiers = ai_response.get("identifiers", {})
        embedding_vectors = ai_response.get("embedding_vectors", {})
        
        if not questions_data:
            raise HTTPException(
                status_code=422,
                detail="AI service returned no questions"
            )
        
        # Validate identifiers shape (warn only - not strict requirement)
        expected_keys = ["skills", "focus_areas", "difficulty", "tone"]
        missing_keys = [k for k in expected_keys if k not in identifiers]
        if missing_keys:
            logger.warning(f"AI identifiers missing expected fields: {missing_keys}")
        
        logger.debug(f"AI response valid with {len(questions_data)} questions")
        
        # Step 2: Persist questions to PostgreSQL and sync to Qdrant (consolidated)
        persisted_questions = await _persist_and_sync_questions(
            questions_data=questions_data,
            embedding_vectors=embedding_vectors,
            session_id=None
        )
        
        # Step 3: Build final structured response
        from app.models.schemas import StructuredQuestion, QuestionIdentifier
        
        structured_questions = []
        # Ensure we have matching counts
        if len(questions_data) != len(persisted_questions):
            logger.warning(f"Mismatch: {len(questions_data)} questions_data vs {len(persisted_questions)} persisted")
        
        for q_data, persisted_q in zip(questions_data, persisted_questions):
            question_text = q_data.get("text") or q_data.get("question_text", "")
            if not question_text:
                continue
            
            # Extract identifiers if present
            identifiers_data = q_data.get("identifiers", {})
            question_identifier = None
            if identifiers_data:
                question_identifier = QuestionIdentifier(**identifiers_data) if isinstance(identifiers_data, dict) else identifiers_data
            
            # Get source - ensure source is valid literal
            source_raw = q_data.get("source", "newly_generated")
            if source_raw not in ["from_library", "newly_generated"]:
                source = "newly_generated"
            else:
                source = source_raw
            
            # Always use persisted question ID - guaranteed to exist
            question_id = str(persisted_q.id)
            
            structured_questions.append(StructuredQuestion(
                text=question_text,
                source=source,
                question_id=question_id,  # Always use persisted UUID
                metadata=q_data.get("metadata", {}),
                identifiers=question_identifier
            ))
        
        response = StructuredQuestionResponse(
            identifiers=identifiers,
            questions=structured_questions,
            embedding_vectors=embedding_vectors if embedding_vectors else None
        )
        
        logger.info(f"Successfully generated {len(structured_questions)} questions for role: {request.role_name}")
        return response
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to generate questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

@router.post("/parse-jd", response_model=ParseJDResponse)
async def parse_job_description(
    request: ParseJDRequest,
    service: Optional[str] = create_service_query_param(),
    current_user: dict = Depends(get_current_user_required),
    ai_client = Depends(get_ai_client_dependency)
):
    """
    Parse job description and generate relevant interview questions.
    
    ⚠️ DEPRECATED: This endpoint is maintained for backward compatibility only.
    It uses the structured question generation flow internally.
    New clients should use /api/v1/questions/generate instead.
    """
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.warning("Deprecated endpoint '/api/v1/parse-jd' called. Use '/api/v1/questions/generate' instead.")
    
    validated_service = InputValidator.validate_service(service)
    
    if not ai_client:
        raise HTTPException(status_code=503, detail="AI service unavailable")
    
    try:
        # Convert to structured request format
        from app.models.schemas import JobRequest
        
        job_request = JobRequest(
            role_name=request.role,
            job_description=request.jobDescription,
            resume=None,
            limit=10
        )
        
        # Call structured question generation
        structured_response = await ai_client.generate_questions_structured(
            role_name=job_request.role_name,
            job_description=job_request.job_description,
            resume=job_request.resume
        )
        
        # Extract questions from structured response
        questions_data = structured_response.get("questions", [])
        embedding_vectors = structured_response.get("embedding_vectors", {})
        
        # Persist questions using shared helper (consolidated logic)
        await _persist_and_sync_questions(
            questions_data=questions_data,
            embedding_vectors=embedding_vectors,
            session_id=None
        )
        
        # Format response for backward compatibility
        question_texts = [
            q.get("text") if isinstance(q, dict) else str(q)
            for q in questions_data
        ]
        
        # Count by source
        question_bank_count = sum(
            1 for q in questions_data 
            if (isinstance(q, dict) and q.get("source") == "from_library")
        )
        ai_generated_count = len(questions_data) - question_bank_count
        
        return ParseJDResponse(
            questions=question_texts,
            role=request.role,
            jobDescription=request.jobDescription,
            service_used=validated_service,
            question_bank_count=question_bank_count,
            ai_generated_count=ai_generated_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to generate questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

@router.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
async def analyze_answer(
    request: AnalyzeAnswerRequest,
    service: Optional[str] = create_service_query_param(),
    question_id: int = Query(..., description="Question ID to store the answer"),
    current_user: dict = Depends(get_current_user_required),
    ai_client = Depends(get_ai_client_dependency)
):
    """Analyze user's answer and provide feedback using AI service microservice."""
    validated_service = InputValidator.validate_service(service)
    
    if not ai_client:
        raise HTTPException(status_code=503, detail="AI service unavailable")
    
    try:
        # Verify question exists and belongs to user (async)
        from app.database.models import Question, InterviewSession, Answer
        from sqlalchemy import select
        
        async_db_gen = get_async_db()
        session = await async_db_gen.__anext__()
        try:
            # Verify question access
            result = await session.execute(
                select(Question)
                .join(InterviewSession)
                .where(
                    Question.id == question_id,
                    InterviewSession.user_id == current_user["id"]
                )
            )
            question = result.scalar_one_or_none()
            
            if not question:
                raise HTTPException(status_code=404, detail="Question not found")
            
            # Get question text and role for analysis
            question_text = question.question_text if hasattr(question, 'question_text') else "Interview question"
            role = getattr(question, 'role', '') if hasattr(question, 'role') else ""
            
            # Use AI service microservice for analysis
            response = await ai_client.analyze_answer(
                job_description=request.jobDescription,
                question=question_text,
                answer=request.answer,
                role=role
            )
            
            # Store answer and analysis in database directly
            answer = Answer(
                question_id=question_id,
                answer_text=request.answer,
                analysis_result=response,
                score={"clarity": response.get("score", {}).get("clarity", 0), 
                      "confidence": response.get("score", {}).get("confidence", 0)},
                multi_agent_scores=response.get("multi_agent_analysis")
            )
            
            session.add(answer)
            await session.commit()
        finally:
            await session.close()
            try:
                await async_db_gen.__anext__()  # Trigger cleanup
            except StopAsyncIteration:
                pass
        
        # Extract enhanced scoring rubric
        from app.routers.analysis_helpers import extract_enhanced_score
        enhanced_score = extract_enhanced_score(response)
        
        return AnalyzeAnswerResponse(
            analysis=response.get("analysis", ""),
            score=response.get("score", {}),
            enhanced_score=enhanced_score,
            suggestions=response.get("suggestions", []),
            jobDescription=request.jobDescription,
            answer=request.answer,
            service_used=validated_service,
            multi_agent_analysis=response.get("multi_agent_analysis")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to analyze answer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze answer: {str(e)}")

@router.get("/services")
async def get_available_services(ai_client = Depends(get_ai_client_dependency)):
    """
    Get status of AI service microservice.
    """
    if not ai_client:
        raise HTTPException(status_code=503, detail="AI service unavailable")
    
    try:
        is_healthy = await ai_client.health_check()
        health_status = {
            "ai_service_microservice": {
                "status": "healthy" if is_healthy else "unhealthy",
                "url": ai_client.base_url
            }
        }
        return {
            "ai_service_microservice": health_status["ai_service_microservice"],
            "status": "healthy" if is_healthy else "unhealthy"
        }
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")

@router.get("/models")
async def list_models():
    """
    List available AI models.
    
    Note: Models are managed by the ai-service microservice.
    """
    raise HTTPException(
        status_code=501,
        detail="Model listing not implemented. Use ai-service /models endpoint."
    )

@router.post("/models/{model_name}/pull")
async def pull_model(model_name: str):
    """
    Pull a model to AI service.
    
    Note: Model management is handled by the ai-service microservice.
    """
    raise HTTPException(
        status_code=501,
        detail="Model pulling not implemented. Use ai-service /models endpoint."
    )


# Note: Database operation handlers have been moved to DatabaseOperationHandler class
# for better organization and reusability

# Legacy handlers (kept for backward compatibility)
async def _handle_database_operation(operation_type: str, **kwargs):
    """
    Unified handler for database operations.
    
    Standardized to use async-only pattern.
    """
    # Use strategy pattern for operation handling
    operation_handlers = {
        "parse_jd": _handle_parse_jd_operation,
        "analyze_answer": _handle_analyze_answer_operation
    }
    
    handler = operation_handlers.get(operation_type)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown operation type: {operation_type}")
    
    # Always use async pattern (standardized)
    return await handler(is_async=True, **kwargs)

async def _handle_parse_jd_operation(is_async: bool, **kwargs):
    """Unified handler for JD parsing using ai-client."""
    from app.services.service_factory import get_ai_client
    
    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(status_code=500, detail="AI service not available")
    
    if is_async:
        async_db_gen = get_async_db()
        db = await async_db_gen.__anext__()
        try:
            return await _handle_parse_jd_unified(ai_client, db, **kwargs)
        finally:
            try:
                await async_db_gen.__anext__()
            except StopAsyncIteration:
                pass
    else:
        db = next(get_db())
        try:
            return await _handle_parse_jd_unified(ai_client, db, **kwargs)
        finally:
            db.close()

async def _handle_analyze_answer_operation(is_async: bool, **kwargs):
    """Unified analyze answer handler for both async and sync."""
    from app.services.service_factory import get_ai_client
    
    ai_client = get_ai_client()
    if not ai_client:
        raise HTTPException(status_code=500, detail="AI service not available")
    
    if is_async:
        async_db_gen = get_async_db()
        db = await async_db_gen.__anext__()
        try:
            return await _handle_async_analyze_answer(ai_client, db, **kwargs)
        finally:
            try:
                await async_db_gen.__anext__()
            except StopAsyncIteration:
                pass
    else:
        db = next(get_db())
        try:
            return await _handle_sync_analyze_answer(ai_client, db, **kwargs)
        finally:
            db.close()


async def _handle_parse_jd_unified(ai_client, db, request, validated_service, current_user):
    """
    JD parsing logic using provided ai-client.
    
    NOTE: This is a legacy handler kept for backward compatibility.
    Uses QuestionStoreService.persist_and_sync_questions() for consolidated logic.
    """
    from app.utils.logger import get_logger
    from app.exceptions import AIServiceError
    
    logger = get_logger(__name__)
    
    if not ai_client:
        raise AIServiceError("AI service unavailable")
    
    try:
        # Call ai-service for structured question generation
        try:
            response = await ai_client.generate_questions_structured(
                role_name=request.role,
                job_description=request.jobDescription,
                resume=getattr(request, "resume", None)
            )
        except AIServiceUnavailableError as e:
            logger.warning(f"AI service unavailable, using enhanced fallback: {e}")
            # Use enhanced fallback that queries database
            fallback_response = await get_fallback_response(
                operation="question_generation",
                role=request.role,
                count=10,
                db_session=db,
                job_description=request.jobDescription
            )
            response = {
                "questions": fallback_response.get("questions", []),
                "identifiers": {
                    "role": request.role,
                    "difficulty": "medium",
                    "category": "general"
                },
                "embedding_vectors": {}
            }
            logger.info(f"Using fallback questions: {fallback_response.get('metadata', {}).get('source', 'unknown')}")
        
        # Extract questions data
        questions_data = response.get("questions", [])
        embedding_vectors = response.get("embedding_vectors", {})
        
        # Persist questions to database using consolidated service method
        question_store = QuestionStoreService(db)
        _ = await question_store.persist_and_sync_questions(
            questions=questions_data,
            embeddings_dict=embedding_vectors,
            session_id=None
        )  # Questions persisted and synced to Qdrant
        
        # Extract question texts for response
        question_texts = [
            q.get("text") or q.get("question_text", "") 
            for q in questions_data
        ]
        
        # Count database vs AI questions by source
        db_count = sum(1 for q in questions_data if q.get("source") == "from_library")
        ai_count = len(questions_data) - db_count
        
        return ParseJDResponse(
            questions=question_texts,
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
    
    # Store answer and analysis in database directly
    from app.database.models import Answer
    
    if hasattr(db, 'execute'):  # Async session
        answer = Answer(
            question_id=question_id,
            answer_text=request.answer,
            analysis_result=response,
            score={"clarity": response.get("score", {}).get("clarity", 0), 
                  "confidence": response.get("score", {}).get("confidence", 0)},
            multi_agent_scores=response.get("multi_agent_analysis")
        )
        db.add(answer)
        await db.commit()
    else:  # Sync session
        answer = Answer(
            question_id=question_id,
            answer_text=request.answer,
            analysis_result=response,
            score={"clarity": response.get("score", {}).get("clarity", 0), 
                  "confidence": response.get("score", {}).get("confidence", 0)},
            multi_agent_scores=response.get("multi_agent_analysis")
        )
        db.add(answer)
        db.commit()
    
    # Extract enhanced scoring rubric
    from app.routers.analysis_helpers import extract_enhanced_score
    enhanced_score = extract_enhanced_score(response)
    
    return AnalyzeAnswerResponse(
        analysis=response.get("analysis", ""),
        score=response.get("score", {}),
        enhanced_score=enhanced_score,
        suggestions=response.get("suggestions", []),
        jobDescription=request.jobDescription,
        answer=request.answer,
        service_used=validated_service,
        multi_agent_analysis=response.get("multi_agent_analysis")
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
    
    # Store answer and analysis in database directly
    from app.database.models import Answer
    
    answer = Answer(
        question_id=question_id,
        answer_text=request.answer,
        analysis_result=response_dict,
        score={"clarity": response_dict.get("score", {}).get("clarity", 0), 
              "confidence": response_dict.get("score", {}).get("confidence", 0)},
        multi_agent_scores=response_dict.get("multi_agent_analysis")
    )
    
    db.add(answer)
    db.commit()
    
    # Extract enhanced scoring rubric
    from app.routers.analysis_helpers import extract_enhanced_score
    enhanced_score = extract_enhanced_score(response_dict)
    
    # Return in the expected format
    if 'multi_agent_analysis' in response_dict:
        # Create proper response object using Pydantic model
        return AnalyzeAnswerResponse(
            analysis=response_dict.get("analysis", ""),
            score=response_dict.get("score", {}),
            enhanced_score=enhanced_score,
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