"""
Question Engine Service for InterviewIQ

This service provides a unified interface for generating interview questions
from both practice scenarios and job-based interviews.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.models import Question
from app.services.hybrid_ai_service import HybridAIService
from app.services.scenario_service import ScenarioService
from app.utils.logger import get_logger
from app.exceptions import AIServiceError

logger = get_logger(__name__)

class QuestionEngine:
    """Unified question generation service for both practice and job-based interviews."""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = HybridAIService()
        self.scenario_service = ScenarioService(db)
    
    def generate_questions_from_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Generate questions from a practice scenario using database integration.
        
        Args:
            scenario_id: ID of the practice scenario
            
        Returns:
            List of question dictionaries with id, text, and type
        """
        try:
            # Get questions from database using ScenarioService
            questions = self.scenario_service.get_scenario_questions(scenario_id)
            
            if not questions:
                logger.warning(f"No questions found for scenario {scenario_id}")
                return []
            
            # Increment usage count for analytics
            self.scenario_service.increment_usage_count(scenario_id)
            
            logger.info(f"Generated {len(questions)} questions for scenario {scenario_id}")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions from scenario {scenario_id}: {e}")
            raise AIServiceError(f"Failed to generate questions from scenario: {e}")
    
    def generate_questions_from_job(self, job_title: str, job_description: str) -> List[Dict[str, Any]]:
        """
        Generate questions from job title and description using AI.
        
        Args:
            job_title: The job title/role
            job_description: The job description
            
        Returns:
            List of question dictionaries with id, text, and type
        """
        try:
            # Use the existing AI service to generate questions
            ai_response = self.ai_service.generate_interview_questions(job_title, job_description)
            
            questions = []
            for i, question_text in enumerate(ai_response.questions, 1):
                # Determine question type based on content
                question_type = self._classify_question_type(question_text)
                
                questions.append({
                    "id": f"job_{hash(job_title)}_{i}",
                    "text": question_text,
                    "type": question_type,
                    "difficulty_level": "medium",
                    "category": "job_based"
                })
            
            logger.info(f"Generated {len(questions)} questions for job: {job_title}")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions from job {job_title}: {e}")
            raise AIServiceError(f"Failed to generate questions from job description: {e}")
    
    
    def _classify_question_type(self, question_text: str) -> str:
        """
        Classify the type of question based on its content.
        
        Args:
            question_text: The question text to classify
            
        Returns:
            Question type: "behavioral", "technical", "situational", or "general"
        """
        question_lower = question_text.lower()
        
        # Technical questions
        if any(keyword in question_lower for keyword in [
            "code", "programming", "algorithm", "database", "system", "architecture",
            "debug", "optimize", "performance", "security", "testing"
        ]):
            return "technical"
        
        # Behavioral questions (STAR method)
        if any(keyword in question_lower for keyword in [
            "tell me about a time", "describe a situation", "give me an example",
            "how did you handle", "what did you do when", "share an experience"
        ]):
            return "behavioral"
        
        # Situational questions
        if any(keyword in question_lower for keyword in [
            "what would you do if", "how would you handle", "imagine you",
            "suppose you", "if you were", "scenario"
        ]):
            return "situational"
        
        # Default to general
        return "general"
    
    def get_available_scenarios(self) -> List[Dict[str, str]]:
        """
        Get list of available practice scenarios from database.
        
        Returns:
            List of scenario dictionaries with id, name, and description
        """
        try:
            scenarios = self.scenario_service.get_all_scenarios()
            
            scenario_list = []
            for scenario in scenarios:
                scenario_list.append({
                    "id": scenario.id,
                    "name": scenario.name,
                    "description": scenario.description or f"Practice questions for {scenario.name} roles",
                    "category": scenario.category,
                    "difficulty_level": scenario.difficulty_level,
                    "compatible_roles": scenario.compatible_roles
                })
            
            logger.info(f"Retrieved {len(scenario_list)} available scenarios")
            return scenario_list
            
        except Exception as e:
            logger.error(f"Error retrieving available scenarios: {e}")
            # Return empty list on error to prevent API failures
            return []
