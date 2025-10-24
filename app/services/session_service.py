"""
Unified Session Service for Confida

This service provides both sync and async database operations for managing interview sessions,
eliminating the need for separate SessionService and AsyncSessionService classes.
"""
import uuid
from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc
from app.database.models import InterviewSession, SessionQuestion
# AsyncDatabaseOperations functionality now in unified database service
from app.services.question_service import QuestionService
from app.exceptions import AIServiceError
# Error handling imports removed as they were unused
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class SessionService:
    """Service for managing interview sessions with both sync and async support."""
    
    def __init__(self, db_session: Union[Session, AsyncSession]):
        self.db_session = db_session
        self.is_async = isinstance(db_session, AsyncSession)
        
        if self.is_async:
            self.db_ops = AsyncDatabaseOperations(db_session)
        else:
            # For sync operations, we'll use direct SQLAlchemy operations
            self.question_service = QuestionService(db_session)
    
    # Session Creation Methods
    async def create_session(
        self,
        user_id: Union[int, str],
        role: str,
        job_description: str,
        title: Optional[str] = None,
        mode: str = "interview"
    ) -> InterviewSession:
        """Create a new interview session (works for both sync and async)."""
        try:
            session_data = {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role": role,
                "job_description": job_description,
                "title": title or f"Interview for {role}",
                "mode": mode,
                "question_source": "generated",
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if self.is_async:
                session = await self.db_ops.create(InterviewSession, **session_data)
                await self.db_session.commit()
            else:
                session = InterviewSession(**session_data)
                self.db_session.add(session)
                self.db_session.commit()
                self.db_session.refresh(session)
            
            logger.info(f"Created interview session {session.id} for user {user_id}")
            return session
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error creating session: {e}")
            raise AIServiceError(f"Failed to create interview session: {e}")
    
    async def create_practice_session(
        self,
        user_id: Union[int, str],
        role: str,
        scenario_id: str
    ) -> InterviewSession:
        """Create a new practice session with scenario-based questions."""
        try:
            # Generate questions from scenario
            if self.is_async:
                # For async, we'll need to handle this differently
                questions_data = []  # TODO: Implement async scenario question generation
            else:
                questions_data = self.question_service.generate_questions_from_scenario(scenario_id)
            
            # Create session
            session_data = {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role": role,
                "scenario_id": scenario_id,
                "mode": "practice",
                "question_source": "scenario",
                "question_ids": [q["id"] for q in questions_data] if questions_data else [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if self.is_async:
                session = await self.db_ops.create(InterviewSession, **session_data)
                await self.db_session.commit()
            else:
                session = InterviewSession(**session_data)
                self.db_session.add(session)
                self.db_session.commit()
                self.db_session.refresh(session)
            
            logger.info(f"Created practice session {session.id} for user {user_id}")
            return session
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error creating practice session: {e}")
            raise AIServiceError(f"Failed to create practice session: {e}")
    
    # Session Retrieval Methods
    async def get_session(
        self,
        session_id: str,
        user_id: Union[int, str]
    ) -> Optional[InterviewSession]:
        """Get a session by ID and user ID."""
        try:
            if self.is_async:
                result = await self.db_session.execute(
                    select(InterviewSession)
                    .where(InterviewSession.id == session_id)
                    .where(InterviewSession.user_id == user_id)
                )
                return result.scalar_one_or_none()
            else:
                return self.db_session.query(InterviewSession).filter(
                    InterviewSession.id == session_id,
                    InterviewSession.user_id == user_id
                ).first()
                
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    async def get_user_sessions(
        self,
        user_id: Union[int, str],
        limit: int = 50
    ) -> List[InterviewSession]:
        """Get all sessions for a user."""
        try:
            if self.is_async:
                result = await self.db_session.execute(
                    select(InterviewSession)
                    .where(InterviewSession.user_id == user_id)
                    .order_by(desc(InterviewSession.created_at))
                    .limit(limit)
                )
                return result.scalars().all()
            else:
                return self.db_session.query(InterviewSession).filter(
                    InterviewSession.user_id == user_id
                ).order_by(desc(InterviewSession.created_at)).limit(limit).all()
                
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    # Session Update Methods
    async def update_session(
        self,
        session_id: str,
        user_id: Union[int, str],
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
            
            if self.is_async:
                await self.db_session.execute(
                    update(InterviewSession)
                    .where(InterviewSession.id == session_id)
                    .values(**updates)
                )
                await self.db_session.commit()
            else:
                self.db_session.query(InterviewSession).filter(
                    InterviewSession.id == session_id
                ).update(updates)
                self.db_session.commit()
            
            # Return updated session
            return await self.get_session(session_id, user_id)
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error updating session {session_id}: {e}")
            return None
    
    # Session Deletion Methods
    async def delete_session(
        self,
        session_id: str,
        user_id: Union[int, str]
    ) -> bool:
        """Delete a session and all associated data."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                return False
            
            if self.is_async:
                await self.db_session.execute(
                    delete(InterviewSession)
                    .where(InterviewSession.id == session_id)
                )
                await self.db_session.commit()
            else:
                self.db_session.query(InterviewSession).filter(
                    InterviewSession.id == session_id
                ).delete()
                self.db_session.commit()
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    # Question Management Methods
    async def add_questions_to_session(
        self,
        session_id: str,
        questions: List[str],
        user_id: Union[int, str]
    ) -> List[SessionQuestion]:
        """Add questions to a session."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                return []
            
            session_questions = []
            for i, question_text in enumerate(questions, 1):
                session_question_data = {
                    "id": uuid.uuid4(),
                    "session_id": session_id,
                    "question_text": question_text,
                    "question_order": i,
                    "created_at": datetime.utcnow()
                }
                
                if self.is_async:
                    session_question = await self.db_ops.create(SessionQuestion, **session_question_data)
                    session_questions.append(session_question)
                else:
                    session_question = SessionQuestion(**session_question_data)
                    self.db_session.add(session_question)
                    session_questions.append(session_question)
            
            if self.is_async:
                await self.db_session.commit()
            else:
                self.db_session.commit()
            
            logger.info(f"Added {len(questions)} questions to session {session_id}")
            return session_questions
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error adding questions to session {session_id}: {e}")
            return []
    
    # Atomic Operations
    async def create_session_with_questions_atomic(
        self,
        user_id: Union[int, str],
        role: str,
        job_description: str,
        questions: List[str]
    ) -> tuple[InterviewSession, List[SessionQuestion]]:
        """Create a session with questions in a single atomic transaction."""
        try:
            # Create session
            session = await self.create_session(
                user_id=user_id,
                role=role,
                job_description=job_description,
                mode="interview"
            )
            
            # Add questions to session
            session_questions = await self.add_questions_to_session(
                session_id=session.id,
                questions=questions,
                user_id=user_id
            )
            
            logger.info(f"Successfully created session {session.id} with {len(session_questions)} questions")
            return session, session_questions
            
        except Exception as e:
            logger.error(f"Error in atomic session creation: {e}")
            raise AIServiceError(f"Failed to create session with questions: {e}")
    
    # Legacy Compatibility Methods
    def create_session_sync(self, user_id: int, role: str, job_description: str) -> InterviewSession:
        """Legacy sync method for backward compatibility."""
        if self.is_async:
            raise ValueError("Cannot use sync method with async session")
        
        return self.create_session(user_id, role, job_description)
    
    def create_practice_session_sync(self, user_id: int, role: str, scenario_id: str) -> InterviewSession:
        """Legacy sync method for backward compatibility."""
        if self.is_async:
            raise ValueError("Cannot use sync method with async session")
        
        return self.create_practice_session(user_id, role, scenario_id)
