"""
Centralized Fallback Manager for Confida

This service consolidates all fallback logic from various services
into a single, comprehensive fallback management system.
"""
from typing import Dict, Any, List, Callable
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FallbackManager:
    """Centralized fallback manager for all services."""
    
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
    
    def get_fallback_response(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Get fallback response for a specific operation."""
        try:
            if operation in self.fallback_strategies:
                return self.fallback_strategies[operation](**kwargs)
            elif operation in self.fallback_responses:
                return self.fallback_responses[operation].copy()
            else:
                return self._generic_fallback(operation, **kwargs)
        except Exception as e:
            logger.error(f"Error generating fallback for {operation}: {e}")
            return self._generic_fallback(operation, **kwargs)
    
    def _fallback_questions(self, role: str = "Software Engineer", count: int = 10, **kwargs) -> Dict[str, Any]:
        """Generate fallback questions based on role."""
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
        
        return {
            "questions": selected_questions,
            "metadata": {
                "source": "fallback",
                "reason": "service_unavailable",
                "role": role,
                "count": len(selected_questions)
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
fallback_manager = FallbackManager()

# Convenience functions
def get_fallback_response(operation: str, **kwargs) -> Dict[str, Any]:
    """Get fallback response for an operation."""
    return fallback_manager.get_fallback_response(operation, **kwargs)

def register_fallback_strategy(operation: str, strategy: Callable) -> None:
    """Register a custom fallback strategy."""
    fallback_manager.register_fallback_strategy(operation, strategy)

def register_fallback_response(operation: str, response: Dict[str, Any]) -> None:
    """Register a custom fallback response."""
    fallback_manager.register_fallback_response(operation, response)
