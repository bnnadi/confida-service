from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Annotated, List, Optional
from app.services.database_service import get_db
from app.services.session_service import SessionService
from app.database.models import InterviewSession, Question, SessionQuestion
from app.models.schemas import (
    CreateSessionRequest, 
    InterviewSessionResponse, 
    CompleteSessionResponse,
    AddQuestionsRequest,
    AddAnswerRequest,
    AnswerResponse,
    SessionPreviewResponse,
    ScenarioListResponse,
    QuestionPreview
)
from app.middleware.auth_middleware import get_current_user_required
from app.services.audit_service import log_data_access


def validate_session_uuid(
    session_id: str = Path(..., description="Session UUID"),
) -> str:
    """Validate session_id is a valid UUID. Raises 422 for invalid format."""
    try:
        UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format")
    return session_id


def validate_question_uuid(
    question_id: str = Path(..., description="Question UUID"),
) -> str:
    """Validate question_id is a valid UUID. Raises 422 for invalid format."""
    try:
        UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID format")
    return question_id


SessionId = Annotated[str, Depends(validate_session_uuid)]
QuestionId = Annotated[str, Depends(validate_question_uuid)]


router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _session_to_response(session: InterviewSession) -> InterviewSessionResponse:
    """Convert InterviewSession ORM to InterviewSessionResponse schema."""
    return InterviewSessionResponse(
        id=str(session.id),
        user_id=str(session.user_id),
        mode=session.mode or "interview",
        role=session.role,
        job_description=session.job_description or None,
        scenario_id=session.scenario_id,
        question_source=session.question_source or "generated",
        status=session.status or "active",
        total_questions=session.total_questions or 0,
        completed_questions=session.completed_questions or 0,
        created_at=session.created_at.isoformat() if session.created_at else "",
        updated_at=session.updated_at.isoformat() if session.updated_at else None,
    )


