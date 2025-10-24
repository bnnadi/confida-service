from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.services.database_service import get_db
from app.services.session_service import SessionService
from app.database.models import InterviewSession, Question
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

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

@router.post("/", response_model=InterviewSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Create a new interview session (supports both practice and interview modes)."""
    session_service = SessionService(db)
    
    if request.mode == "practice":
        session = session_service.create_practice_session(
            user_id=current_user["id"],
            role=request.role,
            scenario_id=request.scenario_id
        )
    elif request.mode == "interview":
        session = session_service.create_interview_session(
            user_id=current_user["id"],
            role=request.role,
            job_title=request.job_title,
            job_description=request.job_description
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'practice' or 'interview'")
    
    return session

@router.get("/", response_model=List[InterviewSessionResponse])
async def get_user_sessions(
    current_user: dict = Depends(get_current_user_required),
    limit: int = Query(10, description="Number of sessions to return"),
    offset: int = Query(0, description="Number of sessions to skip"),
    db: Session = Depends(get_db)
):
    """Get all interview sessions for a user."""
    session_service = SessionService(db)
    sessions = session_service.get_user_sessions(current_user["id"], limit, offset)
    return sessions

@router.get("/{session_id}", response_model=CompleteSessionResponse)
async def get_session(
    session_id: int,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get a complete session with questions and answers."""
    session_service = SessionService(db)
    session_data = session_service.get_session_with_questions_and_answers(session_id, current_user["id"])
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session_data

@router.post("/{session_id}/questions", response_model=List[dict])
async def add_questions_to_session(
    session_id: int,
    request: AddQuestionsRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Add questions to an interview session."""
    session_service = SessionService(db)
    
    # Verify session belongs to user
    session = session_service.get_session(session_id, current_user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = session_service.add_questions_to_session(session_id, request.questions)
    return [{"id": q.id, "question_text": q.question_text, "question_order": q.question_order} for q in questions]

@router.get("/{session_id}/questions", response_model=List[dict])
async def get_session_questions(
    session_id: int,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get all questions for a session."""
    session_service = SessionService(db)
    
    # Verify session belongs to user
    session = session_service.get_session(session_id, current_user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = session_service.get_session_questions(session_id)
    return [{"id": q.id, "question_text": q.question_text, "question_order": q.question_order} for q in questions]

@router.post("/questions/{question_id}/answers", response_model=AnswerResponse)
async def add_answer_to_question(
    question_id: int,
    request: AddAnswerRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Add an answer to a question."""
    session_service = SessionService(db)
    
    # Verify question exists and belongs to user's session
    question = db.query(Question).join(InterviewSession).filter(
        Question.id == question_id,
        InterviewSession.user_id == current_user["id"]
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    answer = session_service.add_answer(
        question_id=question_id,
        answer_text=request.answer_text,
        analysis_result=request.analysis_result,
        score=request.score
    )
    return answer

@router.get("/questions/{question_id}/answers", response_model=List[AnswerResponse])
async def get_question_answers(
    question_id: int,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get all answers for a question."""
    session_service = SessionService(db)
    
    # Verify question exists and belongs to user's session
    question = db.query(Question).join(InterviewSession).filter(
        Question.id == question_id,
        InterviewSession.user_id == current_user["id"]
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    answers = session_service.get_question_answers(question_id)
    return answers

@router.patch("/{session_id}/status")
async def update_session_status(
    session_id: int,
    status: str = Query(..., description="New status (active, completed, abandoned)"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Update session status."""
    session_service = SessionService(db)
    session = session_service.update_session_status(session_id, status, current_user["id"])
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session status updated successfully", "status": session.status}

@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Delete a session and all its data."""
    session_service = SessionService(db)
    success = session_service.delete_session(session_id, current_user["id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}

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
        preview_data = session_service.preview_practice_session(role, scenario_id)
    elif mode == "interview":
        if not job_title or not job_description:
            raise HTTPException(status_code=400, detail="job_title and job_description are required for interview mode")
        preview_data = session_service.preview_interview_session(role, job_title, job_description)
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'practice' or 'interview'")
    
    # Convert questions to QuestionPreview objects
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
    scenarios = session_service.get_available_scenarios()
    
    return ScenarioListResponse(
        scenarios=scenarios,
        total=len(scenarios)
    )
