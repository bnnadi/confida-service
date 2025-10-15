"""
Async Hybrid AI Service.

This service intelligently combines question bank retrieval with AI generation,
providing a seamless experience for interview question generation.
"""
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.async_question_bank_service import AsyncQuestionBankService
from app.services.ollama_service import OllamaService
from app.utils.cache import cached
from app.utils.metrics import metrics
import time
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

class AsyncHybridAIService:
    """Async service that combines question bank with AI generation."""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.question_bank_service = AsyncQuestionBankService(db_session)
        self.ollama_service = OllamaService()
    
    @cached("async_question_generation", ttl=3600, cache_key_params=["role", "job_description", "count", "difficulty", "categories"])
    async def generate_interview_questions(
        self,
        role: str,
        job_description: str,
        count: int = 10,
        difficulty: str = "medium",
        categories: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate interview questions using a hybrid approach:
        1. First try to get questions from the question bank
        2. If not enough questions, generate additional ones using AI
        3. Store AI-generated questions in the question bank
        """
        start_time = time.time()
        
        try:
            # Try to get questions from the question bank first
            bank_questions = await self.question_bank_service.get_questions_for_role(
                role, job_description, count
            )
            
            # If we have enough questions from the bank, return them
            if len(bank_questions) >= count:
                logger.info(f"Retrieved {len(bank_questions)} questions from question bank")
                result = {
                    "questions": [q.question_text for q in bank_questions[:count]],
                    "source": "question_bank",
                    "bank_questions_count": len(bank_questions),
                    "ai_questions_count": 0
                }
                
                # Record metrics for question bank
                duration = time.time() - start_time
                metrics.record_ai_service_request(
                    service="question_bank",
                    operation="async_generate_interview_questions",
                    status="success",
                    duration=duration
                )
                
                return result
            
            # If we need more questions, generate them using AI
            remaining_count = count - len(bank_questions)
            ai_questions = await self._generate_ai_questions(
                role, job_description, remaining_count, difficulty, categories
            )
            
            # Store AI-generated questions in the question bank
            if ai_questions:
                prompt_hash = self._generate_prompt_hash(role, job_description, difficulty, categories)
                stored_questions = await self.question_bank_service.store_generated_questions(
                    ai_questions, role, job_description, "hybrid_ai", prompt_hash
                )
                logger.info(f"Stored {len(stored_questions)} AI-generated questions in question bank")
            
            # Combine questions from both sources
            all_questions = [q.question_text for q in bank_questions] + ai_questions
            
            result = {
                "questions": all_questions[:count],
                "source": "hybrid",
                "bank_questions_count": len(bank_questions),
                "ai_questions_count": len(ai_questions)
            }
            
            # Record metrics for hybrid approach
            duration = time.time() - start_time
            metrics.record_ai_service_request(
                service="hybrid_ai",
                operation="async_generate_interview_questions",
                status="success",
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            metrics.record_ai_service_request(
                service="hybrid_ai",
                operation="async_generate_interview_questions",
                status="error",
                duration=duration
            )
            logger.error(f"Error generating interview questions: {e}")
            raise
    
    async def analyze_answer(
        self,
        question: str,
        answer: str,
        role: str,
        job_description: str
    ) -> Dict[str, Any]:
        """
        Analyze an answer using AI and update question bank statistics.
        """
        try:
            # Use Ollama service to analyze the answer
            analysis = self.ollama_service.analyze_answer(question, answer, role, job_description)
            
            # Update question bank statistics if the question exists
            await self._update_question_stats(question, analysis.get("score", 0))
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing answer: {e}")
            raise
    
    async def get_available_services(self) -> Dict[str, Any]:
        """Get available AI services and question bank statistics."""
        try:
            # Get AI services
            ai_services = self.ollama_service.get_available_services()
            
            # Get question bank statistics
            question_bank_stats = await self.question_bank_service.get_question_bank_stats()
            
            return {
                "ai_services": ai_services,
                "question_bank_stats": question_bank_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting available services: {e}")
            raise
    
    async def list_models(self, service: str) -> List[str]:
        """List available models for a specific AI service."""
        try:
            return self.ollama_service.list_available_models()
        except Exception as e:
            logger.error(f"Error listing models for service '{service}': {e}")
            raise
    
    async def pull_model(self, service: str, model: str) -> Dict[str, Any]:
        """Pull a model for a specific AI service."""
        try:
            success = self.ollama_service.pull_model(model)
            return {"success": success, "model": model}
        except Exception as e:
            logger.error(f"Error pulling model '{model}' for service '{service}': {e}")
            raise
    
    async def _generate_ai_questions(
        self,
        role: str,
        job_description: str,
        count: int,
        difficulty: str,
        categories: List[str]
    ) -> List[str]:
        """Generate questions using AI service."""
        try:
            # Create a prompt for AI question generation
            prompt = self._create_question_generation_prompt(
                role, job_description, count, difficulty, categories
            )
            
            # Use Ollama service to generate questions
            response = self.ollama_service.generate_questions(prompt)
            
            # Parse the response to extract questions
            questions = self._parse_ai_response(response)
            
            return questions[:count]  # Ensure we don't exceed the requested count
            
        except Exception as e:
            logger.error(f"Error generating AI questions: {e}")
            return []
    
    async def _update_question_stats(self, question_text: str, score: float) -> None:
        """Update question bank statistics for a specific question."""
        try:
            # Find the question in the database
            from app.database.models import Question
            from sqlalchemy import select, update
            
            result = await self.db_session.execute(
                select(Question).where(Question.question_text == question_text)
            )
            question = result.scalar_one_or_none()
            
            if question:
                # Update statistics
                new_usage_count = question.usage_count + 1
                new_average_score = (
                    (question.average_score * question.usage_count + score) / new_usage_count
                )
                new_success_rate = (
                    (question.success_rate * question.usage_count + (1 if score >= 0.7 else 0)) / new_usage_count
                )
                
                await self.db_session.execute(
                    update(Question)
                    .where(Question.id == question.id)
                    .values(
                        usage_count=new_usage_count,
                        average_score=new_average_score,
                        success_rate=new_success_rate,
                        updated_at=datetime.utcnow()
                    )
                )
                
                await self.db_session.commit()
                logger.info(f"Updated statistics for question: {question_text[:50]}...")
                
        except Exception as e:
            logger.error(f"Error updating question stats: {e}")
            await self.db_session.rollback()
    
    def _create_question_generation_prompt(
        self,
        role: str,
        job_description: str,
        count: int,
        difficulty: str,
        categories: List[str]
    ) -> str:
        """Create a prompt for AI question generation."""
        categories_text = ", ".join(categories) if categories else "technical, behavioral, system design"
        
        prompt = f"""
        Generate {count} interview questions for a {role} position.
        
        Job Description:
        {job_description}
        
        Requirements:
        - Difficulty level: {difficulty}
        - Categories: {categories_text}
        - Questions should be specific to the role and job requirements
        - Mix of technical and behavioral questions
        - Each question should be clear and actionable
        
        Format: Return only the questions, one per line, without numbering or bullet points.
        """
        
        return prompt.strip()
    
    def _parse_ai_response(self, response: str) -> List[str]:
        """Parse AI response to extract individual questions."""
        try:
            # Split by newlines and clean up
            questions = []
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith(('#', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                    # Remove common prefixes
                    for prefix in ['Q:', 'Question:', 'Q.', 'Q)']:
                        if line.startswith(prefix):
                            line = line[len(prefix):].strip()
                            break
                    questions.append(line)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return []
    
    def _generate_prompt_hash(
        self,
        role: str,
        job_description: str,
        difficulty: str,
        categories: List[str]
    ) -> str:
        """Generate a hash for the prompt to identify similar requests."""
        prompt_data = f"{role}:{job_description}:{difficulty}:{':'.join(categories or [])}"
        return hashlib.sha256(prompt_data.encode()).hexdigest()
