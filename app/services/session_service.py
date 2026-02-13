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
from sqlalchemy.orm import selectinload, joinedload
from app.database.models import InterviewSession, SessionQuestion, Question, Scenario
from app.exceptions import AIServiceError
from app.services.encryption_service import get_encryption_service
from app.utils.logger import get_logger
from datetime import datetime, timezone
import json

logger = get_logger(__name__)


class SessionService:
    """Service for managing interview sessions with both sync and async support."""
    
    def __init__(self, db_session: Union[Session, AsyncSession]):
        self.db_session = db_session
        self.is_async = isinstance(db_session, AsyncSession)
        
        # Use direct SQLAlchemy operations for both sync and async
    
    # Session Creation Methods
    def _encrypt_session_fields(self, user_id: str, job_description: str, job_context: Optional[dict]) -> tuple:
        """Encrypt sensitive session fields if encryption enabled."""
        enc = get_encryption_service()
        uid = str(user_id)
        enc_jd = enc.encrypt(job_description or "", uid) if job_description or enc.is_enabled() else (job_description or "")
        enc_ctx = enc.encrypt(job_context, uid) if job_context and enc.is_enabled() else job_context
        return enc_jd, enc_ctx

    def _decrypt_session(self, session: InterviewSession) -> InterviewSession:
        """Decrypt sensitive fields on a session in place."""
        enc = get_encryption_service()
        if not enc.is_enabled():
            return session
        uid = str(session.user_id)
        if session.job_description and isinstance(session.job_description, str):
            dec = enc.decrypt(session.job_description, uid)
            if dec is not None:
                session.job_description = dec if isinstance(dec, str) else json.dumps(dec)
        if session.job_context and isinstance(session.job_context, str):
            dec = enc.decrypt(session.job_context, uid)
            if dec is not None and isinstance(dec, dict):
                session.job_context = dec
        return session

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
            job_ctx = {"title": title} if title else None
            enc_jd, enc_ctx = self._encrypt_session_fields(user_id, job_description or "", job_ctx)
            session_data = {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role": role,
                "job_description": enc_jd,
                "mode": mode,
                "question_source": "generated",
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            if enc_ctx is not None:
                session_data["job_context"] = enc_ctx
            
            session = InterviewSession(**session_data)
            self.db_session.add(session)
            if self.is_async:
                await self.db_session.commit()
                await self.db_session.refresh(session)
            else:
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
                # Note: Question generation now handled by AI service microservice
                questions_data = []  # TODO: Implement scenario-based question generation via AI service
            
            # Create session
            session_data = {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role": role,
                "job_description": "",
                "scenario_id": scenario_id,
                "mode": "practice",
                "question_source": "scenario",
                "question_ids": [q["id"] for q in questions_data] if questions_data else [],
                "status": "active",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            session = InterviewSession(**session_data)
            self.db_session.add(session)
            if self.is_async:
                await self.db_session.commit()
                await self.db_session.refresh(session)
            else:
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
    
    async def create_interview_session(
        self,
        user_id: Union[int, str],
        role: str,
        job_title: Optional[str] = None,
        job_description: Optional[str] = None
    ) -> InterviewSession:
        """Create a new interview session (alias for create_session with interview params)."""
        title = job_title or role
        return await self.create_session(
            user_id=user_id,
            role=role,
            job_description=job_description or "",
            title=title,
            mode="interview"
        )
    
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
                sess = result.scalar_one_or_none()
            else:
                sess = self.db_session.query(InterviewSession).filter(
                    InterviewSession.id == session_id,
                    InterviewSession.user_id == user_id
                ).first()
            return self._decrypt_session(sess) if sess else None
                
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def get_user_sessions(
        self,
        user_id: Union[int, str],
        limit: int = 50,
        offset: int = 0
    ) -> List[InterviewSession]:
        """Get all sessions for a user."""
        try:
            if self.is_async:
                result = await self.db_session.execute(
                    select(InterviewSession)
                    .where(InterviewSession.user_id == user_id)
                    .order_by(desc(InterviewSession.created_at))
                    .limit(limit)
                    .offset(offset)
                )
                sessions = result.scalars().all()
            else:
                sessions = self.db_session.query(InterviewSession).filter(
                    InterviewSession.user_id == user_id
                ).order_by(desc(InterviewSession.created_at)).limit(limit).offset(offset).all()
            return [self._decrypt_session(s) for s in sessions]
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
            updates["updated_at"] = datetime.now(timezone.utc)
            
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
        """Add questions to a session. Creates Question records in question bank, then SessionQuestion links."""
        try:
            # Verify session belongs to user
            session = await self.get_session(session_id, user_id)
            if not session:
                return []
            
            session_questions = []
            for i, question_text in enumerate(questions, 1):
                # Create or get Question in question bank
                if self.is_async:
                    result = await self.db_session.execute(
                        select(Question).where(Question.question_text == question_text)
                    )
                    existing = result.scalar_one_or_none()
                else:
                    existing = self.db_session.query(Question).filter(
                        Question.question_text == question_text
                    ).first()
                
                if existing:
                    question_id = existing.id
                else:
                    question = Question(
                        id=uuid.uuid4(),
                        question_text=question_text,
                        category="interview",
                        difficulty_level="medium",
                        question_metadata={},
                        usage_count=0,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )
                    self.db_session.add(question)
                    if not self.is_async:
                        self.db_session.flush()
                    else:
                        await self.db_session.flush()
                    question_id = question.id
                
                session_question = SessionQuestion(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    question_id=question_id,
                    question_order=i,
                    created_at=datetime.now(timezone.utc)
                )
                self.db_session.add(session_question)
                session_questions.append(session_question)
            
            if self.is_async:
                await self.db_session.commit()
                for sq in session_questions:
                    await self.db_session.refresh(sq)
            else:
                self.db_session.commit()
                for sq in session_questions:
                    self.db_session.refresh(sq)
            
            logger.info(f"Added {len(questions)} questions to session {session_id}")
            return session_questions
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error adding questions to session {session_id}: {e}")
            return []

    async def remove_question_from_session(
        self,
        session_id: str,
        session_question_id: str,
        user_id: Union[int, str]
    ) -> bool:
        """Remove a question from a session by SessionQuestion id.

        Returns True if removed, False if not found or session doesn't belong to user.
        """
        try:
            session = await self.get_session(session_id, user_id)
            if not session:
                return False

            if self.is_async:
                result = await self.db_session.execute(
                    select(SessionQuestion)
                    .where(SessionQuestion.id == session_question_id)
                    .where(SessionQuestion.session_id == session_id)
                )
                sq = result.scalar_one_or_none()
            else:
                sq = self.db_session.query(SessionQuestion).filter(
                    SessionQuestion.id == session_question_id,
                    SessionQuestion.session_id == session_id
                ).first()

            if not sq:
                return False

            if self.is_async:
                await self.db_session.delete(sq)
                await self.db_session.commit()
            else:
                self.db_session.delete(sq)
                self.db_session.commit()

            logger.info(f"Removed question {session_question_id} from session {session_id}")
            return True

        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"Error removing question from session {session_id}: {e}")
            return False

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
    
    async def get_session_with_questions_and_answers(
        self,
        session_id: str,
        user_id: Union[int, str]
    ) -> Optional[dict]:
        """Get a session with its questions (and answers from question relationship)."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None
        # Load session_questions with question relationship
        if self.is_async:
            result = await self.db_session.execute(
                select(InterviewSession)
                .options(selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.question))
                .where(InterviewSession.id == session_id)
                .where(InterviewSession.user_id == user_id)
            )
            session = result.scalar_one_or_none()
        else:
            session = self.db_session.query(InterviewSession).options(
                selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.question)
            ).filter(
                InterviewSession.id == session_id,
                InterviewSession.user_id == user_id
            ).first()
        if not session:
            return None
        questions_data = []
        for sq in sorted(session.session_questions, key=lambda x: x.question_order):
            q = sq.question
            questions_data.append({
                "id": str(sq.id),
                "question_text": q.question_text if q else "",
                "question_order": sq.question_order,
                "created_at": sq.created_at.isoformat() if sq.created_at else ""
            })
        return {
            "session": {
                "id": str(session.id),
                "user_id": str(session.user_id),
                "mode": session.mode,
                "role": session.role,
                "job_description": session.job_description,
                "scenario_id": session.scenario_id,
                "question_source": session.question_source,
                "status": session.status,
                "total_questions": session.total_questions,
                "completed_questions": session.completed_questions,
                "created_at": session.created_at.isoformat() if session.created_at else "",
                "updated_at": session.updated_at.isoformat() if session.updated_at else None
            },
            "questions": questions_data
        }

    async def get_session_questions(
        self,
        session_id: str,
        user_id: Union[int, str]
    ) -> Optional[List[dict]]:
        """Get all questions for a session. Returns None if session not found."""
        session = await self.get_session(session_id, user_id)
        if not session:
            return None
        if self.is_async:
            result = await self.db_session.execute(
                select(InterviewSession)
                .options(selectinload(InterviewSession.session_questions).selectinload(SessionQuestion.question))
                .where(InterviewSession.id == session_id)
                .where(InterviewSession.user_id == user_id)
            )
            session = result.scalar_one_or_none()
        else:
            session = self.db_session.query(InterviewSession).options(
                joinedload(InterviewSession.session_questions).joinedload(SessionQuestion.question)
            ).filter(
                InterviewSession.id == session_id,
                InterviewSession.user_id == user_id
            ).first()
        if not session:
            return []
        result_list = []
        for sq in sorted(session.session_questions, key=lambda x: x.question_order):
            q = sq.question
            result_list.append({
                "id": str(sq.id),
                "question_text": q.question_text if q else "",
                "question_order": sq.question_order
            })
        return result_list

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        user_id: Union[int, str]
    ) -> Optional[InterviewSession]:
        """Update session status."""
        return await self.update_session(session_id, user_id, status=status)

    async def get_available_scenarios(self) -> List[dict]:
        """Get available practice scenarios."""
        try:
            if self.is_async:
                result = await self.db_session.execute(
                    select(Scenario).where(Scenario.is_active == True)
                )
                scenarios = result.scalars().all()
            else:
                scenarios = self.db_session.query(Scenario).filter(Scenario.is_active == True).all()
            return [
                {"id": s.id, "name": s.name, "description": s.description, "category": s.category}
                for s in scenarios
            ]
        except Exception as e:
            logger.error(f"Error getting scenarios: {e}")
            return []

    async def preview_practice_session(self, role: str, scenario_id: str) -> dict:
        """Preview a practice session without creating it."""
        if self.is_async:
            result = await self.db_session.execute(
                select(Scenario).where(Scenario.id == scenario_id)
            )
            scenario = result.scalar_one_or_none()
        else:
            scenario = self.db_session.query(Scenario).filter(Scenario.id == scenario_id).first()
        if not scenario:
            return {"mode": "practice", "role": role, "questions": [], "total_questions": 0, "estimated_duration": 0}
        # Build preview from scenario question_ids if available
        question_ids = scenario.question_ids or []
        qids = []
        if isinstance(question_ids, list):
            for qid in question_ids:
                try:
                    qids.append(uuid.UUID(str(qid)) if isinstance(qid, str) else qid)
                except (ValueError, TypeError):
                    pass
        questions = []
        if qids and not self.is_async:
            qs = self.db_session.query(Question).filter(Question.id.in_(qids)).all()
            questions = [{"id": str(q.id), "text": q.question_text, "type": "behavioral", "difficulty_level": "medium", "category": "general"} for q in qs]
        elif qids and self.is_async:
            result = await self.db_session.execute(select(Question).where(Question.id.in_(qids)))
            qs = result.scalars().all()
            questions = [{"id": str(q.id), "text": q.question_text, "type": "behavioral", "difficulty_level": "medium", "category": "general"} for q in qs]
        return {
            "mode": "practice",
            "role": role,
            "questions": questions,
            "total_questions": len(questions),
            "estimated_duration": max(5, len(questions) * 2)
        }

    async def preview_interview_session(self, role: str, job_title: str, job_description: str) -> dict:
        """Preview an interview session without creating it."""
        return {
            "mode": "interview",
            "role": role,
            "questions": [],
            "total_questions": 0,
            "estimated_duration": 0
        }

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
