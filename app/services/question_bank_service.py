"""
Question Bank Service

Provides CRUD operations and analytics for the question bank.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.database.models import Question, SessionQuestion, Answer
from app.models.question_requests import (
    QuestionCreateRequest, QuestionUpdateRequest, QuestionFilters
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QuestionBankService:
    """Service for managing question bank operations."""
    
    def __init__(self, db: Session):
        """
        Initialize QuestionBankService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_question(self, question_data: QuestionCreateRequest) -> Question:
        """
        Create a new question in the question bank.
        
        Args:
            question_data: Question creation data
            
        Returns:
            Created Question object
        """
        try:
            # Check for duplicate question text
            existing = self.db.execute(
                select(Question).where(Question.question_text == question_data.question_text)
            ).scalar_one_or_none()
            
            if existing:
                raise ValueError(f"Question with this text already exists: {existing.id}")
            
            # Create new question
            question = Question(
                question_text=question_data.question_text,
                category=question_data.category,
                subcategory=question_data.subcategory,
                difficulty_level=question_data.difficulty_level,
                compatible_roles=question_data.compatible_roles or [],
                required_skills=question_data.required_skills or [],
                industry_tags=question_data.industry_tags or [],
                question_metadata=question_data.question_metadata or {}
            )
            
            self.db.add(question)
            self.db.flush()
            self.db.refresh(question)
            
            logger.info(f"Created question: {question.id}")
            return question
            
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            self.db.rollback()
            raise
    
    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """
        Get a question by ID.
        
        Args:
            question_id: Question UUID string
            
        Returns:
            Question object or None if not found
        """
        try:
            question_uuid = UUID(question_id)
            result = self.db.execute(
                select(Question).where(Question.id == question_uuid)
            )
            return result.scalar_one_or_none()
        except ValueError:
            logger.warning(f"Invalid question ID format: {question_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting question by ID: {e}")
            return None
    
    def get_questions(
        self,
        category: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        compatible_roles: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[QuestionFilters] = None
    ) -> List[Question]:
        """
        Get questions with filtering and pagination.
        
        Args:
            category: Filter by category
            difficulty_level: Filter by difficulty level
            compatible_roles: Filter by compatible roles
            limit: Maximum number of results
            offset: Number of results to skip
            filters: Additional filter criteria
            
        Returns:
            List of Question objects
        """
        try:
            query = select(Question)
            conditions = []
            
            # Apply filters
            if category or (filters and filters.category):
                cat = category or (filters.category if filters else None)
                conditions.append(Question.category == cat)
            
            if difficulty_level or (filters and filters.difficulty_level):
                diff = difficulty_level or (filters.difficulty_level if filters else None)
                conditions.append(Question.difficulty_level == diff)
            
            if compatible_roles or (filters and filters.compatible_roles):
                roles = compatible_roles or (filters.compatible_roles if filters else None)
                if roles:
                    # JSONB contains query
                    role_conditions = [Question.compatible_roles.contains([role]) for role in roles]
                    conditions.append(or_(*role_conditions))
            
            if filters:
                if filters.required_skills:
                    skill_conditions = [Question.required_skills.contains([skill]) for skill in filters.required_skills]
                    conditions.append(or_(*skill_conditions))
                
                if filters.industry_tags:
                    tag_conditions = [Question.industry_tags.contains([tag]) for tag in filters.industry_tags]
                    conditions.append(or_(*tag_conditions))
                
                if filters.min_usage_count is not None:
                    conditions.append(Question.usage_count >= filters.min_usage_count)
                
                if filters.min_success_rate is not None:
                    conditions.append(Question.success_rate >= filters.min_success_rate)
                
                if filters.min_average_score is not None:
                    conditions.append(Question.average_score >= filters.min_average_score)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order and paginate
            query = query.order_by(desc(Question.created_at)).limit(limit).offset(offset)
            
            result = self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting questions: {e}")
            return []
    
    def search_questions(
        self,
        query_text: str,
        filters: Optional[QuestionFilters] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Question]:
        """
        Search questions with text search and filtering.
        
        Args:
            query_text: Text to search for
            filters: Additional filter criteria
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching Question objects
        """
        try:
            query = select(Question).where(
                Question.question_text.ilike(f"%{query_text}%")
            )
            
            # Apply additional filters
            conditions = []
            if filters:
                if filters.category:
                    conditions.append(Question.category == filters.category)
                if filters.difficulty_level:
                    conditions.append(Question.difficulty_level == filters.difficulty_level)
                if filters.compatible_roles:
                    role_conditions = [Question.compatible_roles.contains([role]) for role in filters.compatible_roles]
                    conditions.append(or_(*role_conditions))
                if filters.required_skills:
                    skill_conditions = [Question.required_skills.contains([skill]) for skill in filters.required_skills]
                    conditions.append(or_(*skill_conditions))
                if filters.min_usage_count is not None:
                    conditions.append(Question.usage_count >= filters.min_usage_count)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(desc(Question.usage_count)).limit(limit).offset(offset)
            
            result = self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error searching questions: {e}")
            return []
    
    def update_question(
        self,
        question_id: str,
        question_data: QuestionUpdateRequest
    ) -> Optional[Question]:
        """
        Update an existing question.
        
        Args:
            question_id: Question UUID string
            question_data: Update data
            
        Returns:
            Updated Question object or None if not found
        """
        try:
            question = self.get_question_by_id(question_id)
            if not question:
                return None
            
            # Update fields
            if question_data.question_text is not None:
                question.question_text = question_data.question_text
            if question_data.category is not None:
                question.category = question_data.category
            if question_data.subcategory is not None:
                question.subcategory = question_data.subcategory
            if question_data.difficulty_level is not None:
                question.difficulty_level = question_data.difficulty_level
            if question_data.compatible_roles is not None:
                question.compatible_roles = question_data.compatible_roles
            if question_data.required_skills is not None:
                question.required_skills = question_data.required_skills
            if question_data.industry_tags is not None:
                question.industry_tags = question_data.industry_tags
            if question_data.question_metadata is not None:
                question.question_metadata = question_data.question_metadata
            
            self.db.flush()
            self.db.refresh(question)
            
            logger.info(f"Updated question: {question.id}")
            return question
            
        except Exception as e:
            logger.error(f"Error updating question: {e}")
            self.db.rollback()
            return None
    
    def delete_question(self, question_id: str) -> bool:
        """
        Delete a question from the question bank.
        
        Args:
            question_id: Question UUID string
            
        Returns:
            True if deleted, False if not found
        """
        try:
            question = self.get_question_by_id(question_id)
            if not question:
                return False
            
            # Check if question is linked to any sessions
            linked_sessions = self.db.execute(
                select(func.count(SessionQuestion.id)).where(
                    SessionQuestion.question_id == question.id
                )
            ).scalar()
            
            if linked_sessions > 0:
                raise ValueError(f"Cannot delete question {question_id}: it is linked to {linked_sessions} session(s)")
            
            self.db.delete(question)
            self.db.flush()
            
            logger.info(f"Deleted question: {question_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            self.db.rollback()
            raise
    
    def get_question_suggestions(
        self,
        role: str,
        job_description: str,
        limit: int = 10
    ) -> List[Question]:
        """
        Get question suggestions for a specific role and job description.
        
        Args:
            role: Job role
            job_description: Job description text
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested Question objects
        """
        try:
            # Search for questions matching the role
            role_lower = role.lower()
            query = select(Question).where(
                or_(
                    Question.compatible_roles.contains([role]),
                    Question.compatible_roles.contains([role_lower]),
                    Question.category.ilike(f"%{role_lower}%")
                )
            ).order_by(
                desc(Question.usage_count),
                desc(Question.success_rate)
            ).limit(limit)
            
            result = self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting question suggestions: {e}")
            return []
    
    def bulk_import_questions(
        self,
        questions_data: List[QuestionCreateRequest]
    ) -> Dict[str, Any]:
        """
        Bulk import questions.
        
        Args:
            questions_data: List of question creation data
            
        Returns:
            Dictionary with import results
        """
        imported = 0
        failed = 0
        errors = []
        
        for q_data in questions_data:
            try:
                self.create_question(q_data)
                imported += 1
            except Exception as e:
                failed += 1
                errors.append(f"Failed to import question '{q_data.question_text[:50]}...': {str(e)}")
        
        self.db.commit()
        
        return {
            "imported": imported,
            "failed": failed,
            "errors": errors
        }
    
    def bulk_update_questions(
        self,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Bulk update questions.
        
        Args:
            updates: List of update dictionaries with question_id and update data
            
        Returns:
            Dictionary with update results
        """
        updated = 0
        failed = 0
        errors = []
        
        for update_data in updates:
            try:
                question_id = update_data.pop("question_id")
                update_request = QuestionUpdateRequest(**update_data)
                result = self.update_question(question_id, update_request)
                if result:
                    updated += 1
                else:
                    failed += 1
                    errors.append(f"Question {question_id} not found")
            except Exception as e:
                failed += 1
                errors.append(f"Failed to update question: {str(e)}")
        
        self.db.commit()
        
        return {
            "updated": updated,
            "failed": failed,
            "errors": errors
        }