@router.post("/", response_model=InterviewSessionResponse, status_code=201)
async def create_session(
    request: CreateSessionRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Create a new interview session (supports both practice and interview modes)."""
    try:
        session_service = SessionService(db)
        if request.mode == "practice":
            if not request.scenario_id:
                raise HTTPException(status_code=400, detail="scenario_id is required for practice mode")
            session = await session_service.create_practice_session(
                user_id=current_user["id"],
                role=request.role,
                scenario_id=request.scenario_id
            )
        elif request.mode == "interview":
            session = await session_service.create_interview_session(
                user_id=current_user["id"],
                role=request.role,
                job_title=request.job_title,
                job_description=request.job_description
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Must be 'practice' or 'interview'")
        ip = http_request.client.host if http_request.client else None
        log_data_access(db, current_user["id"], "session", "write", resource_id=str(session.id), ip_address=ip)
        return _session_to_response(session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[InterviewSessionResponse])
async def get_user_sessions(
    request: Request,
    current_user: dict = Depends(get_current_user_required),
    limit: int = Query(10, description="Number of sessions to return"),
    offset: int = Query(0, description="Number of sessions to skip"),
    db: Session = Depends(get_db)
):
    """Get all interview sessions for a user."""
    session_service = SessionService(db)
    sessions = await session_service.get_user_sessions(current_user["id"], limit, offset)
    ip = request.client.host if request.client else None
    log_data_access(db, current_user["id"], "sessions", "list", ip_address=ip)
    return [_session_to_response(s) for s in sessions]


@router.get("/preview", response_model=SessionPreviewResponse)
async def preview_session(
    mode: str = Query(..., description="Session mode: 'practice' or 'interview'"),
    role: str = Query(..., description="Job role"),
    scenario_id: Optional[str] = Query(None, description="Scenario ID for practice mode"),
    job_title: Optional[str] = Query(None, description="Job title for interview mode"),
    job_description: Optional[str] = Query(None, description="Job description for interview mode"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Preview a session without creating it."""
    session_service = SessionService(db)
    if mode == "practice":
        if not scenario_id:
            raise HTTPException(status_code=400, detail="scenario_id is required for practice mode")
        preview_data = await session_service.preview_practice_session(role, scenario_id)
    elif mode == "interview":
        if not job_title or not job_description:
            raise HTTPException(status_code=400, detail="job_title and job_description are required for interview mode")
        preview_data = await session_service.preview_interview_session(role, job_title, job_description)
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'practice' or 'interview'")
    questions = [
        QuestionPreview(
            id=q["id"],
            text=q["text"],
            type=q["type"],
            difficulty_level=q["difficulty_level"],
            category=q["category"]
        ) for q in preview_data["questions"]
    ]
    return SessionPreviewResponse(
        mode=preview_data["mode"],
        role=preview_data["role"],
        questions=questions,
        total_questions=preview_data["total_questions"],
        estimated_duration=preview_data["estimated_duration"]
    )


@router.get("/scenarios", response_model=ScenarioListResponse)
async def get_scenarios(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get available practice scenarios."""
    session_service = SessionService(db)
    scenarios = await session_service.get_available_scenarios()
    return ScenarioListResponse(
        scenarios=scenarios,
        total=len(scenarios)
    )


@router.get("/{session_id}", response_model=CompleteSessionResponse)
async def get_session(
    request: Request,
    session_id: SessionId,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get a complete session with questions and answers."""
    session_service = SessionService(db)
    session_data = await session_service.get_session_with_questions_and_answers(session_id, current_user["id"])
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    ip = request.client.host if request.client else None
    log_data_access(db, current_user["id"], "session", "get", resource_id=session_id, ip_address=ip)
    return session_data

@router.post("/{session_id}/questions", response_model=List[dict])
async def add_questions_to_session(
    http_request: Request,
    session_id: SessionId,
    request: AddQuestionsRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Add questions to an interview session."""
    session_service = SessionService(db)
    
    # Verify session belongs to user
    session = await session_service.get_session(session_id, current_user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = await session_service.add_questions_to_session(
        session_id, request.questions, current_user["id"]
    )
    ip = http_request.client.host if http_request.client else None
    log_data_access(db, current_user["id"], "session_question", "write", resource_id=session_id, ip_address=ip)
    return [
        {"id": str(q.id), "question_text": q.question.question_text if q.question else "", "question_order": q.question_order}
        for q in questions
    ]

@router.get("/{session_id}/questions", response_model=List[dict])
async def get_session_questions(
    session_id: SessionId,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get all questions for a session."""
    session_service = SessionService(db)
    
    questions = await session_service.get_session_questions(session_id, current_user["id"])
    if questions is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return questions


@router.delete("/{session_id}/questions/{question_id}", status_code=200)
async def remove_question_from_session(
    request: Request,
    session_id: SessionId,
    question_id: QuestionId,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Remove a question from a session by SessionQuestion id."""
    session_service = SessionService(db)
    success = await session_service.remove_question_from_session(
        session_id, question_id, current_user["id"]
    )
    if not success:
        raise HTTPException(status_code=404, detail="Session question not found")
    ip = request.client.host if request.client else None
    log_data_access(db, current_user["id"], "session_question", "delete", resource_id=question_id, ip_address=ip)
    return {"message": "Question removed from session"}


@router.post("/questions/{question_id}/answers", response_model=AnswerResponse)
async def add_answer_to_question(
    question_id: str,
    request: AddAnswerRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Add an answer to a question."""
    from app.database.models import Answer, SessionQuestion
    from app.services.encryption_service import get_encryption_service
    from app.services.audit_service import log_data_access

    session_question = db.query(SessionQuestion).join(
        InterviewSession, SessionQuestion.session_id == InterviewSession.id
    ).filter(
        SessionQuestion.question_id == question_id,
        InterviewSession.user_id == current_user["id"]
    ).first()
    if not session_question:
        raise HTTPException(status_code=404, detail="Question not found")

    enc = get_encryption_service()
    uid = str(current_user["id"])
    enc_answer = enc.encrypt(request.answer_text, uid) or request.answer_text
    enc_analysis = enc.encrypt(request.analysis_result, uid) if enc.is_enabled() and request.analysis_result else request.analysis_result
    enc_score = enc.encrypt(request.score, uid) if enc.is_enabled() and request.score else request.score

    answer = Answer(
        question_id=question_id,
        session_id=session_question.session_id,
        answer_text=enc_answer,
        analysis_result=enc_analysis,
        score=enc_score,
        audio_file_id=request.audio_file_id
    )
    db.add(answer)
    log_data_access(db, uid, "answer", "write", question_id)
    
    # Update SessionQuestion.session_specific_context to store answer audio file ID
    if request.audio_file_id:
        session_question = db.query(SessionQuestion).filter(
            SessionQuestion.question_id == question_id
        ).first()
        
        if session_question:
            # Update session_specific_context with answer audio file ID
            context = session_question.session_specific_context or {}
            if not isinstance(context, dict):
                context = {}
            context["answer_audio_file_id"] = request.audio_file_id
            session_question.session_specific_context = context
    
    db.commit()
    db.refresh(answer)
    
    return answer

@router.get("/questions/{question_id}/answers", response_model=List[AnswerResponse])
async def get_question_answers(
    question_id: str,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get all answers for a question."""
    from app.database.models import Answer
    
    # Verify question exists and belongs to user's session (via SessionQuestion -> InterviewSession)
    question = db.query(Question).join(SessionQuestion).join(InterviewSession).filter(
        Question.id == question_id,
        InterviewSession.user_id == current_user["id"]
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Get all answers for the question
    answers = db.query(Answer).filter(Answer.question_id == question_id).all()
    return answers

@router.patch("/{session_id}/status")
async def update_session_status(
    request: Request,
    session_id: SessionId,
    status: str = Query(..., description="New status (active, completed, abandoned)"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Update session status."""
    session_service = SessionService(db)
    session = await session_service.update_session_status(session_id, status, current_user["id"])
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    ip = request.client.host if request.client else None
    log_data_access(db, current_user["id"], "session", "write", resource_id=session_id, ip_address=ip)
    return {"message": "Session status updated successfully", "status": session.status}

@router.delete("/{session_id}", status_code=204)
async def delete_session(
    request: Request,
    session_id: SessionId,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Delete a session and all its data."""
    session_service = SessionService(db)
    success = await session_service.delete_session(session_id, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    ip = request.client.host if request.client else None
    log_data_access(db, current_user["id"], "session", "delete", resource_id=session_id, ip_address=ip)
    return Response(status_code=204)
