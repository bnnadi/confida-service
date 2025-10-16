from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.database.models import InterviewSession, Question, SessionQuestion, Answer, User
from app.exceptions import AIServiceError
from app.utils.error_context import ErrorContext
from app.services.question_service import QuestionService


class SessionService:
    """Service for managing interview sessions, questions, and answers."""
    
    def __init__(self, db: Session):
        self.db = db
        self.question_service = QuestionService(db)
    
    def create_session(self, user_id: int, role: str, job_description: str) -> InterviewSession:
        """Create a new interview session (legacy method for backward compatibility)."""
        try:
            session = InterviewSession(
                user_id=user_id,
                mode="interview",
                role=role,
                job_description=job_description,
                question_source="generated",
                status="active"
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to create interview session: {e}")
    
    def create_practice_session(self, user_id: int, role: str, scenario_id: str) -> InterviewSession:
        """Create a new practice session with scenario-based questions."""
        try:
            # Generate questions from scenario
            questions_data = self.question_engine.generate_questions_from_scenario(scenario_id)
            
            # Create session
            session = InterviewSession(
                user_id=user_id,
                mode="practice",
                role=role,
                scenario_id=scenario_id,
                question_source="scenario",
                question_ids=[q["id"] for q in questions_data],
                status="active",
                total_questions=len(questions_data)
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            # Add questions to session
            self._add_questions_to_session(session.id, questions_data)
            
            return session
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to create practice session: {e}")
    
    def create_interview_session(self, user_id: int, role: str, job_title: str, job_description: str) -> InterviewSession:
        """Create a new job-based interview session with AI-generated questions."""
        try:
            # Generate questions from job description
            questions_data = self.question_engine.generate_questions_from_job(job_title, job_description)
            
            # Create session
            session = InterviewSession(
                user_id=user_id,
                mode="interview",
                role=role,
                job_description=job_description,
                question_source="generated",
                question_ids=[q["id"] for q in questions_data],
                job_context={
                    "job_title": job_title,
                    "job_description": job_description
                },
                status="active",
                total_questions=len(questions_data)
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            # Add questions to session
            self._add_questions_to_session(session.id, questions_data)
            
            return session
        except Exception as e:
            self.db.rollback()
            raise AIServiceError(f"Failed to create interview session: {e}")
    
    def _add_questions_to_session(self, session_id: int, questions_data: List[Dict[str, Any]]) -> List[Question]:
        """Add questions to a session from question data."""
        try:
            question_objects = []
            for i, question_data in enumerate(questions_data, 1):
                question = Question(
                    session_id=session_id,
                    question_text=question_data["text"],
                    question_order=i,
                    difficulty_level=question_data.get("difficulty_level", "medium"),
                    category=question_data.get("category", "general")
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
    
    def preview_practice_session(self, role: str, scenario_id: str) -> Dict[str, Any]:
        """Preview a practice session without creating it."""
        try:
            questions_data = self.question_engine.generate_questions_from_scenario(scenario_id)
            
            return {
                "mode": "practice",
                "role": role,
                "questions": questions_data,
                "total_questions": len(questions_data),
                "estimated_duration": len(questions_data) * 3  # 3 minutes per question
            }
        except Exception as e:
            raise AIServiceError(f"Failed to preview practice session: {e}")
    
    def preview_interview_session(self, role: str, job_title: str, job_description: str) -> Dict[str, Any]:
        """Preview an interview session without creating it."""
        try:
            questions_data = self.question_engine.generate_questions_from_job(job_title, job_description)
            
            return {
                "mode": "interview",
                "role": role,
                "questions": questions_data,
                "total_questions": len(questions_data),
                "estimated_duration": len(questions_data) * 3  # 3 minutes per question
            }
        except Exception as e:
            raise AIServiceError(f"Failed to preview interview session: {e}")
    
    def create_session_with_questions_atomic(
        self, 
        user_id: int, 
        role: str, 
        job_description: str, 
        questions: List[str]
    ) -> tuple[InterviewSession, List[Question]]:
        """Create a session with questions in a single atomic transaction."""
        from app.utils.logger import get_logger
        from app.exceptions import AIServiceError
        
        logger = get_logger(__name__)
        
        try:
            # Start transaction
            session = InterviewSession(
                user_id=user_id,
                mode="interview",
                role=role,
                job_description=job_description,
                question_source="generated",
                status="active",
                total_questions=len(questions)
            )
            self.db.add(session)
            self.db.flush()  # Get the session ID without committing
            
            # Bulk create questions
            question_objects = []
            for i, question_text in enumerate(questions, 1):
                # Check if question already exists in global bank
                existing_question = self._find_question_by_text(question_text)
                
                if existing_question:
                    question_id = existing_question.id
                    # Update usage count
                    existing_question.usage_count = (existing_question.usage_count or 0) + 1
                else:
                    # Create new question in global bank
                    question = Question(
                        question_text=question_text,
                        question_metadata={
                            "created_from_session": str(session.id),
                            "created_at": datetime.utcnow().isoformat()
                        },
                        difficulty_level="medium",
                        category="general",
                        usage_count=1
                    )
                    self.db.add(question)
                    self.db.flush()  # Get the question ID
                    question_id = question.id
                
                # Create session-question link
                session_question = SessionQuestion(
                    session_id=session.id,
                    question_id=question_id,
                    question_order=i
                )
                self.db.add(session_question)
                question_objects.append(question)
            
            # Commit the entire transaction
            self.db.commit()
            self.db.refresh(session)
            
            logger.info(f"Successfully created session {session.id} with {len(question_objects)} questions atomically")
            return session, question_objects
            
        except Exception as e:
            # Rollback on any error
            self.db.rollback()
            logger.error(f"Error creating session with questions atomically: {e}")
            raise AIServiceError(f"Failed to create session with questions: {e}")
    
    def _find_question_by_text(self, question_text: str) -> Optional[Question]:
        """Find a question by its text."""
        try:
            return self.db.query(Question).filter(Question.question_text == question_text).first()
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error finding question by text: {e}")
            return None

    def get_available_scenarios(self) -> List[Dict[str, str]]:
        """Get list of available practice scenarios."""
        return self.question_engine.get_available_scenarios()
