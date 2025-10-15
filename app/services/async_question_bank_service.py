"""
Async Question Bank Service.

This service provides async database operations for managing the global question bank,
including intelligent question selection, storage, and statistics.
"""
import hashlib
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from app.database.models import Question, SessionQuestion
from app.database.async_operations import AsyncDatabaseOperations
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

class AsyncQuestionBankService:
    """Async service for managing the global question bank."""
    
    # Centralized categorization rules
    CATEGORIZATION_RULES = {
        "technical": [
            "code", "programming", "algorithm", "data structure", "framework", "library",
            "database", "api", "debug", "optimize", "performance", "architecture"
        ],
        "behavioral": [
            "experience", "situation", "challenge", "conflict", "team", "leadership",
            "decision", "mistake", "learn", "improve", "motivate", "handle"
        ],
        "system_design": [
            "design", "system", "scale", "distributed", "microservice", "architecture",
            "load balancer", "cache", "database design", "high availability"
        ]
    }
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.db_ops = AsyncDatabaseOperations(db_session)
    
    async def get_questions_for_role(
        self, 
        role: str, 
        job_description: str, 
        count: int = 10
    ) -> List[Question]:
        """
        Get questions from the question bank for a specific role.
        Uses intelligent selection based on role, job description, and question quality.
        """
        try:
            # Extract keywords from role and job description
            keywords = self._extract_keywords_from_role_and_jd(role, job_description)
            
            # Build query with intelligent filtering
            query = select(Question).where(
                and_(
                    # Filter by compatible roles or general questions
                    or_(
                        Question.compatible_roles.contains([role.lower()]),
                        Question.compatible_roles.is_(None),
                        Question.compatible_roles == []
                    ),
                    # Filter by required skills if specified
                    or_(
                        Question.required_skills.overlap(keywords),
                        Question.required_skills.is_(None),
                        Question.required_skills == []
                    )
                )
            )
            
            # Order by quality metrics (usage count, average score, success rate)
            query = query.order_by(
                desc(Question.success_rate),
                desc(Question.average_score),
                asc(Question.usage_count)  # Prefer less used questions
            )
            
            # Limit results
            query = query.limit(count)
            
            result = await self.db_session.execute(query)
            questions = result.scalars().all()
            
            # Update usage count for selected questions
            if questions:
                question_ids = [q.id for q in questions]
                await self._increment_usage_count(question_ids)
            
            logger.info(f"Retrieved {len(questions)} questions from question bank for role '{role}'")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions for role '{role}': {e}")
            raise
    
    async def store_generated_questions(
        self,
        questions: List[str],
        role: str,
        job_description: str,
        ai_service_used: str,
        prompt_hash: str
    ) -> List[Question]:
        """
        Store AI-generated questions in the question bank.
        Avoids duplicates and enriches with metadata.
        """
        try:
            stored_questions = []
            
            for question_text in questions:
                # Check if question already exists
                existing_question = await self._find_existing_question(question_text, prompt_hash)
                
                if existing_question:
                    # Update usage count for existing question
                    existing_question.usage_count += 1
                    existing_question.updated_at = datetime.utcnow()
                    stored_questions.append(existing_question)
                else:
                    # Create new question
                    question_data = {
                        "question_text": question_text,
                        "question_metadata": {
                            "role": role,
                            "job_description": job_description,
                            "generated_at": datetime.utcnow().isoformat()
                        },
                        "difficulty_level": self._determine_difficulty(question_text, role, job_description),
                        "category": self._determine_category(question_text, role, job_description),
                        "subcategory": self._determine_subcategory(question_text, role, job_description),
                        "compatible_roles": [role.lower()],
                        "required_skills": self._extract_skills_from_question(question_text),
                        "industry_tags": self._extract_industry_tags(job_description),
                        "usage_count": 1,
                        "ai_service_used": ai_service_used,
                        "generation_prompt_hash": prompt_hash,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                    
                    new_question = await self.db_ops.create(Question, **question_data)
                    stored_questions.append(new_question)
            
            await self.db_session.commit()
            logger.info(f"Stored {len(stored_questions)} questions in question bank")
            return stored_questions
            
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error storing questions: {e}")
            raise
    
    async def get_question_bank_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the question bank."""
        try:
            # Get total count
            total_questions = await self.db_ops.count(Question)
            
            # Get questions by category
            category_stats = await self._get_category_stats()
            
            # Get questions by difficulty
            difficulty_stats = await self._get_difficulty_stats()
            
            # Get questions by AI service
            service_stats = await self._get_service_stats()
            
            # Get recent activity
            recent_activity = await self._get_recent_activity()
            
            return {
                "total_questions": total_questions,
                "questions_by_category": category_stats,
                "questions_by_difficulty": difficulty_stats,
                "questions_by_service": service_stats,
                "recent_activity": recent_activity,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting question bank stats: {e}")
            raise
    
    async def _find_existing_question(self, question_text: str, prompt_hash: str) -> Optional[Question]:
        """Find existing question by text or prompt hash."""
        try:
            # First try to find by exact text match
            result = await self.db_session.execute(
                select(Question).where(Question.question_text == question_text)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                return existing
            
            # Then try to find by prompt hash
            result = await self.db_session.execute(
                select(Question).where(Question.generation_prompt_hash == prompt_hash)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error finding existing question: {e}")
            return None
    
    async def _increment_usage_count(self, question_ids: List[str]) -> None:
        """Increment usage count for selected questions."""
        try:
            for question_id in question_ids:
                await self.db_session.execute(
                    select(Question)
                    .where(Question.id == question_id)
                    .update({"usage_count": Question.usage_count + 1})
                )
        except Exception as e:
            logger.error(f"Error incrementing usage count: {e}")
    
    async def _get_category_stats(self) -> Dict[str, int]:
        """Get question count by category."""
        try:
            result = await self.db_session.execute(
                select(Question.category, func.count(Question.id))
                .group_by(Question.category)
            )
            return dict(result.fetchall())
        except Exception as e:
            logger.error(f"Error getting category stats: {e}")
            return {}
    
    async def _get_difficulty_stats(self) -> Dict[str, int]:
        """Get question count by difficulty level."""
        try:
            result = await self.db_session.execute(
                select(Question.difficulty_level, func.count(Question.id))
                .group_by(Question.difficulty_level)
            )
            return dict(result.fetchall())
        except Exception as e:
            logger.error(f"Error getting difficulty stats: {e}")
            return {}
    
    async def _get_service_stats(self) -> Dict[str, int]:
        """Get question count by AI service used."""
        try:
            result = await self.db_session.execute(
                select(Question.ai_service_used, func.count(Question.id))
                .group_by(Question.ai_service_used)
            )
            return dict(result.fetchall())
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {}
    
    async def _get_recent_activity(self) -> Dict[str, Any]:
        """Get recent question bank activity."""
        try:
            # Get questions created in the last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_questions = await self.db_ops.count(
                Question,
                filters={"created_at": week_ago}
            )
            
            # Get most used questions
            result = await self.db_session.execute(
                select(Question.question_text, Question.usage_count)
                .order_by(desc(Question.usage_count))
                .limit(5)
            )
            most_used = [{"question": q, "usage": u} for q, u in result.fetchall()]
            
            return {
                "questions_added_last_week": recent_questions,
                "most_used_questions": most_used
            }
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return {}
    
    def _extract_keywords_from_role_and_jd(self, role: str, job_description: str) -> List[str]:
        """Extract relevant keywords from role and job description."""
        text = f"{role} {job_description}".lower()
        
        # Common technical keywords
        tech_keywords = [
            "python", "java", "javascript", "react", "angular", "vue", "node", "django", "flask",
            "spring", "sql", "postgresql", "mysql", "mongodb", "redis", "docker", "kubernetes",
            "aws", "azure", "gcp", "git", "ci/cd", "api", "rest", "graphql", "microservices",
            "machine learning", "ai", "data science", "analytics", "devops", "security"
        ]
        
        # Extract matching keywords
        keywords = []
        for keyword in tech_keywords:
            if keyword in text:
                keywords.append(keyword)
        
        # Extract other meaningful words (3+ characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        keywords.extend([word for word in words if word not in keywords])
        
        return keywords[:20]  # Limit to 20 keywords
    
    def _categorize_by_keywords(self, text: str, rules: Dict[str, List[str]]) -> str:
        """Generic keyword-based categorization."""
        text_lower = text.lower()
        for category, keywords in rules.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        return "technical"  # default
    
    def _determine_category(self, question_text: str, role: str, job_description: str) -> str:
        """Determine the category of a question."""
        return self._categorize_by_keywords(question_text, self.CATEGORIZATION_RULES)
    
    def _determine_difficulty(self, question_text: str, role: str, job_description: str) -> str:
        """Determine the difficulty level of a question."""
        text = question_text.lower()
        
        # Easy questions
        if any(keyword in text for keyword in [
            "what is", "define", "explain", "basic", "simple", "difference between"
        ]) or len(question_text.split()) < 15:
            return "easy"
        
        # Hard questions
        if any(keyword in text for keyword in [
            "design", "implement", "optimize", "scale", "distributed", "complex",
            "algorithm", "data structure", "performance", "architecture"
        ]) or len(question_text.split()) > 30:
            return "hard"
        
        # Default to medium
        return "medium"
    
    def _determine_subcategory(self, question_text: str, role: str, job_description: str) -> Optional[str]:
        """Determine the subcategory of a question."""
        text = question_text.lower()
        
        # Technical subcategories
        if "python" in text or "django" in text or "flask" in text:
            return "python"
        elif "javascript" in text or "react" in text or "node" in text:
            return "javascript"
        elif "java" in text or "spring" in text:
            return "java"
        elif "database" in text or "sql" in text:
            return "database"
        elif "api" in text or "rest" in text:
            return "api_design"
        elif "algorithm" in text or "data structure" in text:
            return "algorithms"
        
        return None
    
    def _extract_skills_from_question(self, question_text: str) -> List[str]:
        """Extract required skills from question text."""
        text = question_text.lower()
        skills = []
        
        # Map keywords to skills
        skill_mapping = {
            "python": ["python", "programming"],
            "javascript": ["javascript", "js", "programming"],
            "java": ["java", "programming"],
            "react": ["react", "frontend", "javascript"],
            "angular": ["angular", "frontend", "javascript"],
            "vue": ["vue", "frontend", "javascript"],
            "node": ["node.js", "backend", "javascript"],
            "django": ["django", "python", "web_framework"],
            "flask": ["flask", "python", "web_framework"],
            "spring": ["spring", "java", "web_framework"],
            "sql": ["sql", "database"],
            "postgresql": ["postgresql", "database"],
            "mysql": ["mysql", "database"],
            "mongodb": ["mongodb", "database", "nosql"],
            "redis": ["redis", "cache", "database"],
            "docker": ["docker", "containerization"],
            "kubernetes": ["kubernetes", "containerization", "orchestration"],
            "aws": ["aws", "cloud"],
            "azure": ["azure", "cloud"],
            "gcp": ["gcp", "google cloud", "cloud"],
            "git": ["git", "version_control"],
            "api": ["api", "rest", "web_services"],
            "microservices": ["microservices", "architecture"],
            "machine learning": ["machine learning", "ml", "ai"],
            "data science": ["data science", "analytics"],
            "devops": ["devops", "ci/cd", "automation"],
            "security": ["security", "cybersecurity"]
        }
        
        for skill, keywords in skill_mapping.items():
            if any(keyword in text for keyword in keywords):
                skills.append(skill)
        
        return skills[:10]  # Limit to 10 skills
    
    def _extract_industry_tags(self, job_description: str) -> List[str]:
        """Extract industry tags from job description."""
        text = job_description.lower()
        tags = []
        
        industry_mapping = {
            "technology": ["tech", "software", "it", "computer"],
            "finance": ["finance", "banking", "fintech", "financial"],
            "healthcare": ["healthcare", "medical", "health", "pharma"],
            "ecommerce": ["ecommerce", "retail", "shopping", "marketplace"],
            "education": ["education", "learning", "edtech", "school"],
            "gaming": ["gaming", "game", "entertainment"],
            "automotive": ["automotive", "car", "vehicle", "transportation"],
            "aerospace": ["aerospace", "aviation", "space", "defense"],
            "energy": ["energy", "oil", "gas", "renewable", "power"],
            "telecommunications": ["telecom", "communication", "network", "wireless"]
        }
        
        for industry, keywords in industry_mapping.items():
            if any(keyword in text for keyword in keywords):
                tags.append(industry)
        
        return tags[:5]  # Limit to 5 tags
