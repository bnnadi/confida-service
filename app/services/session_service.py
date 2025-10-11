from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from app.models.interview import InterviewSession, Question, Answer
from app.models.user import User
from app.exceptions import AIServiceError
from app.utils.error_context import ErrorContext


class SessionService:
    """Service for managing interview sessions, questions, and answers."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, user_id: int, role: str, job_description: str) -> InterviewSession:
        """Create a new interview session."""
        try:
            session = InterviewSession(
                user_id=user_id,
                role=role,
                job_description=job_description,
                status="active"
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to create interview session: {e}")
    
    def get_session(self, session_id: int, user_id: Optional[int] = None) -> Optional[InterviewSession]:
        """Get an interview session by ID."""
        try:
            query = self.db.query(InterviewSession).filter(InterviewSession.id == session_id)
            if user_id:
                query = query.filter(InterviewSession.user_id == user_id)
            return query.first()
        except Exception as e:
            raise AIServiceError(f"Failed to get interview session: {e}")
    
    def get_user_sessions(self, user_id: int, limit: int = 10, offset: int = 0) -> List[InterviewSession]:
        """Get all interview sessions for a user."""
        try:
            return (self.db.query(InterviewSession)
                    .filter(InterviewSession.user_id == user_id)
                    .order_by(desc(InterviewSession.created_at))
                    .offset(offset)
                    .limit(limit)
                    .all())
        except Exception as e:
            raise AIServiceError(f"Failed to get user sessions: {e}")
    
    def update_session_status(self, session_id: int, status: str, user_id: Optional[int] = None) -> Optional[InterviewSession]:
        """Update session status."""
        try:
            query = self.db.query(InterviewSession).filter(InterviewSession.id == session_id)
            if user_id:
                query = query.filter(InterviewSession.user_id == user_id)
            
            session = query.first()
            if session:
                session.status = status
                self.db.commit()
                self.db.refresh(session)
            return session
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to update session status: {e}")
    
    def add_questions_to_session(self, session_id: int, questions: List[str]) -> List[Question]:
        """Add questions to an interview session."""
        try:
            session = self.get_session(session_id)
            if not session:
                raise AIServiceError("Session not found")
            
            question_objects = []
            for i, question_text in enumerate(questions, 1):
                question = Question(
                    session_id=session_id,
                    question_text=question_text,
                    question_order=i
                )
                self.db.add(question)
                question_objects.append(question)
            
            self.db.commit()
            for question in question_objects:
                self.db.refresh(question)
            
            return question_objects
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to add questions to session: {e}")
    
    def get_session_questions(self, session_id: int) -> List[Question]:
        """Get all questions for a session."""
        try:
            return (self.db.query(Question)
                    .filter(Question.session_id == session_id)
                    .order_by(Question.question_order)
                    .all())
        except Exception as e:
            raise AIServiceError(f"Failed to get session questions: {e}")
    
    def add_answer(self, question_id: int, answer_text: str, 
                   analysis_result: Optional[Dict[str, Any]] = None,
                   score: Optional[Dict[str, Any]] = None) -> Answer:
        """Add an answer to a question."""
        try:
            answer = Answer(
                question_id=question_id,
                answer_text=answer_text,
                analysis_result=analysis_result,
                score=score
            )
            self.db.add(answer)
            self.db.commit()
            self.db.refresh(answer)
            return answer
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to add answer: {e}")
    
    def get_question_answers(self, question_id: int) -> List[Answer]:
        """Get all answers for a question."""
        try:
            return (self.db.query(Answer)
                    .filter(Answer.question_id == question_id)
                    .order_by(Answer.created_at)
                    .all())
        except Exception as e:
            raise AIServiceError(f"Failed to get question answers: {e}")
    
    def get_session_with_questions_and_answers(self, session_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get a complete session with questions and answers."""
        try:
            session = self.get_session(session_id, user_id)
            if not session:
                return None
            
            questions = self.get_session_questions(session_id)
            questions_with_answers = []
            
            for question in questions:
                answers = self.get_question_answers(question.id)
                questions_with_answers.append({
                    "question": question,
                    "answers": answers
                })
            
            return {
                "session": session,
                "questions": questions_with_answers
            }
        except Exception as e:
            raise AIServiceError(f"Failed to get complete session: {e}")
    
    def delete_session(self, session_id: int, user_id: Optional[int] = None) -> bool:
        """Delete a session and all its questions and answers."""
        try:
            query = self.db.query(InterviewSession).filter(InterviewSession.id == session_id)
            if user_id:
                query = query.filter(InterviewSession.user_id == user_id)
            
            session = query.first()
            if session:
                # Cascade delete will handle questions and answers
                self.db.delete(session)
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to delete session: {e}")
