"""
Async Question Bank Service for intelligent question selection and management.

This service provides async database operations for the question bank system,
enabling concurrent question selection and improved performance.
"""
import asyncio
import hashlib
import json
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Question, SessionQuestion, InterviewSession
from app.database.async_connection import get_async_db_connection
from app.utils.logger import get_logger
from app.models.schemas import ParseJDResponse

logger = get_logger(__name__)


class AsyncQuestionBankService:
    """Async service for managing the global question bank and intelligent question selection."""
    
    # Centralized categorization rules (shared with sync service)
    CATEGORIZATION_RULES = {
        "behavioral": [
            "experience", "tell me about", "describe", "situation", "behavioral"
        ],
        "system_design": [
            "system", "architecture", "design", "scale", "distributed"
        ],
        "leadership": [
            "lead", "manage", "team", "mentor", "leadership"
        ],
        "technical": []  # Default category
    }
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
    
    async def get_questions_for_role(self, role: str, job_description: str, count: int = 10) -> List[Question]:
        """
        Get questions for a specific role using intelligent selection algorithms.
        
        Args:
            role: The job role/title
            job_description: The job description text
            count: Number of questions to return
            
        Returns:
            List of selected questions
        """
        try:
            # Define processing pipeline
            pipeline = [
                lambda r, jd: self._analyze_role(r, jd),
                lambda analysis: self._find_compatible_questions(analysis),
                lambda questions: self._ensure_question_diversity(questions, count),
                self._update_usage_stats
            ]
            
            # Execute pipeline
            result = (role, job_description)
            for step in pipeline:
                result = await step(*result) if isinstance(result, tuple) else await step(result)
            
            logger.info(f"Selected {len(result)} questions for role '{role}'")
            return result
            
        except Exception as e:
            logger.error(f"Error selecting questions for role '{role}': {e}")
            return await self._get_fallback_questions(role, count)
    
    async def get_questions_for_role_with_analysis(self, role: str, analysis, count: int = 10) -> List[Question]:
        """
        Get questions for a role using pre-computed role analysis.
        
        Args:
            role: The job role/title
            analysis: Pre-computed role analysis
            count: Number of questions to return
            
        Returns:
            List of selected questions
        """
        try:
            # Find compatible questions with scoring
            compatible_questions = await self._find_compatible_questions(analysis)
            
            # Apply diversity algorithms
            diverse_questions = await self._ensure_question_diversity(compatible_questions, count)
            
            # Update usage statistics
            await self._update_usage_stats(diverse_questions)
            
            logger.info(f"Selected {len(diverse_questions)} questions for role '{role}' with analysis")
            return diverse_questions
            
        except Exception as e:
            logger.error(f"Error selecting questions for role '{role}' with analysis: {e}")
            return await self._get_fallback_questions(role, count)
    
    async def store_questions_for_role_with_analysis(self, role: str, questions: List[str], 
                                                   job_description: str, analysis) -> List[Question]:
        """
        Store AI-generated questions with role analysis metadata.
        
        Args:
            role: The job role
            questions: List of question texts
            job_description: The job description
            analysis: Role analysis result
            
        Returns:
            List of stored Question objects
        """
        try:
            stored_questions = []
            
            for question_text in questions:
                # Check if similar question already exists
                existing_question = await self._find_similar_question(question_text)
                if existing_question:
                    logger.info(f"Similar question already exists, skipping: {question_text[:50]}...")
                    stored_questions.append(existing_question)
                    continue
                
                # Create new question
                question = Question(
                    question_text=question_text,
                    question_metadata=self._create_question_metadata(analysis),
                    difficulty_level=self._determine_difficulty(question_text, analysis),
                    category=self._categorize_question(question_text),
                    subcategory=self._get_subcategory(question_text),
                    compatible_roles=[role],
                    required_skills=analysis.key_skills if hasattr(analysis, 'key_skills') else [],
                    industry_tags=[analysis.industry.value] if hasattr(analysis, 'industry') else [],
                    ai_service_used="dynamic_prompt",
                    generation_prompt_hash=self._generate_prompt_hash(role, job_description)
                )
                
                if self.db_session:
                    self.db_session.add(question)
                    await self.db_session.flush()
                    stored_questions.append(question)
                else:
                    # Use direct database connection
                    async with get_async_db_connection() as conn:
                        # This would need to be implemented with raw SQL
                        # For now, we'll use the session-based approach
                        pass
            
            if self.db_session:
                await self.db_session.commit()
            
            logger.info(f"Stored {len(stored_questions)} new questions with role analysis")
            return stored_questions
            
        except Exception as e:
            logger.error(f"Error storing questions with analysis: {e}")
            if self.db_session:
                await self.db_session.rollback()
            raise
    
    async def _analyze_role(self, role: str, job_description: str) -> Dict[str, Any]:
        """Analyze role requirements using async operations."""
        # This would integrate with the RoleAnalysisService
        # For now, return a basic analysis
        return {
            "primary_role": role,
            "required_skills": ["python", "javascript", "sql"],
            "industry": "technology",
            "seniority_level": "mid",
            "company_size": "medium",
            "tech_stack": ["python", "javascript", "postgresql"]
        }
    
    async def _find_compatible_questions(self, role_analysis: Dict[str, Any]) -> List[Question]:
        """Find compatible questions using async database queries."""
        if not self.db_session:
            return []
        
        try:
            # Build query based on role analysis
            query = select(Question)
            
            # Filter by compatible roles
            if role_analysis.get("primary_role"):
                query = query.where(
                    Question.compatible_roles.contains([role_analysis["primary_role"]])
                )
            
            # Filter by required skills
            if role_analysis.get("required_skills"):
                skill_conditions = [
                    Question.required_skills.contains([skill]) 
                    for skill in role_analysis["required_skills"]
                ]
                query = query.where(or_(*skill_conditions))
            
            # Filter by industry
            if role_analysis.get("industry"):
                query = query.where(
                    Question.industry_tags.contains([role_analysis["industry"]])
                )
            
            # Order by usage count and success rate
            query = query.order_by(
                desc(Question.usage_count),
                desc(Question.success_rate)
            )
            
            result = await self.db_session.execute(query)
            questions = result.scalars().all()
            
            logger.info(f"Found {len(questions)} compatible questions")
            return questions
            
        except Exception as e:
            logger.error(f"Error finding compatible questions: {e}")
            return []
    
    async def _ensure_question_diversity(self, questions: List[Question], count: int) -> List[Question]:
        """Ensure question diversity using async operations."""
        if len(questions) <= count:
            return questions
        
        # Group questions by category and difficulty
        categories = ["technical", "behavioral", "system_design", "leadership"]
        difficulties = ["easy", "medium", "hard"]
        
        selected = []
        for category in categories:
            for difficulty in difficulties:
                category_questions = [
                    q for q in questions 
                    if q.category == category and q.difficulty_level == difficulty
                ]
                if category_questions:
                    selected.append(random.choice(category_questions))
        
        # If we don't have enough diverse questions, fill with remaining
        if len(selected) < count:
            remaining = [q for q in questions if q not in selected]
            selected.extend(remaining[:count - len(selected)])
        
        return selected[:count]
    
    async def _update_usage_stats(self, questions: List[Question]) -> None:
        """Update usage statistics for questions."""
        if not self.db_session or not questions:
            return
        
        try:
            for question in questions:
                question.usage_count = (question.usage_count or 0) + 1
                question.updated_at = datetime.utcnow()
            
            await self.db_session.commit()
            logger.debug(f"Updated usage stats for {len(questions)} questions")
            
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
            await self.db_session.rollback()
    
    async def _find_similar_question(self, question_text: str) -> Optional[Question]:
        """Find similar question using async database query."""
        if not self.db_session:
            return None
        
        try:
            # Simple similarity check based on text length and keywords
            query = select(Question).where(
                and_(
                    func.length(Question.question_text) >= len(question_text) * 0.8,
                    func.length(Question.question_text) <= len(question_text) * 1.2
                )
            )
            
            result = await self.db_session.execute(query)
            questions = result.scalars().all()
            
            # Find most similar question
            for question in questions:
                if self._calculate_similarity(question_text, question.question_text) > 0.8:
                    return question
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding similar question: {e}")
            return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _create_question_metadata(self, role_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create question metadata from role analysis."""
        return {
            "role_analysis": role_analysis,
            "created_at": datetime.utcnow().isoformat(),
            "source": "ai_generated"
        }
    
    def _determine_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> str:
        """Determine question difficulty using functional approach."""
        # Priority-based difficulty determination
        difficulty_determiners = [
            self._get_seniority_difficulty,
            self._get_keyword_difficulty,
            lambda *args: 'medium'  # Default fallback
        ]
        
        for determiner in difficulty_determiners:
            if difficulty := determiner(question_text, role_analysis):
                return difficulty
        
        return 'medium'
    
    def _get_seniority_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Get difficulty based on seniority level."""
        seniority_map = {'senior': 'hard', 'junior': 'easy', 'mid': 'medium'}
        return seniority_map.get(role_analysis.get('seniority_level', 'mid'))
    
    def _get_keyword_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Get difficulty based on keywords."""
        text_lower = question_text.lower()
        keyword_rules = [
            (['complex', 'advanced', 'architecture', 'design', 'optimize'], 'hard'),
            (['basic', 'simple', 'explain', 'what is'], 'easy')
        ]
        
        for keywords, difficulty in keyword_rules:
            if any(word in text_lower for word in keywords):
                return difficulty
        return None
    
    def _categorize_question(self, question_text: str) -> str:
        """Categorize question using centralized rules."""
        return self._categorize_by_keywords(question_text, self.CATEGORIZATION_RULES)
    
    def _categorize_by_keywords(self, text: str, rules: Dict[str, List[str]]) -> str:
        """Categorize text based on keyword rules."""
        text_lower = text.lower()
        
        for category, keywords in rules.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return "technical"  # Default category
    
    def _get_subcategory(self, question_text: str) -> str:
        """Get question subcategory."""
        text_lower = question_text.lower()
        
        subcategory_keywords = {
            "api_design": ["api", "rest", "graphql", "endpoint"],
            "database": ["database", "sql", "query", "table"],
            "algorithms": ["algorithm", "complexity", "sort", "search"],
            "system_design": ["system", "architecture", "scale", "distributed"],
            "teamwork": ["team", "collaborate", "work with", "team member"],
            "leadership": ["lead", "manage", "mentor", "guide"]
        }
        
        for subcategory, keywords in subcategory_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return subcategory
        
        return "general"
    
    def _generate_prompt_hash(self, role: str, job_description: str) -> str:
        """Generate a hash for the prompt to identify similar requests."""
        prompt_data = f"{role}:{job_description}"
        return hashlib.sha256(prompt_data.encode()).hexdigest()
    
    async def _get_fallback_questions(self, role: str, count: int) -> List[Question]:
        """Get fallback questions when no specific questions are found."""
        if not self.db_session:
            return []
        
        try:
            # Get random questions as fallback
            query = select(Question).order_by(func.random()).limit(count)
            result = await self.db_session.execute(query)
            questions = result.scalars().all()
            
            logger.info(f"Using {len(questions)} fallback questions for role '{role}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting fallback questions: {e}")
            return []
    
    async def get_question_bank_stats(self) -> Dict[str, Any]:
        """Get question bank statistics."""
        if not self.db_session:
            return {}
        
        try:
            # Get total questions count
            total_query = select(func.count(Question.id))
            total_result = await self.db_session.execute(total_query)
            total_questions = total_result.scalar()
            
            # Get questions by category
            category_query = select(
                Question.category,
                func.count(Question.id).label('count')
            ).group_by(Question.category)
            category_result = await self.db_session.execute(category_query)
            category_stats = {row.category: row.count for row in category_result}
            
            # Get questions by difficulty
            difficulty_query = select(
                Question.difficulty_level,
                func.count(Question.id).label('count')
            ).group_by(Question.difficulty_level)
            difficulty_result = await self.db_session.execute(difficulty_query)
            difficulty_stats = {row.difficulty_level: row.count for row in difficulty_result}
            
            return {
                "total_questions": total_questions,
                "category_distribution": category_stats,
                "difficulty_distribution": difficulty_stats,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting question bank stats: {e}")
            return {}