import os
import json
import requests
from typing import List, Dict, Any, Optional
from enum import Enum
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.services.ollama_service import OllamaService
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
    def __init__(self):
        self.ollama_service = OllamaService()
        self.service_priority = self._get_service_priority()
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize external services if configured
        self._init_external_services()
    
    def _get_service_priority(self) -> List[AIServiceType]:
        """Get service priority based on configuration."""
        priority = []
        
        # Check which services are configured
        if os.getenv("OLLAMA_BASE_URL"):
            priority.append(AIServiceType.OLLAMA)
        
        if os.getenv("OPENAI_API_KEY"):
            priority.append(AIServiceType.OPENAI)
        
        if os.getenv("ANTHROPIC_API_KEY"):
            priority.append(AIServiceType.ANTHROPIC)
        
        # Default to Ollama if nothing configured
        if not priority:
            priority.append(AIServiceType.OLLAMA)
        
        return priority
    
    def _init_external_services(self):
        """Initialize external AI service clients with better error handling."""
        self.openai_client = ServiceInitializer.init_openai_client()
        self.anthropic_client = ServiceInitializer.init_anthropic_client()
    
    def generate_interview_questions(self, role: str, job_description: str, 
                                   preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Generate questions using the best available service."""
        
        services_to_try = self._get_services_to_try(preferred_service)
        
        for service_type in services_to_try:
            try:
                return self._call_ai_service(service_type, "generate_interview_questions", role, job_description)
            except ServiceUnavailableError as e:
                logger.warning(f"Error with {service_type.value}: {e}")
                continue
        
        # If all services fail, return fallback
        return FallbackResponses.get_fallback_questions(role)
    
    def analyze_answer(self, job_description: str, question: str, answer: str,
                      preferred_service: Optional[str] = None) -> AnalyzeAnswerResponse:
        """Analyze answer using the best available service."""
        
        services_to_try = self._get_services_to_try(preferred_service)
        
        for service_type in services_to_try:
            try:
                return self._call_ai_service(service_type, "analyze_answer", job_description, question, answer)
            except ServiceUnavailableError as e:
                logger.warning(f"Error with {service_type.value}: {e}")
                continue
        
        # If all services fail, return fallback
        return FallbackResponses.get_fallback_analysis()
    
    def _get_services_to_try(self, preferred_service: Optional[str] = None) -> List[AIServiceType]:
        """Get list of services to try in order."""
        if not preferred_service:
            return self.service_priority
        
        # Find preferred service
        preferred = next(
            (s for s in AIServiceType if s.value == preferred_service.lower()), 
            None
        )
        
        if not preferred:
            return self.service_priority
        
        # Return preferred first, then others
        return [preferred] + [s for s in self.service_priority if s != preferred]
    
    def _call_ai_service(self, service_type: AIServiceType, method: str, *args, **kwargs):
        """Generic method to call AI services with consistent error handling."""
        try:
            if service_type == AIServiceType.OPENAI:
                if not self.openai_client:
                    raise ServiceUnavailableError("OpenAI client not initialized")
                return getattr(self, f"_{method}_openai")(*args, **kwargs)
            elif service_type == AIServiceType.ANTHROPIC:
                if not self.anthropic_client:
                    raise ServiceUnavailableError("Anthropic client not initialized")
                return getattr(self, f"_{method}_anthropic")(*args, **kwargs)
            elif service_type == AIServiceType.OLLAMA:
                return getattr(self.ollama_service, method)(*args, **kwargs)
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