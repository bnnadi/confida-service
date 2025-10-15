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
from app.services.ai_service_orchestrator import AIServiceOrchestrator, AIServiceType
from app.services.service_factory import ServiceFactory
from app.services.smart_token_optimizer import SmartTokenOptimizer
from app.services.cost_tracker import CostTracker
from app.utils.prompt_templates import PromptTemplates
from app.utils.response_parsers import ResponseParsers
from app.utils.ai_request_handler import AIRequestHandler
from app.utils.service_initializer import ServiceInitializer
from app.utils.fallback_responses import FallbackResponses
from app.utils.cache import cached
from app.utils.metrics import metrics
from app.utils.metrics_decorator import with_metrics, with_error_handling
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
        self.db_session = db_session
        self.settings = get_settings()
        
        # Use factory pattern for service initialization
        self._services = ServiceFactory.create_services(db_session, self.settings)
        self._orchestrator = ServiceFactory.create_orchestrator(self._services)
        
        # Initialize token optimization and cost tracking
        self.token_optimizer = SmartTokenOptimizer()
        self.cost_tracker = CostTracker(db_session)
        
        # Initialize unified AI request handler
        self.ai_request_handler = AIRequestHandler()
        
        # Assign services to instance variables for backward compatibility
        self._assign_services()
    
    def _assign_services(self):
        """Assign services from factory to instance variables for backward compatibility."""
        self.ollama_service = self._services['ollama_service']
        self.openai_client = self._services['openai_client']
        self.anthropic_client = self._services['anthropic_client']
        self.question_bank_service = self._services['question_bank_service']
        self.role_analysis_service = self._services['role_analysis_service']
        self.dynamic_prompt_service = self._services['dynamic_prompt_service']
        self.intelligent_selector = self._services['intelligent_selector']
        self.ai_fallback_service = self._services['ai_fallback_service']
        self.service_priority = self._services['service_priority']
        self.orchestrator = self._orchestrator
        
        # Set clients in the unified request handler
        self.ai_request_handler.set_client('openai', self.openai_client)
        self.ai_request_handler.set_client('anthropic', self.anthropic_client)
    
    @cached("question_generation", ttl=3600, cache_key_params=["role", "job_description", "preferred_service"])
    @with_metrics("generate_interview_questions")
    def generate_interview_questions(self, role: str, job_description: str, 
                                   preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Generate questions using dynamic prompts and role analysis."""
        # Get role analysis with fallback
        analysis = self._get_role_analysis(role, job_description)
        
        # Try question bank first with role analysis
        if result := self._try_question_bank_with_analysis(role, job_description, analysis):
            return result
        
        # Generate dynamic prompt based on role analysis
        dynamic_prompt = self._get_dynamic_prompt(role, job_description, analysis)
        
        # Try AI services with dynamic prompt
        return self._try_ai_services_with_dynamic_prompt("generate_interview_questions", role, job_description, dynamic_prompt, analysis, preferred_service)
    
    @with_error_handling(fallback_func=lambda role, job_desc: self._generate_interview_questions_fallback(role, job_desc))
    def _get_role_analysis(self, role: str, job_description: str):
        """Get role analysis with error handling."""
        analysis = self.role_analysis_service.analyze_role(role, job_description)
        logger.info(f"Role analysis completed: {analysis.industry.value}, {analysis.job_function.value}, {analysis.seniority_level.value}")
        return analysis
    
    @with_error_handling(fallback_func=lambda role, job_desc, analysis: PromptTemplates.get_question_generation_prompt(role, job_description))
    def _get_dynamic_prompt(self, role: str, job_description: str, analysis):
        """Get dynamic prompt with fallback to template."""
        dynamic_prompt = self.dynamic_prompt_service.generate_question_prompt(role, job_description, analysis)
        logger.info(f"Generated dynamic prompt for {analysis.industry.value} {analysis.job_function.value}")
        return dynamic_prompt
    
    def _generate_interview_questions_fallback(self, role: str, job_description: str, 
                                             preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Fallback method when role analysis fails."""
        # Try question bank first
        if result := self._try_question_bank(role, job_description):
            return result
        
        # Try AI services with simplified fallback
        return self._try_ai_services("generate_interview_questions", role, job_description, preferred_service)
    
    @cached("answer_analysis", ttl=1800, cache_key_params=["job_description", "question", "answer", "preferred_service"])
    @with_metrics("analyze_answer")
    def analyze_answer(self, job_description: str, question: str, answer: str,
                      preferred_service: Optional[str] = None) -> AnalyzeAnswerResponse:
        """Analyze answer using the best available service."""
        return self._try_ai_services("analyze_answer", job_description, question, answer, preferred_service)
    
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
    
    def _try_ai_services(self, method: str, *args, **kwargs) -> ParseJDResponse:
        """Simplified AI service orchestration using the orchestrator."""
        preferred_service = kwargs.pop('preferred_service', None) if 'preferred_service' in kwargs else None
        
        # Use the orchestrator for clean service management
        result = self.orchestrator.try_services(method, preferred_service=preferred_service, *args, **kwargs)
        
        # Store generated questions if needed
        if result and method == "generate_interview_questions":
            self._store_generated_questions_if_needed(result, method, *args, **kwargs)
        
        return result
    
    def _try_ai_services_with_dynamic_prompt(self, method: str, role: str, job_description: str, 
                                           dynamic_prompt: str, analysis, preferred_service: Optional[str] = None) -> ParseJDResponse:
        """Try AI services with dynamic prompt and role analysis."""
        # Use the orchestrator with dynamic prompt
        result = self.orchestrator.try_services(
            method, 
            preferred_service=preferred_service,
            role=role,
            job_description=job_description,
            dynamic_prompt=dynamic_prompt,
            analysis=analysis
        )
        
        # Store generated questions if needed
        if result and method == "generate_interview_questions":
            self._store_generated_questions_with_analysis(result, role, job_description, analysis)
        
        return result
    
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
    
    def _generate_questions_with_service(self, service_type: str, role: str, job_description: str) -> ParseJDResponse:
        """Unified question generation for all AI services."""
        service_config = {
            "openai": {
                "create_method": self._create_ai_request,
                "parse_method": self._parse_openai_response
            },
            "anthropic": {
                "create_method": self._create_ai_request,
                "parse_method": self._parse_anthropic_response
            }
        }
        
        config = service_config[service_type]
        
        # Optimize token usage
        optimization_result = self.token_optimizer.optimize_request(
            role, job_description, service_type, 10
        )
        
        try:
            # Create and execute request
            response = config["create_method"](service_type, optimization_result.optimal_tokens, role, job_description)
            questions = config["parse_method"](response)
            
            # Track success
            self._track_successful_request(service_type, optimization_result, response, role)
            return ParseJDResponse(questions=questions)
            
        except Exception as e:
            # Track failure
            self._track_failed_request(service_type, optimization_result, role, str(e))
            raise
    
    def _create_ai_request(self, service_type: str, max_tokens: int, role: str, job_description: str):
        """Create unified AI request using the request handler."""
        return self.ai_request_handler.create_request(service_type, max_tokens, role, job_description)
    
    def _parse_openai_response(self, response) -> List[Dict[str, Any]]:
        """Parse OpenAI response."""
        questions_text = response.choices[0].message.content.strip()
        return ResponseParsers.parse_questions_from_response(questions_text)
    
    def _parse_anthropic_response(self, response) -> List[Dict[str, Any]]:
        """Parse Anthropic response."""
        questions_text = response.content[0].text.strip()
        return ResponseParsers.parse_questions_from_response(questions_text)
    
    def _track_successful_request(self, service_type: str, optimization_result, response, role: str):
        """Track successful AI service request."""
        from app.services.cost_tracker import CostTrackingRequest
        
        actual_tokens = self._get_actual_tokens(service_type, response)
        request = CostTrackingRequest(
            service=service_type,
            operation="generate_questions",
            tokens_used=actual_tokens,
            estimated_cost=optimization_result.estimated_cost,
            role=role,
            complexity_score=optimization_result.complexity_score,
            optimization_applied=optimization_result.optimization_applied,
            success=True
        )
        self.cost_tracker.track_request(request)
    
    def _track_failed_request(self, service_type: str, optimization_result, role: str, error_message: str):
        """Track failed AI service request."""
        from app.services.cost_tracker import CostTrackingRequest
        
        request = CostTrackingRequest(
            service=service_type,
            operation="generate_questions",
            tokens_used=0,
            estimated_cost=0.0,
            role=role,
            complexity_score=optimization_result.complexity_score,
            optimization_applied=optimization_result.optimization_applied,
            success=False,
            error_message=error_message
        )
        self.cost_tracker.track_request(request)
    
    def _get_actual_tokens(self, service_type: str, response) -> int:
        """Get actual tokens used from response."""
        if service_type == "openai" and hasattr(response, 'usage'):
            return response.usage.total_tokens
        elif service_type == "anthropic" and hasattr(response, 'usage'):
            return response.usage.input_tokens + response.usage.output_tokens
        return 0

    def _generate_questions_openai(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate questions using OpenAI with token optimization."""
        return self._generate_questions_with_service("openai", role, job_description)
    
    def _generate_questions_anthropic(self, role: str, job_description: str) -> ParseJDResponse:
        """Generate questions using Anthropic Claude with token optimization."""
        return self._generate_questions_with_service("anthropic", role, job_description)
    
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