"""
Async Session Service.

This service provides async database operations for managing interview sessions,
including creating sessions, adding questions, and storing answers.
"""
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.database.models import InterviewSession, Question, SessionQuestion, Answer
from app.database.async_operations import AsyncDatabaseOperations
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

class AsyncSessionService:
    """Async service for managing interview sessions."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.db_ops = AsyncDatabaseOperations(db_session)
    
    async def create_session(
        self,
        user_id: str,
        role: str,
        job_description: str,
        title: Optional[str] = None
    ) -> InterviewSession:
        """Create a new interview session."""
        try:
            session_data = {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role": role,
                "job_description": job_description,
                "title": title or f"Interview for {role}",
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            session = await self.db_ops.create(InterviewSession, **session_data)
            await self.db_session.commit()
            
            logger.info(f"Created interview session {session.id} for user {user_id}")
            return session
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error creating session: {e}")
            raise
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[InterviewSession]:
        """Get a session by ID, ensuring it belongs to the user."""
        try:
            result = await self.db_session.execute(
                select(InterviewSession)
                .where(
                    InterviewSession.id == session_id,
                    InterviewSession.user_id == user_id
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[InterviewSession]:
        """Get all sessions for a user."""
        try:
            result = await self.db_session.execute(
                select(InterviewSession)
                .where(InterviewSession.user_id == user_id)
                .order_by(InterviewSession.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    async def update_session(
        self,
        session_id: str,
        user_id: str,
        **updates
    ) -> Optional[InterviewSession]:
        """Update a session."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                return None
            
            # Update fields
            updates["updated_at"] = datetime.utcnow()
            await self.db_session.execute(
                update(InterviewSession)
                .where(InterviewSession.id == session_id)
                .values(**updates)
            )
            
            await self.db_session.commit()
            
            # Return updated session
            return await self.get_session(session_id, user_id)
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error updating session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a session and all associated data."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                return False
            
            # Delete session (cascade will handle related records)
            await self.db_session.execute(
                delete(InterviewSession)
                .where(InterviewSession.id == session_id)
            )
            
            await self.db_session.commit()
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def add_questions_to_session(
        self,
        session_id: str,
        questions: List[str],
        user_id: str
    ) -> List[SessionQuestion]:
        """Add questions to a session."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                raise ValueError("Session not found or access denied")
            
            session_questions = []
            
            for i, question_text in enumerate(questions):
                # Check if question already exists in global bank
                existing_question = await self._find_question_by_text(question_text)
                
                if existing_question:
                    question_id = existing_question.id
                else:
                    # Create new question in global bank
                    question_data = {
                        "id": uuid.uuid4(),
                        "question_text": question_text,
                        "question_metadata": {
                            "created_from_session": session_id,
                            "created_at": datetime.utcnow().isoformat()
                        },
                        "difficulty_level": "medium",
                        "category": "general",
                        "usage_count": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    new_question = await self.db_ops.create(Question, **question_data)
                    question_id = new_question.id
                
                # Create session-question link
                session_question_data = {
                    "id": uuid.uuid4(),
                    "session_id": session_id,
                    "question_id": question_id,
                    "question_order": i + 1,
                    "created_at": datetime.utcnow()
                }
                session_question = await self.db_ops.create(SessionQuestion, **session_question_data)
                session_questions.append(session_question)
            
            await self.db_session.commit()
            logger.info(f"Added {len(questions)} questions to session {session_id}")
            return session_questions
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error adding questions to session {session_id}: {e}")
            raise
    
    async def get_session_questions(
        self,
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all questions for a session."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                return []
            
            result = await self.db_session.execute(
                select(SessionQuestion, Question)
                .join(Question, SessionQuestion.question_id == Question.id)
                .where(SessionQuestion.session_id == session_id)
                .order_by(SessionQuestion.question_order)
            )
            
            questions = []
            for session_question, question in result.fetchall():
                questions.append({
                    "session_question_id": session_question.id,
                    "question_id": question.id,
                    "question_text": question.question_text,
                    "question_order": session_question.question_order,
                    "difficulty_level": question.difficulty_level,
                    "category": question.category,
                    "created_at": session_question.created_at
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions for session {session_id}: {e}")
            return []
    
    async def add_answer(
        self,
        question_id: str,
        answer_text: str,
        analysis_result: Dict[str, Any],
        score: Dict[str, float],
        user_id: str
    ) -> Optional[Answer]:
        """Add an answer to a question."""
        try:
            # Verify question exists and user has access
            result = await self.db_session.execute(
                select(Question, InterviewSession)
                .join(SessionQuestion, Question.id == SessionQuestion.question_id)
                .join(InterviewSession, SessionQuestion.session_id == InterviewSession.id)
                .where(
                    Question.id == question_id,
                    InterviewSession.user_id == user_id
                )
            )
            question, session = result.first()
            
            if not question:
                raise ValueError("Question not found or access denied")
            
            # Create answer
            answer_data = {
                "id": uuid.uuid4(),
                "question_id": question_id,
                "answer_text": answer_text,
                "analysis_result": analysis_result,
                "score": score,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            answer = await self.db_ops.create(Answer, **answer_data)
            await self.db_session.commit()
            
            logger.info(f"Added answer for question {question_id}")
            return answer
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error adding answer for question {question_id}: {e}")
            return None
    
    async def get_question_answers(
        self,
        question_id: str,
        user_id: str
    ) -> List[Answer]:
        """Get all answers for a question."""
        try:
            # Verify question exists and user has access
            result = await self.db_session.execute(
                select(Question, InterviewSession)
                .join(SessionQuestion, Question.id == SessionQuestion.question_id)
                .join(InterviewSession, SessionQuestion.session_id == InterviewSession.id)
                .where(
                    Question.id == question_id,
                    InterviewSession.user_id == user_id
                )
            )
            question, session = result.first()
            
            if not question:
                return []
            
            # Get answers
            result = await self.db_session.execute(
                select(Answer)
                .where(Answer.question_id == question_id)
                .order_by(Answer.created_at.desc())
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting answers for question {question_id}: {e}")
            return []
    
    async def _find_question_by_text(self, question_text: str) -> Optional[Question]:
        """Find a question by its text."""
        try:
            result = await self.db_session.execute(
                select(Question).where(Question.question_text == question_text)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error finding question by text: {e}")
            return None
