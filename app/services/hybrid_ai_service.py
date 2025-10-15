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
from app.services.role_analysis_service import RoleAnalysisService
from app.services.dynamic_prompt_service import DynamicPromptService
from app.services.intelligent_question_selector import IntelligentQuestionSelector, UserContext
from app.services.ai_fallback_service import AIFallbackService
from app.utils.prompt_templates import PromptTemplates
from app.utils.response_parsers import ResponseParsers
from app.utils.service_initializer import ServiceInitializer
from app.utils.fallback_responses import FallbackResponses
from app.utils.cache import cached
from app.utils.metrics import metrics
from app.utils.logger import get_logger
from app.exceptions import ServiceUnavailableError
from app.config import get_settings
import time

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
        self.settings = get_settings()
        
        # Initialize question bank service if database session is available
        self.question_bank_service = None
        if self.db_session:
            self.question_bank_service = QuestionBankService(self.db_session)
        
        # Initialize role analysis and dynamic prompt services
        self.role_analysis_service = RoleAnalysisService()
        self.dynamic_prompt_service = DynamicPromptService()
        
        # Initialize intelligent selection services
        self.intelligent_selector = IntelligentQuestionSelector(db_session)
        self.ai_fallback_service = AIFallbackService(db_session)
        
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
    
    @cached("question_generation", ttl=3600, cache_key_params=["role", "job_description", "preferred_service"])
    def generate_interview_questions(self, role: str, job_description: str, 
                                   preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Generate questions using dynamic prompts and role analysis."""
        start_time = time.time()
        
        try:
            # Perform role analysis
            try:
                analysis = self.role_analysis_service.analyze_role(role, job_description)
                logger.info(f"Role analysis completed: {analysis.industry.value}, {analysis.job_function.value}, {analysis.seniority_level.value}")
            except Exception as e:
                logger.error(f"Role analysis failed: {e}")
                # Fallback to original method
                result = self._generate_interview_questions_fallback(role, job_description, preferred_service)
                # Record metrics for fallback
                duration = time.time() - start_time
                metrics.record_ai_service_request(
                    service="fallback",
                    operation="generate_interview_questions",
                    status="success",
                    duration=duration
                )
                return result
            
            # Try question bank first with role analysis
            if result := self._try_question_bank_with_analysis(role, job_description, analysis):
                # Record metrics for question bank
                duration = time.time() - start_time
                metrics.record_ai_service_request(
                    service="question_bank",
                    operation="generate_interview_questions",
                    status="success",
                    duration=duration
                )
                return result
            
            # Generate dynamic prompt based on role analysis
            try:
                dynamic_prompt = self.dynamic_prompt_service.generate_question_prompt(
                    role, job_description, analysis
                )
                logger.info(f"Generated dynamic prompt for {analysis.industry.value} {analysis.job_function.value}")
            except Exception as e:
                logger.error(f"Dynamic prompt generation failed: {e}")
                # Fallback to template prompt
                dynamic_prompt = PromptTemplates.get_question_generation_prompt(role, job_description)
            
            # Try AI services with dynamic prompt
            result = self._try_ai_services_with_dynamic_prompt("generate_interview_questions", role, job_description, dynamic_prompt, analysis, preferred_service)
            
            # Record metrics for AI service
            duration = time.time() - start_time
            service_name = preferred_service or "auto"
            metrics.record_ai_service_request(
                service=service_name,
                operation="generate_interview_questions",
                status="success",
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            service_name = preferred_service or "auto"
            metrics.record_ai_service_request(
                service=service_name,
                operation="generate_interview_questions",
                status="error",
                duration=duration
            )
            raise
    
    def _generate_interview_questions_fallback(self, role: str, job_description: str, 
                                             preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Fallback method when role analysis fails."""
        # Try question bank first
        if result := self._try_question_bank(role, job_description):
            return result
        
        # Try AI services with simplified fallback
        return self._try_ai_services("generate_interview_questions", role, job_description, preferred_service)
    
    @cached("answer_analysis", ttl=1800, cache_key_params=["job_description", "question", "answer", "preferred_service"])
    def analyze_answer(self, job_description: str, question: str, answer: str,
                      preferred_service: Optional[str] = None) -> AnalyzeAnswerResponse:
        """Analyze answer using the best available service."""
        start_time = time.time()
        
        try:
            result = self._try_ai_services("analyze_answer", job_description, question, answer, preferred_service)
            
            # Record metrics for AI service
            duration = time.time() - start_time
            service_name = preferred_service or "auto"
            metrics.record_ai_service_request(
                service=service_name,
                operation="analyze_answer",
                status="success",
                duration=duration
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            service_name = preferred_service or "auto"
            metrics.record_ai_service_request(
                service=service_name,
                operation="analyze_answer",
                status="error",
                duration=duration
            )
            raise
    
    async def generate_intelligent_questions(self, 
                                           role: str, 
                                           job_description: str,
                                           user_context: Optional[UserContext] = None,
                                           target_count: int = 10) -> Dict[str, Any]:
        """Generate questions using intelligent selection with AI fallback."""
        try:
            logger.info(f"Starting intelligent question generation for role: {role}")
            
            # Use intelligent question selector
            selection_result = await self.intelligent_selector.select_questions(
                role=role,
                job_description=job_description,
                user_context=user_context,
                target_count=target_count
            )
            
            # Convert to response format
            questions = [q.question_text for q in selection_result.questions]
            
            # Create response similar to ParseJDResponse
            response = {
                "questions": questions,
                "source": selection_result.source,
                "database_hit_rate": selection_result.database_hit_rate,
                "ai_generated_count": selection_result.ai_generated_count,
                "diversity_score": selection_result.diversity_score,
                "selection_time": selection_result.selection_time,
                "role_analysis": {
                    "primary_role": selection_result.role_analysis.primary_role,
                    "industry": selection_result.role_analysis.industry.value,
                    "seniority_level": selection_result.role_analysis.seniority_level.value,
                    "required_skills": selection_result.role_analysis.required_skills,
                    "tech_stack": selection_result.role_analysis.tech_stack
                } if selection_result.role_analysis else None
            }
            
            logger.info(f"Intelligent question generation completed: "
                       f"{len(questions)} questions, "
                       f"database hit rate: {selection_result.database_hit_rate:.2%}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in intelligent question generation: {e}")
            # Fallback to traditional AI generation
            return await self._fallback_to_traditional_generation(role, job_description, target_count)
    
    async def _fallback_to_traditional_generation(self, 
                                                role: str, 
                                                job_description: str, 
                                                target_count: int) -> Dict[str, Any]:
        """Fallback to traditional AI generation when intelligent selection fails."""
        try:
            # Use existing generate_interview_questions method
            response = self.generate_interview_questions(role, job_description)
            
            return {
                "questions": response.questions[:target_count],
                "source": "ai_fallback",
                "database_hit_rate": 0.0,
                "ai_generated_count": len(response.questions[:target_count]),
                "diversity_score": 0.5,  # Default diversity score
                "selection_time": 0.0,
                "role_analysis": None
            }
            
        except Exception as e:
            logger.error(f"Error in fallback generation: {e}")
            return {
                "questions": [],
                "source": "error",
                "database_hit_rate": 0.0,
                "ai_generated_count": 0,
                "diversity_score": 0.0,
                "selection_time": 0.0,
                "role_analysis": None
            }
    
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
    
    def _try_question_bank_with_analysis(self, role: str, job_description: str, analysis) -> Optional[ParseJDResponse]:
        """Try question bank with role analysis."""
        if not self.question_bank_service:
            return None
        
        try:
            # Try to get questions based on role analysis
            questions = self.question_bank_service.get_questions_for_role_with_analysis(
                role, analysis, count=10
            )
            if questions:
                question_texts = [q.question_text for q in questions]
                logger.info(f"Retrieved {len(question_texts)} questions from question bank for role '{role}' with analysis")
                return ParseJDResponse(
                    questions=question_texts,
                    metadata={
                        "source": "question_bank",
                        "role_analysis": self.role_analysis_service.get_analysis_summary(analysis)
                    }
                )
            else:
                logger.info(f"No questions found in question bank for role '{role}' with analysis, falling back to AI generation")
        except Exception as e:
            logger.warning(f"Error accessing question bank with analysis: {e}, falling back to AI generation")
        
        return None
    
    def _try_ai_services_generic(self, method: str, services_to_try: List[AIServiceType], 
                                call_func, store_func, fallback_func, *args, **kwargs) -> ParseJDResponse:
        """Generic AI service orchestration with configurable call/store/fallback functions."""
        for service_type in services_to_try:
            try:
                result = call_func(service_type, method, *args, **kwargs)
                store_func(result, method, *args, **kwargs)
                return result
            except ServiceUnavailableError as e:
                logger.warning(f"Error with {service_type.value}: {e}")
                continue
        
        return fallback_func(*args, **kwargs)
    
    def _try_ai_services(self, method: str, *args, **kwargs) -> ParseJDResponse:
        """Simplified AI service orchestration with early returns."""
        preferred_service = kwargs.pop('preferred_service', None) if 'preferred_service' in kwargs else None
        services_to_try = self._get_services_to_try(preferred_service)
        
        def fallback_func(*args, **kwargs):
            if method == "generate_interview_questions":
                return FallbackResponses.get_fallback_questions(args[0] if args else "unknown")
            else:
                return FallbackResponses.get_fallback_analysis()
        
        return self._try_ai_services_generic(
            method, services_to_try, 
            self._call_ai_service, 
            self._store_generated_questions_if_needed,
            fallback_func,
            *args, **kwargs
        )
    
    def _try_ai_services_with_dynamic_prompt(self, method: str, role: str, job_description: str, 
                                           dynamic_prompt: str, analysis, preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Try AI services with dynamic prompt and role analysis."""
        services_to_try = self._get_services_to_try(preferred_service)
        
        def fallback_func(*args, **kwargs):
            fallback_questions = FallbackResponses.get_fallback_questions(role)
            return ParseJDResponse(
                questions=fallback_questions,
                metadata={
                    "source": "fallback",
                    "role_analysis": self.role_analysis_service.get_analysis_summary(analysis)
                }
            )
        
        return self._try_ai_services_generic(
            method, services_to_try,
            self._call_ai_service_with_dynamic_prompt,
            lambda result, method, *args, **kwargs: self._store_generated_questions_with_analysis(result, role, job_description, analysis),
            fallback_func,
            dynamic_prompt
        )
    
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
    
    def _store_generated_questions_with_analysis(self, result: ParseJDResponse, role: str, 
                                               job_description: str, analysis):
        """Store generated questions with role analysis."""
        if (self.question_bank_service and result.questions):
            try:
                self.question_bank_service.store_questions_for_role_with_analysis(
                    role, result.questions, job_description, analysis
                )
                logger.info(f"Stored {len(result.questions)} AI-generated questions with role analysis")
            except Exception as e:
                logger.warning(f"Error storing questions with analysis: {e}")
    
    def _call_ai_service_with_dynamic_prompt(self, service_type: AIServiceType, method: str, dynamic_prompt: str):
        """Call AI service with dynamic prompt."""
        if service_type == AIServiceType.OPENAI:
            return self._generate_questions_with_dynamic_prompt_openai(dynamic_prompt)
        elif service_type == AIServiceType.ANTHROPIC:
            return self._generate_questions_with_dynamic_prompt_anthropic(dynamic_prompt)
        elif service_type == AIServiceType.OLLAMA:
            return self.ollama_service.generate_interview_questions(dynamic_prompt)
        else:
            raise ServiceUnavailableError(f"Unknown service type: {service_type}")
    
    def _generate_questions_with_dynamic_prompt_openai(self, dynamic_prompt: str) -> ParseJDResponse:
        """Generate questions using OpenAI with dynamic prompt."""
        if not self.openai_client:
            raise ServiceUnavailableError("OpenAI client not initialized")
        
        response = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
            messages=[
                {"role": "system", "content": "You are an expert interview question generator. Generate high-quality, relevant interview questions based on the provided prompt."},
                {"role": "user", "content": dynamic_prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        questions_text = response.choices[0].message.content.strip()
        questions = ResponseParsers.parse_questions_from_response(questions_text)
        
        return ParseJDResponse(questions=questions)
    
    def _generate_questions_with_dynamic_prompt_anthropic(self, dynamic_prompt: str) -> ParseJDResponse:
        """Generate questions using Anthropic with dynamic prompt."""
        if not self.anthropic_client:
            raise ServiceUnavailableError("Anthropic client not initialized")
        
        response = self.anthropic_client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
            max_tokens=1000,
            system="You are an expert interview question generator. Generate high-quality, relevant interview questions based on the provided prompt.",
            messages=[{"role": "user", "content": dynamic_prompt}]
        )
        
        questions_text = response.content[0].text.strip()
        questions = ResponseParsers.parse_questions_from_response(questions_text)
        
        return ParseJDResponse(questions=questions)
    
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