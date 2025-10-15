import os
import json
import requests
import hashlib
from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy.orm import Session
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.services.ollama_service import OllamaService
from app.services.question_bank_service import QuestionBankService
from app.utils.prompt_templates import PromptTemplates
from app.utils.response_parsers import ResponseParsers
from app.utils.service_initializer import ServiceInitializer
from app.utils.fallback_responses import FallbackResponses
from app.utils.logger import get_logger
from app.exceptions import ServiceUnavailableError

logger = get_logger(__name__)

class AIServiceType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class HybridAIService:
    def __init__(self, db_session: Optional[Session] = None):
        self.ollama_service = OllamaService()
        self.service_priority = self._get_service_priority()
        self.openai_client = None
        self.anthropic_client = None
        self.db_session = db_session
        
        # Initialize question bank service if database session is available
        self.question_bank_service = None
        if self.db_session:
            self.question_bank_service = QuestionBankService(self.db_session)
        
        # Initialize external services if configured
        self._init_external_services()
    
    def _get_service_priority(self) -> List[AIServiceType]:
        """Get service priority using functional approach."""
        service_configs = [
            (AIServiceType.OLLAMA, "OLLAMA_BASE_URL"),
            (AIServiceType.OPENAI, "OPENAI_API_KEY"),
            (AIServiceType.ANTHROPIC, "ANTHROPIC_API_KEY")
        ]
        
        # Filter services based on configuration
        available_services = [
            service_type for service_type, env_var in service_configs
            if os.getenv(env_var)
        ]
        
        # Default to Ollama if nothing configured
        return available_services or [AIServiceType.OLLAMA]
    
    def _init_external_services(self):
        """Initialize external AI service clients with better error handling."""
        self.openai_client = ServiceInitializer.init_openai_client()
        self.anthropic_client = ServiceInitializer.init_anthropic_client()
    
    def generate_interview_questions(self, role: str, job_description: str, 
                                   preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Generate questions using question bank first, then AI services as fallback."""
        
        # Try question bank first
        if result := self._try_question_bank(role, job_description):
            return result
        
        # Try AI services with simplified fallback
        return self._try_ai_services("generate_interview_questions", role, job_description, preferred_service)
    
    def analyze_answer(self, job_description: str, question: str, answer: str,
                      preferred_service: Optional[str] = None) -> AnalyzeAnswerResponse:
        """Analyze answer using the best available service."""
        return self._try_ai_services("analyze_answer", job_description, question, answer, preferred_service)
    
    def _get_services_to_try(self, preferred_service: Optional[str] = None) -> List[AIServiceType]:
        """Get services to try using functional approach."""
        if not preferred_service:
            return self.service_priority
        
        # Find preferred service using functional approach
        preferred = next(
            (s for s in AIServiceType if s.value == preferred_service.lower()), 
            None
        )
        
        if not preferred:
            return self.service_priority
        
        # Return preferred first, then others
        return [preferred] + [s for s in self.service_priority if s != preferred]
    
    def _try_question_bank(self, role: str, job_description: str) -> Optional[ParseJDResponse]:
        """Extract question bank logic into separate method."""
        if not self.question_bank_service:
            return None
        
        try:
            questions = self.question_bank_service.get_questions_for_role(role, job_description, count=10)
            if questions:
                question_texts = [q.question_text for q in questions]
                logger.info(f"Retrieved {len(question_texts)} questions from question bank for role '{role}'")
                return ParseJDResponse(questions=question_texts)
            else:
                logger.info(f"No questions found in question bank for role '{role}', falling back to AI generation")
        except Exception as e:
            logger.warning(f"Error accessing question bank: {e}, falling back to AI generation")
        
        return None
    
    def _try_ai_services(self, method: str, *args, **kwargs) -> ParseJDResponse:
        """Simplified AI service orchestration with early returns."""
        preferred_service = kwargs.pop('preferred_service', None) if 'preferred_service' in kwargs else None
        services_to_try = self._get_services_to_try(preferred_service)
        
        for service_type in services_to_try:
            try:
                result = self._call_ai_service(service_type, method, *args, **kwargs)
                self._store_generated_questions_if_needed(result, method, *args, **kwargs)
                return result
            except ServiceUnavailableError as e:
                logger.warning(f"Error with {service_type.value}: {e}")
                continue
        
        # Return appropriate fallback based on method
        if method == "generate_interview_questions":
            return FallbackResponses.get_fallback_questions(args[0] if args else "unknown")
        else:
            return FallbackResponses.get_fallback_analysis()
    
    def _store_generated_questions_if_needed(self, result: ParseJDResponse, method: str, *args, **kwargs):
        """Store generated questions in question bank if applicable."""
        if (method == "generate_interview_questions" and 
            self.question_bank_service and 
            result.questions and 
            len(args) >= 2):
            
            try:
                role, job_description = args[0], args[1]
                prompt_hash = self._generate_prompt_hash(role, job_description)
                self.question_bank_service.store_generated_questions(
                    questions=result.questions,
                    role=role,
                    job_description=job_description,
                    ai_service_used="hybrid",  # We don't know which specific service succeeded
                    prompt_hash=prompt_hash
                )
                logger.info(f"Stored {len(result.questions)} AI-generated questions in question bank")
            except Exception as e:
                logger.warning(f"Error storing questions in question bank: {e}")
    
    def _call_ai_service(self, service_type: AIServiceType, method: str, *args, **kwargs):
        """Generic method to call AI services with consistent error handling."""
        service_config = {
            AIServiceType.OPENAI: (self.openai_client, f"_{method}_openai"),
            AIServiceType.ANTHROPIC: (self.anthropic_client, f"_{method}_anthropic"),
            AIServiceType.OLLAMA: (self.ollama_service, method)
        }
        
        client, method_name = service_config.get(service_type)
        if not client:
            raise ServiceUnavailableError(f"{service_type.value} client not initialized")
        
        try:
            return getattr(client, method_name)(*args, **kwargs)
        except ServiceUnavailableError:
            raise
        except Exception as e:
            logger.warning(f"Error with {service_type.value} for {method}: {e}")
            raise ServiceUnavailableError(f"{service_type.value} service error: {e}")
    
    def _generate_questions_openai(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate questions using OpenAI."""
        if not self.openai_client:
            raise ServiceUnavailableError("OpenAI client not initialized")
        
        user_prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            messages=[
                {"role": "system", "content": PromptTemplates.QUESTION_GENERATION_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content.strip()
        questions = ResponseParsers.parse_questions_from_response(questions_text)
        
        return ParseJDResponse(questions=questions)
    
    def _generate_questions_anthropic(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate questions using Anthropic Claude."""
        if not self.anthropic_client:
            raise ServiceUnavailableError("Anthropic client not initialized")
        
        user_prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
        
        response = self.anthropic_client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            max_tokens=1000,
            system=PromptTemplates.QUESTION_GENERATION_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        questions_text = response.content[0].text.strip()
        questions = ResponseParsers.parse_questions_from_response(questions_text)
        
        return ParseJDResponse(questions=questions)
    
    def _analyze_answer_openai(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze answer using OpenAI."""
        if not self.openai_client:
            raise ServiceUnavailableError("OpenAI client not initialized")
        
        user_prompt = PromptTemplates.get_analysis_prompt(job_description, question, answer)
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            messages=[
                {"role": "system", "content": PromptTemplates.ANALYSIS_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        analysis_text = response.choices[0].message.content.strip()
        return ResponseParsers.parse_analysis_response(analysis_text)
    
    def _analyze_answer_anthropic(self, job_description: str, question: str, answer: str) -> AnalyzeAnswerResponse:
        """Analyze answer using Anthropic Claude."""
        if not self.anthropic_client:
            raise ServiceUnavailableError("Anthropic client not initialized")
        
        user_prompt = PromptTemplates.get_analysis_prompt(job_description, question, answer)
        
        response = self.anthropic_client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            max_tokens=1500,
            system=PromptTemplates.ANALYSIS_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        analysis_text = response.content[0].text.strip()
        return ResponseParsers.parse_analysis_response(analysis_text)
    
    
    def get_available_services(self) -> Dict[str, bool]:
        """Get status of available AI services."""
        return {
            "ollama": bool(os.getenv("OLLAMA_BASE_URL")),
            "openai": bool(os.getenv("OPENAI_API_KEY") and self.openai_client is not None),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY") and self.anthropic_client is not None)
        }
    
    def get_service_priority(self) -> List[str]:
        """Get current service priority order."""
        return [service.value for service in self.service_priority]
    
    def _generate_prompt_hash(self, role: str, job_description: str) -> str:
        """Generate a hash for the prompt to identify similar requests."""
        prompt_data = f"{role}:{job_description}"
        return hashlib.sha256(prompt_data.encode()).hexdigest()
    
    def get_question_bank_stats(self) -> Dict[str, Any]:
        """Get question bank statistics."""
        if self.question_bank_service:
            return self.question_bank_service.get_question_bank_stats()
        return {} 