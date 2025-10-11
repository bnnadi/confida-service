from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.services.session_service import SessionService
from app.models.interview import InterviewSession, Question
from app.models.schemas import (
    CreateSessionRequest, 
    InterviewSessionResponse, 
    CompleteSessionResponse,
    AddQuestionsRequest,
    AddAnswerRequest,
    AnswerResponse
)
from app.utils.endpoint_helpers import handle_service_errors

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

@router.post("/", response_model=InterviewSessionResponse)
@handle_service_errors("creating interview session")
async def create_session(
    request: CreateSessionRequest,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Create a new interview session."""
    session_service = SessionService(db)
    session = session_service.create_session(
        user_id=user_id,
        role=request.role,
        job_description=request.job_description
    )
    return session

@router.get("/", response_model=List[InterviewSessionResponse])
@handle_service_errors("getting user sessions")
async def get_user_sessions(
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    limit: int = Query(10, description="Number of sessions to return"),
    offset: int = Query(0, description="Number of sessions to skip"),
    db: Session = Depends(get_db)
):
    """Get all interview sessions for a user."""
    session_service = SessionService(db)
    sessions = session_service.get_user_sessions(user_id, limit, offset)
    return sessions

@router.get("/{session_id}", response_model=CompleteSessionResponse)
@handle_service_errors("getting session details")
async def get_session(
    session_id: int,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Get a complete session with questions and answers."""
    session_service = SessionService(db)
    session_data = session_service.get_session_with_questions_and_answers(session_id, user_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session_data

@router.post("/{session_id}/questions", response_model=List[dict])
@handle_service_errors("adding questions to session")
async def add_questions_to_session(
    session_id: int,
    request: AddQuestionsRequest,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Add questions to an interview session."""
    session_service = SessionService(db)
    
    # Verify session belongs to user
    session = session_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = session_service.add_questions_to_session(session_id, request.questions)
    return [{"id": q.id, "question_text": q.question_text, "question_order": q.question_order} for q in questions]

@router.get("/{session_id}/questions", response_model=List[dict])
@handle_service_errors("getting session questions")
async def get_session_questions(
    session_id: int,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Get all questions for a session."""
    session_service = SessionService(db)
    
    # Verify session belongs to user
    session = session_service.get_session(session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    questions = session_service.get_session_questions(session_id)
    return [{"id": q.id, "question_text": q.question_text, "question_order": q.question_order} for q in questions]

@router.post("/questions/{question_id}/answers", response_model=AnswerResponse)
@handle_service_errors("adding answer to question")
async def add_answer_to_question(
    question_id: int,
    request: AddAnswerRequest,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Add an answer to a question."""
    session_service = SessionService(db)
    
    # Verify question exists and belongs to user's session
    question = db.query(Question).join(InterviewSession).filter(
        Question.id == question_id,
        InterviewSession.user_id == user_id
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
@handle_service_errors("getting question answers")
async def get_question_answers(
    question_id: int,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Get all answers for a question."""
    session_service = SessionService(db)
    
    # Verify question exists and belongs to user's session
    question = db.query(Question).join(InterviewSession).filter(
        Question.id == question_id,
        InterviewSession.user_id == user_id
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    answers = session_service.get_question_answers(question_id)
    return answers

@router.patch("/{session_id}/status")
@handle_service_errors("updating session status")
async def update_session_status(
    session_id: int,
    status: str = Query(..., description="New status (active, completed, abandoned)"),
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Update session status."""
    session_service = SessionService(db)
    session = session_service.update_session_status(session_id, status, user_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session status updated successfully", "status": session.status}

@router.delete("/{session_id}")
@handle_service_errors("deleting session")
async def delete_session(
    session_id: int,
    user_id: int = Query(..., description="User ID (temporary - will be from auth)"),
    db: Session = Depends(get_db)
):
    """Delete a session and all its data."""
    session_service = SessionService(db)
    success = session_service.delete_session(session_id, user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}
