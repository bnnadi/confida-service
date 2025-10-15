"""
Simple Question Service for InterviewIQ

This service replaces 11+ overcomplicated question generation services with a single,
clean, maintainable service that handles all question generation needs.

Replaces:
- QuestionEngine
- QuestionBankService  
- HybridAIService
- AsyncHybridAIService
- AsyncQuestionBankService
- AIFallbackService
- IntelligentQuestionSelector
- FunctionalQuestionSelector
- QuestionSelectionPipeline
- QuestionMatcher
- QuestionDiversityEngine
- AIServiceOrchestrator
- ServiceFactory
- DynamicPromptService
"""
import time
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.models import Question
from app.database.question_database_models import QuestionTemplate
from app.services.smart_token_optimizer import SmartTokenOptimizer
from app.services.cost_tracker import CostTracker
from app.utils.logger import get_logger
from app.utils.prompt_templates import PromptTemplates
from app.exceptions import AIServiceError

logger = get_logger(__name__)


class QuestionService:
    """
    Main question generation service for InterviewIQ.
    
    This service replaces 11+ overcomplicated services with a single,
    clean, maintainable solution that handles all question generation needs.
    
    Features:
    - Database-first approach with AI fallback
    - Token optimization and cost tracking
    - Simple, direct implementation
    - Easy to test and maintain
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.token_optimizer = SmartTokenOptimizer()
        self.cost_tracker = CostTracker()
        
        # Initialize AI clients lazily to avoid circular imports
        self._openai_client = None
        self._anthropic_client = None
        self._ollama_service = None
    
    def generate_questions(self, role: str, job_description: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate questions using database-first approach with AI fallback.
        
        This single method replaces the entire complex pipeline of 11+ services.
        
        Args:
            role: Job title/role
            job_description: Job description text
            count: Number of questions to generate
            
        Returns:
            List of question dictionaries with id, text, type, and metadata
        """
        start_time = time.time()
        logger.info(f"Generating {count} questions for role: {role}")
        
        try:
            # Step 1: Try database first (simple query)
            db_questions = self._get_database_questions(role, job_description, count)
            logger.info(f"Found {len(db_questions)} questions in database")
            
            # Step 2: If not enough, use AI (simple call)
            ai_questions = []
            if len(db_questions) < count:
                needed = count - len(db_questions)
                logger.info(f"Need {needed} more questions from AI")
                ai_questions = self._generate_ai_questions(role, job_description, needed)
            
            # Step 3: Combine and format results
            all_questions = db_questions + ai_questions
            formatted_questions = self._format_questions(all_questions, role, start_time)
            
            # Step 4: Log generation metrics
            self._log_generation_metrics(role, job_description, len(db_questions), len(ai_questions), start_time)
            
            logger.info(f"Generated {len(formatted_questions)} questions total")
            return formatted_questions
            
        except Exception as e:
            logger.error(f"Error generating questions for role {role}: {e}")
            raise AIServiceError(f"Failed to generate questions: {e}")
    
    def _get_database_questions(self, role: str, job_description: str, count: int) -> List[QuestionTemplate]:
        """Get questions from database using simple, direct queries."""
        try:
            # Simple role-based query - use basic filtering for now
            role_lower = role.lower()
            
            # Query for active questions (simplified approach)
            questions = self.db.query(QuestionTemplate).filter(
                QuestionTemplate.is_active == True
            ).order_by(
                QuestionTemplate.quality_score.desc(),
                QuestionTemplate.usage_count.asc()  # Prefer less used questions
            ).limit(count).all()
            
            # Update usage count for analytics
            from datetime import datetime
            for question in questions:
                question.usage_count += 1
                question.last_used = datetime.utcnow()
            
            self.db.commit()
            return questions
            
        except Exception as e:
            logger.error(f"Error querying database questions: {e}")
            return []
    
    def _generate_ai_questions(self, role: str, job_description: str, count: int) -> List[Dict[str, Any]]:
        """Generate questions using AI with token optimization."""
        try:
            # Get token optimization using the correct method name
            optimization = self.token_optimizer.optimize_request(role, job_description, "ollama")
            optimal_tokens = optimization.optimal_tokens
            recommended_service = "ollama"  # Default to ollama for simplicity
            
            logger.info(f"Using {recommended_service} with {optimal_tokens} tokens")
            
            # Generate questions using Ollama (simplified approach)
            questions = self._generate_with_ollama(role, job_description, count, optimal_tokens)
            
            # Track cost using legacy method
            self.cost_tracker.track_request_legacy(
                service=recommended_service,
                operation="generate_questions",
                tokens_used=optimal_tokens,
                estimated_cost=optimization.estimated_cost,
                success=True
            )
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating AI questions: {e}")
            return []
    
    def _generate_with_ollama(self, role: str, job_description: str, count: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Generate questions using Ollama service."""
        try:
            if not self._ollama_service:
                from app.services.ollama_service import OllamaService
                self._ollama_service = OllamaService()
            
            # Use the correct method name
            response = self._ollama_service.generate_interview_questions(role, job_description)
            
            # Extract questions from response
            questions = []
            for i, question_text in enumerate(response.questions, 1):
                questions.append({
                    "question_text": question_text,
                    "question_type": self._classify_question_type(question_text),
                    "difficulty_level": "medium",
                    "category": "ai_generated",
                    "source": "ollama",
                    "quality_score": 0.8,
                    "usage_count": 0
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return []
    
    def _generate_with_openai(self, role: str, job_description: str, count: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Generate questions using OpenAI service."""
        try:
            if not self._openai_client:
                from app.utils.service_initializer import ServiceInitializer
                self._openai_client = ServiceInitializer.init_openai_client()
            
            import os
            model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
            prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
            
            response = self._openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PromptTemplates.QUESTION_GENERATION_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content, "openai")
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return []
    
    def _generate_with_anthropic(self, role: str, job_description: str, count: int, max_tokens: int) -> List[Dict[str, Any]]:
        """Generate questions using Anthropic service."""
        try:
            if not self._anthropic_client:
                from app.utils.service_initializer import ServiceInitializer
                self._anthropic_client = ServiceInitializer.init_anthropic_client()
            
            import os
            model = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
            prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
            
            response = self._anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=PromptTemplates.QUESTION_GENERATION_SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            return self._parse_ai_response(content, "anthropic")
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return []
    
    def _parse_ai_response(self, response: str, service: str) -> List[Dict[str, Any]]:
        """Parse AI response into question format."""
        try:
            questions = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or 
                           line.startswith(('•', '-', '*'))):
                    # Clean up the question text
                    question_text = line
                    for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '•', '-', '*']:
                        if question_text.startswith(prefix):
                            question_text = question_text[len(prefix):].strip()
                            break
                    
                    if question_text:
                        questions.append({
                            "question_text": question_text,
                            "question_type": self._classify_question_type(question_text),
                            "difficulty_level": "medium",
                            "category": "ai_generated",
                            "source": service,
                            "quality_score": 0.8,  # Default quality for AI questions
                            "usage_count": 0
                        })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return []
    
    def _format_questions(self, questions: List, role: str, start_time: float) -> List[Dict[str, Any]]:
        """Format questions into consistent dictionary format."""
        formatted = []
        
        for i, question in enumerate(questions, 1):
            if hasattr(question, 'question_text'):
                # Database question
                formatted.append({
                    "id": str(question.id),
                    "text": question.question_text,
                    "type": question.question_type or self._classify_question_type(question.question_text),
                    "difficulty_level": question.difficulty_level,
                    "category": question.question_type,  # Use question_type as category
                    "source": "database",
                    "quality_score": question.quality_score,
                    "metadata": {
                        "generation_method": "database",
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                })
            else:
                # AI question
                formatted.append({
                    "id": f"ai_{hash(role)}_{i}",
                    "text": question["question_text"],
                    "type": question["question_type"],
                    "difficulty_level": question["difficulty_level"],
                    "category": question["category"],
                    "source": question["source"],
                    "quality_score": question["quality_score"],
                    "metadata": {
                        "generation_method": "ai",
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                })
        
        return formatted
    
    def _classify_question_type(self, question_text: str) -> str:
        """Classify question type based on content."""
        question_lower = question_text.lower()
        
        if any(keyword in question_lower for keyword in [
            "code", "programming", "algorithm", "database", "system", "architecture",
            "debug", "optimize", "performance", "security", "testing"
        ]):
            return "technical"
        
        if any(keyword in question_lower for keyword in [
            "tell me about a time", "describe a situation", "give me an example",
            "how did you handle", "what did you do when", "share an experience"
        ]):
            return "behavioral"
        
        if any(keyword in question_lower for keyword in [
            "what would you do if", "how would you handle", "imagine you",
            "suppose you", "if you were", "scenario"
        ]):
            return "situational"
        
        return "general"
    
    def _extract_seniority(self, role: str) -> str:
        """Extract seniority level from role."""
        role_lower = role.lower()
        
        if any(level in role_lower for level in ["senior", "sr", "lead", "principal", "staff", "architect"]):
            return "senior"
        elif any(level in role_lower for level in ["junior", "jr", "entry", "associate"]):
            return "junior"
        elif any(level in role_lower for level in ["manager", "director", "vp", "cto", "head"]):
            return "manager"
        else:
            return "mid"
    
    def _extract_tech_domains(self, job_description: str) -> List[str]:
        """Extract technical domains from job description."""
        domains = []
        desc_lower = job_description.lower()
        
        tech_mapping = {
            "frontend": ["react", "angular", "vue", "javascript", "typescript", "html", "css"],
            "backend": ["python", "java", "node", "api", "server", "database"],
            "cloud": ["aws", "azure", "gcp", "cloud", "kubernetes", "docker"],
            "mobile": ["ios", "android", "mobile", "swift", "kotlin"],
            "data": ["data", "analytics", "machine learning", "ai", "sql", "python"]
        }
        
        for domain, keywords in tech_mapping.items():
            if any(keyword in desc_lower for keyword in keywords):
                domains.append(domain)
        
        return domains
    
    def _log_generation_metrics(self, role: str, job_description: str, db_count: int, ai_count: int, start_time: float):
        """Log generation metrics for analytics."""
        try:
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"Question generation metrics - Role: {role}, "
                       f"DB questions: {db_count}, AI questions: {ai_count}, "
                       f"Processing time: {processing_time}ms")
            
            # Could store in database for analytics if needed
            # self._store_generation_log(role, job_description, db_count, ai_count, processing_time)
            
        except Exception as e:
            logger.error(f"Error logging generation metrics: {e}")
    
    def get_available_scenarios(self) -> List[Dict[str, str]]:
        """
        Get available practice scenarios.
        
        This method provides backward compatibility with the old QuestionEngine.
        """
        try:
            from app.services.scenario_service import ScenarioService
            scenario_service = ScenarioService(self.db)
            scenarios = scenario_service.get_all_scenarios()
            
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
            
            return scenario_list
            
        except Exception as e:
            logger.error(f"Error retrieving scenarios: {e}")
            return []
    
    def generate_questions_from_scenario(self, scenario_id: str) -> List[Dict[str, Any]]:
        """
        Generate questions from a practice scenario.
        
        This method provides backward compatibility with the old QuestionEngine.
        """
        try:
            from app.services.scenario_service import ScenarioService
            scenario_service = ScenarioService(self.db)
            questions = scenario_service.get_scenario_questions(scenario_id)
            
            if questions:
                scenario_service.increment_usage_count(scenario_id)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions from scenario {scenario_id}: {e}")
            return []
