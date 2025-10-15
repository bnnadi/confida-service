"""
Async Database Operations for Question Bank and Session Management.

This module provides async database operations for the question bank system,
enabling concurrent operations and improved performance.
"""
import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, update, insert, delete, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models import Question, SessionQuestion, InterviewSession, User, Answer
from app.database.async_connection import get_async_db_connection
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncDatabaseOperations:
    """Async database operations for question bank and session management."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
    
    async def create(self, model_class, **kwargs):
        """Create a new record asynchronously."""
        if self.db_session:
            instance = model_class(**kwargs)
            self.db_session.add(instance)
            await self.db_session.flush()
            return instance
        else:
            # Use direct database connection
            async with get_async_db_connection() as conn:
                # This would need to be implemented with raw SQL
                # For now, we'll use the session-based approach
                pass
    
    async def get_by_id(self, model_class, record_id):
        """Get a record by ID asynchronously."""
        if not self.db_session:
            return None
        
        try:
            query = select(model_class).where(model_class.id == record_id)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {model_class.__name__} by ID {record_id}: {e}")
            return None
    
    async def get_all(self, model_class, limit: int = 100, offset: int = 0):
        """Get all records with pagination."""
        if not self.db_session:
            return []
        
        try:
            query = select(model_class).offset(offset).limit(limit)
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting all {model_class.__name__}: {e}")
            return []
    
    async def update_by_id(self, model_class, record_id: str, **updates):
        """Update a record by ID."""
        if not self.db_session:
            return None
        
        try:
            query = update(model_class).where(model_class.id == record_id).values(**updates)
            await self.db_session.execute(query)
            await self.db_session.commit()
            return await self.get_by_id(model_class, record_id)
        except Exception as e:
            logger.error(f"Error updating {model_class.__name__} {record_id}: {e}")
            await self.db_session.rollback()
            return None
    
    async def delete_by_id(self, model_class, record_id: str):
        """Delete a record by ID."""
        if not self.db_session:
            return False
        
        try:
            query = delete(model_class).where(model_class.id == record_id)
            result = await self.db_session.execute(query)
            await self.db_session.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting {model_class.__name__} {record_id}: {e}")
            await self.db_session.rollback()
            return False
    
    async def find_questions_by_role(self, role: str, limit: int = 10) -> List[Question]:
        """Find questions compatible with a specific role."""
        if not self.db_session:
            return []
        
        try:
            query = select(Question).where(
                Question.compatible_roles.contains([role])
            ).order_by(desc(Question.usage_count)).limit(limit)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding questions for role {role}: {e}")
            return []
    
    async def find_questions_by_skills(self, skills: List[str], limit: int = 10) -> List[Question]:
        """Find questions that require specific skills."""
        if not self.db_session or not skills:
            return []
        
        try:
            skill_conditions = [
                Question.required_skills.contains([skill]) 
                for skill in skills
            ]
            
            query = select(Question).where(
                or_(*skill_conditions)
            ).order_by(desc(Question.usage_count)).limit(limit)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding questions for skills {skills}: {e}")
            return []
    
    async def find_questions_by_category(self, category: str, limit: int = 10) -> List[Question]:
        """Find questions by category."""
        if not self.db_session:
            return []
        
        try:
            query = select(Question).where(
                Question.category == category
            ).order_by(desc(Question.usage_count)).limit(limit)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding questions for category {category}: {e}")
            return []
    
    async def find_questions_by_difficulty(self, difficulty: str, limit: int = 10) -> List[Question]:
        """Find questions by difficulty level."""
        if not self.db_session:
            return []
        
        try:
            query = select(Question).where(
                Question.difficulty_level == difficulty
            ).order_by(desc(Question.usage_count)).limit(limit)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error finding questions for difficulty {difficulty}: {e}")
            return []
    
    async def get_question_statistics(self) -> Dict[str, Any]:
        """Get question bank statistics."""
        if not self.db_session:
            return {}
        
        try:
            # Total questions
            total_query = select(func.count(Question.id))
            total_result = await self.db_session.execute(total_query)
            total_questions = total_result.scalar()
            
            # Questions by category
            category_query = select(
                Question.category,
                func.count(Question.id).label('count')
            ).group_by(Question.category)
            category_result = await self.db_session.execute(category_query)
            category_stats = {row.category: row.count for row in category_result}
            
            # Questions by difficulty
            difficulty_query = select(
                Question.difficulty_level,
                func.count(Question.id).label('count')
            ).group_by(Question.difficulty_level)
            difficulty_result = await self.db_session.execute(difficulty_query)
            difficulty_stats = {row.difficulty_level: row.count for row in difficulty_result}
            
            # Most used questions
            popular_query = select(Question).order_by(desc(Question.usage_count)).limit(5)
            popular_result = await self.db_session.execute(popular_query)
            popular_questions = popular_result.scalars().all()
            
            return {
                "total_questions": total_questions,
                "category_distribution": category_stats,
                "difficulty_distribution": difficulty_stats,
                "popular_questions": [
                    {
                        "id": str(q.id),
                        "question_text": q.question_text[:100] + "..." if len(q.question_text) > 100 else q.question_text,
                        "usage_count": q.usage_count,
                        "category": q.category
                    }
                    for q in popular_questions
                ],
                "last_updated": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting question statistics: {e}")
            return {}
    
    async def update_question_usage(self, question_id: str, score: Optional[float] = None):
        """Update question usage statistics."""
        if not self.db_session:
            return False
        
        try:
            # Get current question
            question = await self.get_by_id(Question, question_id)
            if not question:
                return False
            
            # Update usage count
            question.usage_count = (question.usage_count or 0) + 1
            
            # Update performance metrics if score provided
            if score is not None:
                if question.average_score is None:
                    question.average_score = score
                else:
                    # Update running average
                    question.average_score = (question.average_score * (question.usage_count - 1) + score) / question.usage_count
                
                # Update success rate (assuming score > 0.7 is success)
                success = score > 0.7
                if question.success_rate is None:
                    question.success_rate = 1.0 if success else 0.0
                else:
                    total_successes = question.success_rate * (question.usage_count - 1)
                    if success:
                        total_successes += 1
                    question.success_rate = total_successes / question.usage_count
            
            question.updated_at = datetime.utcnow()
            await self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating question usage for {question_id}: {e}")
            await self.db_session.rollback()
            return False
    
    async def create_session_with_questions(self, user_id: str, role: str, 
                                          job_description: str, questions: List[str]) -> Tuple[InterviewSession, List[SessionQuestion]]:
        """Create a session with questions atomically."""
        if not self.db_session:
            raise Exception("Database session not available")
        
        try:
            # Create session
            session_data = {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "role": role,
                "job_description": job_description,
                "title": f"Interview for {role}",
                "status": "active",
                "total_questions": len(questions),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            session = await self.create(InterviewSession, **session_data)
            
            # Create session questions
            session_questions = []
            for i, question_text in enumerate(questions):
                # Find or create question
                existing_question = await self._find_question_by_text(question_text)
                
                if existing_question:
                    question_id = existing_question.id
                    # Update usage count
                    await self.update_question_usage(str(question_id))
                else:
                    # Create new question
                    question_data = {
                        "id": uuid.uuid4(),
                        "question_text": question_text,
                        "question_metadata": {
                            "created_from_session": str(session.id),
                            "created_at": datetime.utcnow().isoformat()
                        },
                        "difficulty_level": "medium",
                        "category": "general",
                        "usage_count": 1,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    new_question = await self.create(Question, **question_data)
                    question_id = new_question.id
                
                # Create session question relationship
                session_question_data = {
                    "id": uuid.uuid4(),
                    "session_id": session.id,
                    "question_id": question_id,
                    "question_order": i + 1,
                    "created_at": datetime.utcnow()
                }
                session_question = await self.create(SessionQuestion, **session_question_data)
                session_questions.append(session_question)
            
            await self.db_session.commit()
            logger.info(f"Successfully created session {session.id} with {len(session_questions)} questions")
            return session, session_questions
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error creating session with questions: {e}")
            raise
    
    async def _find_question_by_text(self, question_text: str) -> Optional[Question]:
        """Find a question by its text."""
        if not self.db_session:
            return None
        
        try:
            query = select(Question).where(Question.question_text == question_text)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error finding question by text: {e}")
            return None
    
    async def get_user_sessions(self, user_id: str, limit: int = 20) -> List[InterviewSession]:
        """Get user's interview sessions."""
        if not self.db_session:
            return []
        
        try:
            query = select(InterviewSession).where(
                InterviewSession.user_id == user_id
            ).order_by(desc(InterviewSession.created_at)).limit(limit)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting sessions for user {user_id}: {e}")
            return []
    
    async def get_session_questions(self, session_id: str) -> List[SessionQuestion]:
        """Get questions for a specific session."""
        if not self.db_session:
            return []
        
        try:
            query = select(SessionQuestion).where(
                SessionQuestion.session_id == session_id
            ).order_by(SessionQuestion.question_order)
            
            result = await self.db_session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting questions for session {session_id}: {e}")
            return []
    
    async def commit(self):
        """Commit the current transaction."""
        if self.db_session:
            await self.db_session.commit()
    
    async def rollback(self):
        """Rollback the current transaction."""
        if self.db_session:
            await self.db_session.rollback()