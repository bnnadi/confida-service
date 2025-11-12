"""
Centralized Fallback Manager for Confida

This service consolidates all fallback logic from various services
into a single, comprehensive fallback management system.

Enhanced with database-backed fallback questions system that queries
the question database when AI service fails.
"""
from typing import Dict, Any, List, Callable, Optional
from app.utils.logger import get_logger
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

logger = get_logger(__name__)

class FallbackService:
    """Centralized fallback service for all services."""
    
    def __init__(self):
        self.fallback_responses = self._initialize_fallback_responses()
        self.fallback_strategies = self._initialize_fallback_strategies()
    
    def _initialize_fallback_responses(self) -> Dict[str, Dict[str, Any]]:
        """Initialize standard fallback responses for different operations."""
        return {
            "question_generation": {
                "questions": [
                    "Tell me about your experience with Python programming.",
                    "How do you approach debugging complex issues?",
                    "Describe a challenging project you've worked on.",
                    "What's your experience with database design?",
                    "How do you ensure code quality in your projects?",
                    "Explain your understanding of software architecture.",
                    "How do you handle performance optimization?",
                    "Describe your experience with testing methodologies.",
                    "What's your approach to code review processes?",
                    "How do you stay updated with new technologies?"
                ],
                "metadata": {
                    "source": "fallback",
                    "reason": "service_unavailable",
                    "count": 10
                }
            },
            "answer_analysis": {
                "analysis": "Analysis temporarily unavailable. Please try again later.",
                "score": {
                    "clarity": 7.0,
                    "confidence": 7.0,
                    "technical": 7.0,
                    "overall": 7.0
                },
                "suggestions": [
                    "Analysis service is temporarily unavailable",
                    "Please try again in a few moments"
                ],
                "metadata": {
                    "source": "fallback",
                    "reason": "service_unavailable"
                }
            },
            "file_upload": {
                "success": False,
                "error": "File upload service temporarily unavailable",
                "suggestion": "Please try again later",
                "metadata": {
                    "source": "fallback",
                    "reason": "service_unavailable"
                }
            },
            "role_analysis": {
                "role": "Software Engineer",
                "industry": "Technology",
                "seniority_level": "Mid",
                "company_size": "Medium",
                "required_skills": ["Python", "JavaScript", "SQL"],
                "tech_stack": ["React", "Node.js", "PostgreSQL"],
                "soft_skills": ["Communication", "Teamwork", "Problem Solving"],
                "experience_years": 3,
                "job_function": "engineering",
                "metadata": {
                    "source": "fallback",
                    "reason": "service_unavailable"
                }
            },
            "token_optimization": {
                "optimal_tokens": 500,
                "complexity_score": 1.0,
                "estimated_cost": 0.005,
                "optimization_applied": "fallback_default",
                "confidence_score": 0.5,
                "metadata": {
                    "source": "fallback",
                    "reason": "service_unavailable"
                }
            }
        }
    
    def _initialize_fallback_strategies(self) -> Dict[str, Callable]:
        """Initialize fallback strategies for different operations."""
        return {
            "question_generation": self._fallback_questions,
            "answer_analysis": self._fallback_analysis,
            "file_upload": self._fallback_file_upload,
            "role_analysis": self._fallback_role_analysis,
            "token_optimization": self._fallback_token_optimization
        }
    
    async def get_fallback_response(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Get fallback response for a specific operation."""
        try:
            if operation in self.fallback_strategies:
                strategy = self.fallback_strategies[operation]
                # Check if strategy is async using inspect
                import inspect
                if inspect.iscoroutinefunction(strategy):
                    return await strategy(**kwargs)
                else:
                    return strategy(**kwargs)
            elif operation in self.fallback_responses:
                return self.fallback_responses[operation].copy()
            else:
                return self._generic_fallback(operation, **kwargs)
        except Exception as e:
            logger.error(f"Error generating fallback for {operation}: {e}")
            return self._generic_fallback(operation, **kwargs)
    
    async def _fallback_questions(
        self, 
        role: str = "Software Engineer", 
        count: int = 10, 
        db_session: Optional[Any] = None,
        job_description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced fallback questions that queries database first, then falls back to hardcoded.
        
        Args:
            role: Job role/title
            count: Number of questions to return
            db_session: Database session (sync or async)
            job_description: Optional job description for context
            **kwargs: Additional parameters
            
        Returns:
            Dict with questions list and metadata
        """
        # Try to get questions from database first
        if db_session:
            try:
                db_questions = await self._get_questions_from_database(
                    db_session=db_session,
                    role=role,
                    count=count,
                    job_description=job_description
                )
                
                if db_questions:
                    logger.info(f"Retrieved {len(db_questions)} questions from database for fallback (role: {role})")
                    return {
                        "questions": db_questions,
                        "metadata": {
                            "source": "database_fallback",
                            "reason": "ai_service_unavailable",
                            "role": role,
                            "count": len(db_questions)
                        }
                    }
            except Exception as e:
                logger.warning(f"Failed to retrieve questions from database: {e}. Falling back to hardcoded questions.")
        
        # Fallback to hardcoded questions
        return self._get_hardcoded_fallback_questions(role=role, count=count)
    
    async def _get_questions_from_database(
        self,
        db_session: Any,
        role: str,
        count: int,
        job_description: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query database for relevant questions based on role and criteria.
        
        Args:
            db_session: Database session (sync or async)
            role: Job role to match
            count: Number of questions to retrieve
            job_description: Optional job description for additional context
            
        Returns:
            List of question dictionaries in format expected by AI service
        """
        try:
            from app.database.models import Question
            
            # Determine if session is async
            is_async = hasattr(db_session, 'execute')
            
            # Build query to find questions matching role
            # Try to match compatible_roles JSONB field
            role_lower = role.lower()
            
            if is_async:
                # Async query
                query = select(Question).where(
                    or_(
                        Question.compatible_roles.contains([role]),
                        Question.compatible_roles.contains([role_lower]),
                        func.lower(Question.category).contains(role_lower),
                        Question.question_text.ilike(f"%{role}%")
                    )
                ).order_by(
                    Question.usage_count.desc(),
                    Question.average_score.desc().nulls_last()
                ).limit(count)
                
                result = await db_session.execute(query)
                questions = result.scalars().all()
            else:
                # Sync query
                questions = db_session.query(Question).filter(
                    or_(
                        Question.compatible_roles.contains([role]),
                        Question.compatible_roles.contains([role_lower]),
                        func.lower(Question.category).contains(role_lower),
                        Question.question_text.ilike(f"%{role}%")
                    )
                ).order_by(
                    Question.usage_count.desc(),
                    Question.average_score.desc().nulls_last()
                ).limit(count).all()
            
            # If no role-specific questions found, try general questions
            if not questions:
                logger.info(f"No role-specific questions found for {role}, trying general questions")
                if is_async:
                    general_query = select(Question).order_by(
                        Question.usage_count.desc(),
                        Question.average_score.desc().nulls_last()
                    ).limit(count)
                    result = await db_session.execute(general_query)
                    questions = result.scalars().all()
                else:
                    questions = db_session.query(Question).order_by(
                        Question.usage_count.desc(),
                        Question.average_score.desc().nulls_last()
                    ).limit(count).all()
            
            # Convert to expected format
            question_list = []
            for q in questions:
                question_dict = {
                    "text": q.question_text,
                    "question_text": q.question_text,
                    "question_id": str(q.id),
                    "source": "from_library",
                    "metadata": {
                        "difficulty_level": q.difficulty_level,
                        "category": q.category,
                        "subcategory": q.subcategory,
                        "compatible_roles": q.compatible_roles or [],
                        "required_skills": q.required_skills or [],
                        "industry_tags": q.industry_tags or []
                    },
                    "identifiers": {
                        "difficulty": q.difficulty_level,
                        "category": q.category,
                        "role": role
                    }
                }
                question_list.append(question_dict)
            
            return question_list
            
        except Exception as e:
            logger.error(f"Error querying database for fallback questions: {e}")
            raise
    
    def _get_hardcoded_fallback_questions(self, role: str, count: int) -> Dict[str, Any]:
        """Get hardcoded fallback questions when database query fails."""
        base_questions = self.fallback_responses["question_generation"]["questions"]
        
        # Role-specific question modifications
        role_modifications = {
            "data scientist": ["Explain your experience with machine learning algorithms.",
                             "How do you approach data preprocessing and cleaning?"],
            "frontend developer": ["Describe your experience with modern JavaScript frameworks.",
                                 "How do you ensure responsive design across devices?"],
            "backend developer": ["Explain your approach to API design and development.",
                                "How do you handle database optimization and scaling?"],
            "devops engineer": ["Describe your experience with containerization and orchestration.",
                              "How do you approach infrastructure as code?"]
        }
        
        # Get role-specific questions or use base questions
        role_questions = role_modifications.get(role.lower(), base_questions)
        
        # Combine and limit to requested count
        all_questions = base_questions + role_questions
        selected_questions = all_questions[:count]
        
        # Convert to expected format (list of dicts matching database format)
        question_list = []
        for q_text in selected_questions:
            question_dict = {
                "text": q_text,
                "question_text": q_text,
                "source": "hardcoded_fallback",
                "metadata": {
                    "difficulty_level": "medium",
                    "category": "general",
                    "compatible_roles": [role] if role else [],
                    "required_skills": [],
                    "industry_tags": []
                },
                "identifiers": {
                    "difficulty": "medium",
                    "category": "general",
                    "role": role
                }
            }
            question_list.append(question_dict)
        
        return {
            "questions": question_list,
            "metadata": {
                "source": "hardcoded_fallback",
                "reason": "service_unavailable",
                "role": role,
                "count": len(question_list)
            }
        }
    
    def _fallback_analysis(self, **kwargs) -> Dict[str, Any]:
        """Generate fallback analysis response."""
        return self.fallback_responses["answer_analysis"].copy()
    
    def _fallback_file_upload(self, **kwargs) -> Dict[str, Any]:
        """Generate fallback file upload response."""
        return self.fallback_responses["file_upload"].copy()
    
    def _fallback_role_analysis(self, role: str = "Software Engineer", **kwargs) -> Dict[str, Any]:
        """Generate fallback role analysis response."""
        response = self.fallback_responses["role_analysis"].copy()
        response["role"] = role
        return response
    
    def _fallback_token_optimization(self, **kwargs) -> Dict[str, Any]:
        """Generate fallback token optimization response."""
        return self.fallback_responses["token_optimization"].copy()
    
    def _generic_fallback(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Generate generic fallback response for unknown operations."""
        return {
            "error": f"Service temporarily unavailable for {operation}",
            "message": "Please try again later",
            "metadata": {
                "source": "fallback",
                "reason": "service_unavailable",
                "operation": operation
            }
        }
    
    def register_fallback_strategy(self, operation: str, strategy: Callable) -> None:
        """Register a custom fallback strategy for an operation."""
        self.fallback_strategies[operation] = strategy
        logger.info(f"Registered custom fallback strategy for {operation}")
    
    def register_fallback_response(self, operation: str, response: Dict[str, Any]) -> None:
        """Register a custom fallback response for an operation."""
        self.fallback_responses[operation] = response
        logger.info(f"Registered custom fallback response for {operation}")
    
    def get_available_operations(self) -> List[str]:
        """Get list of operations with available fallbacks."""
        return list(set(self.fallback_responses.keys()) | set(self.fallback_strategies.keys()))
    
    def is_fallback_available(self, operation: str) -> bool:
        """Check if fallback is available for an operation."""
        return operation in self.fallback_responses or operation in self.fallback_strategies

# Global fallback manager instance
fallback_service = FallbackService()

# Convenience functions
async def get_fallback_response(operation: str, **kwargs) -> Dict[str, Any]:
    """Get fallback response for an operation."""
    return await fallback_service.get_fallback_response(operation, **kwargs)

def register_fallback_strategy(operation: str, strategy: Callable) -> None:
    """Register a custom fallback strategy."""
    fallback_service.register_fallback_strategy(operation, strategy)

def register_fallback_response(operation: str, response: Dict[str, Any]) -> None:
    """Register a custom fallback response."""
    fallback_service.register_fallback_response(operation, response)
