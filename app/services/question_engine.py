"""
Question Engine Service for InterviewIQ

This service provides a unified interface for generating interview questions
from both practice scenarios and job-based interviews.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.models import Question
from app.services.hybrid_ai_service import HybridAIService
from app.utils.logger import get_logger
from app.exceptions import AIServiceError

logger = get_logger(__name__)

class QuestionEngine:
    """Unified question generation service for both practice and job-based interviews."""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = HybridAIService()
    
    def generate_questions_from_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Generate questions from a practice scenario.
        
        Args:
            scenario_id: ID of the practice scenario
            
        Returns:
            List of question dictionaries with id, text, and type
        """
        try:
            # For now, we'll use a predefined set of practice questions
            # In a full implementation, this would query a scenarios table
            practice_questions = self._get_practice_questions_by_scenario(scenario_id)
            
            questions = []
            for i, question_text in enumerate(practice_questions, 1):
                questions.append({
                    "id": f"scenario_{scenario_id}_q_{i}",
                    "text": question_text,
                    "type": "behavioral",
                    "difficulty_level": "medium",
                    "category": "practice"
                })
            
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
    
    def _get_practice_questions_by_scenario(self, scenario_id: str) -> List[str]:
        """
        Get practice questions for a specific scenario.
        This is a placeholder implementation - in production, this would query a database.
        """
        # Define practice scenarios with their questions
        scenario_questions = {
            "software_engineer": [
                "Tell me about a challenging technical problem you solved recently.",
                "How do you approach debugging a complex issue?",
                "Describe a time when you had to learn a new technology quickly.",
                "How do you ensure code quality in your projects?",
                "Tell me about a time you had to work with a difficult team member."
            ],
            "data_scientist": [
                "Describe a data analysis project you're particularly proud of.",
                "How do you handle missing or incomplete data?",
                "Tell me about a time you had to explain complex data insights to non-technical stakeholders.",
                "What's your approach to feature selection in machine learning?",
                "Describe a time when your analysis led to a significant business decision."
            ],
            "product_manager": [
                "How do you prioritize features for a product roadmap?",
                "Tell me about a time you had to make a difficult product decision.",
                "How do you gather and analyze user feedback?",
                "Describe a time when you had to manage conflicting stakeholder requirements.",
                "How do you measure the success of a product feature?"
            ],
            "sales_representative": [
                "Tell me about your most successful sales achievement.",
                "How do you handle objections from potential customers?",
                "Describe a time when you had to rebuild a relationship with a difficult client.",
                "How do you qualify leads and prospects?",
                "Tell me about a time you had to meet an aggressive sales target."
            ],
            "marketing_manager": [
                "Describe a successful marketing campaign you've managed.",
                "How do you measure the ROI of marketing activities?",
                "Tell me about a time you had to pivot a marketing strategy mid-campaign.",
                "How do you stay updated with marketing trends and technologies?",
                "Describe a time when you had to work with a limited marketing budget."
            ]
        }
        
        # Return questions for the scenario, or default general questions
        return scenario_questions.get(scenario_id, [
            "Tell me about yourself and your background.",
            "What are your greatest strengths and weaknesses?",
            "Why are you interested in this position?",
            "Where do you see yourself in 5 years?",
            "Do you have any questions for us?"
        ])
    
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
        Get list of available practice scenarios.
        
        Returns:
            List of scenario dictionaries with id, name, and description
        """
        scenarios = [
            {
                "id": "software_engineer",
                "name": "Software Engineer",
                "description": "Practice questions for software engineering roles"
            },
            {
                "id": "data_scientist", 
                "name": "Data Scientist",
                "description": "Practice questions for data science roles"
            },
            {
                "id": "product_manager",
                "name": "Product Manager", 
                "description": "Practice questions for product management roles"
            },
            {
                "id": "sales_representative",
                "name": "Sales Representative",
                "description": "Practice questions for sales roles"
            },
            {
                "id": "marketing_manager",
                "name": "Marketing Manager",
                "description": "Practice questions for marketing roles"
            }
        ]
        
        return scenarios
