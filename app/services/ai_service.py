"""
Unified AI Service for Confida

This service provides a unified interface for all AI operations with comprehensive
error handling, retry logic, circuit breaker patterns, and intelligent fallbacks.
"""
import asyncio
import time
from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass
from app.services.ollama_service import OllamaService
from app.services.question_service import QuestionService
from app.services.multi_agent_scoring import get_multi_agent_scoring_service
from app.utils.logger import get_logger
from app.utils.error_handling import ErrorHandlingService
from app.utils.fallback import get_fallback_response
from app.exceptions import ServiceUnavailableError

logger = get_logger(__name__)

class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"

class ErrorType(Enum):
    """Error classification for intelligent retry strategies."""
    TRANSIENT = "transient"  # Network, timeout, rate limit
    PERMANENT = "permanent"  # Authentication, invalid request
    SERVICE_UNAVAILABLE = "service_unavailable"  # Service down
    QUOTA_EXCEEDED = "quota_exceeded"  # Rate limit, quota

@dataclass
class ServiceHealth:
    """Service health information."""
    status: ServiceStatus
    last_check: float
    consecutive_failures: int
    circuit_breaker_threshold: int = 5
    recovery_timeout: float = 60.0

@dataclass
class RetryConfig:
    """Retry configuration for different error types."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True

class CircuitBreaker:
    """Circuit breaker implementation for service protection."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = ServiceStatus.HEALTHY
    
    def can_execute(self) -> bool:
        """Check if service can execute based on circuit breaker state."""
        if self.state == ServiceStatus.HEALTHY:
            return True
        elif self.state == ServiceStatus.CIRCUIT_OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = ServiceStatus.HEALTHY
                self.failure_count = 0
                logger.info("Circuit breaker: Attempting recovery")
                return True
            return False
        return True
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = ServiceStatus.HEALTHY
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = ServiceStatus.CIRCUIT_OPEN
            logger.warning(f"Circuit breaker: Service marked as unhealthy after {self.failure_count} failures")

class UnifiedAIService:
    """
    Unified AI service with comprehensive error handling and retry logic.
    
    Features:
    - Circuit breaker pattern for service protection
    - Intelligent error classification and retry strategies
    - Multiple AI service fallbacks
    - Comprehensive logging and monitoring
    - Graceful degradation
    """
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.ollama_service = OllamaService()
        self.question_service = QuestionService(db_session) if db_session else None
        self.error_handler = ErrorHandlingService()
        
        # Circuit breakers for each service
        self.circuit_breakers = {
            "ollama": self.error_handler.create_circuit_breaker(failure_threshold=5, recovery_timeout=60.0),
            "multi_agent": self.error_handler.create_circuit_breaker(failure_threshold=3, recovery_timeout=30.0),
            "question_service": self.error_handler.create_circuit_breaker(failure_threshold=3, recovery_timeout=30.0)
        }
        
        # Retry configurations for different error types
        self.retry_configs = {
            ErrorType.TRANSIENT: RetryConfig(max_retries=3, base_delay=1.0, backoff_factor=2.0),
            ErrorType.SERVICE_UNAVAILABLE: RetryConfig(max_retries=2, base_delay=2.0, backoff_factor=3.0),
            ErrorType.QUOTA_EXCEEDED: RetryConfig(max_retries=1, base_delay=5.0, backoff_factor=1.0),
            ErrorType.PERMANENT: RetryConfig(max_retries=0, base_delay=0.0, backoff_factor=1.0)
        }
        
        # Service health tracking
        self.service_health = {
            "ollama": ServiceHealth(ServiceStatus.HEALTHY, time.time(), 0),
            "multi_agent": ServiceHealth(ServiceStatus.HEALTHY, time.time(), 0),
            "question_service": ServiceHealth(ServiceStatus.HEALTHY, time.time(), 0)
        }
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type for retry strategies using unified error handler."""
        error_type = self.error_handler.classify_error(error)
        
        # Map unified error types to internal error types
        type_mapping = {
            "transient": ErrorType.TRANSIENT,
            "service_unavailable": ErrorType.SERVICE_UNAVAILABLE,
            "quota_exceeded": ErrorType.QUOTA_EXCEEDED,
            "permanent": ErrorType.PERMANENT,
            "unknown": ErrorType.TRANSIENT
        }
        
        return type_mapping.get(error_type, ErrorType.TRANSIENT)
    
    def _calculate_retry_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        delay = min(config.base_delay * (config.backoff_factor ** attempt), config.max_delay)
        
        if config.jitter:
            # Add jitter to prevent thundering herd
            import random
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay
    
    async def _execute_with_retry(self, operation, service_name: str, *args, **kwargs):
        """Execute operation with simplified retry logic."""
        circuit_breaker = self.circuit_breakers[service_name]
        
        if not circuit_breaker.can_execute():
            raise ServiceUnavailableError(f"Service {service_name} is currently unavailable")
        
        error_type = ErrorType.TRANSIENT  # Default to transient for retries
        retry_config = self.retry_configs[error_type]
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                # Record success
                circuit_breaker.record_success()
                self.service_health[service_name].consecutive_failures = 0
                self.service_health[service_name].status = ServiceStatus.HEALTHY
                return result
                
            except Exception as e:
                circuit_breaker.record_failure()
                self.service_health[service_name].consecutive_failures += 1
                
                if attempt < retry_config.max_retries:
                    delay = self._calculate_retry_delay(attempt, retry_config)
                    logger.warning(f"Service {service_name} failed (attempt {attempt + 1}), retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    self.service_health[service_name].status = ServiceStatus.UNHEALTHY
                    logger.error(f"Service {service_name} failed after {retry_config.max_retries + 1} attempts")
                    raise e
    
    async def generate_questions(self, role: str, job_description: str, count: int = 10) -> List[Dict[str, Any]]:
        """Generate questions with intelligent fallback strategy."""
        try:
            # Try question service first (database-first approach)
            if self.question_service and self.circuit_breakers["question_service"].can_execute():
                try:
                    return await self._execute_with_retry(
                        self.question_service.generate_questions,
                        "question_service",
                        role, job_description, count
                    )
                except Exception as e:
                    logger.warning(f"Question service failed, falling back to Ollama: {e}")
            
            # Fallback to Ollama service
            if self.circuit_breakers["ollama"].can_execute():
                try:
                    ollama_response = await self._execute_with_retry(
                        self.ollama_service.generate_interview_questions,
                        "ollama",
                        role, job_description
                    )
                    
                    # Convert to expected format
                    return [
                        {
                            "id": f"ollama_{i}",
                            "text": question,
                            "type": "generated",
                            "source": "ollama",
                            "metadata": {"service": "ollama"}
                        }
                        for i, question in enumerate(ollama_response.questions)
                    ]
                except Exception as e:
                    logger.warning(f"Ollama service failed: {e}")
            
            # Final fallback - return generic questions
            logger.warning("All AI services failed, returning fallback questions")
            return self._get_fallback_questions(role, count)
            
        except Exception as e:
            logger.error(f"All question generation methods failed: {e}")
            return self._get_fallback_questions(role, count)
    
    async def analyze_answer(self, job_description: str, answer: str, question: str = "", role: str = "") -> Dict[str, Any]:
        """Analyze answer with multi-agent scoring and fallback."""
        try:
            # Try multi-agent scoring first
            if self.circuit_breakers["multi_agent"].can_execute():
                try:
                    analysis = await self._execute_with_retry(
                        get_multi_agent_scoring_service().analyze_response,
                        "multi_agent",
                        answer, question, job_description, role
                    )
                    
                    # Convert to legacy format
                    return self._format_multi_agent_response(analysis)
                except Exception as e:
                    logger.warning(f"Multi-agent scoring failed, falling back to Ollama: {e}")
            
            # Fallback to Ollama service
            if self.circuit_breakers["ollama"].can_execute():
                try:
                    ollama_response = await self._execute_with_retry(
                        self.ollama_service.analyze_answer,
                        "ollama",
                        job_description, question, answer
                    )
                    
                    # Convert to expected format
                    return self._format_ollama_response(ollama_response)
                except Exception as e:
                    logger.warning(f"Ollama analysis failed: {e}")
            
            # Final fallback
            logger.warning("All analysis services failed, returning fallback analysis")
            return self._get_fallback_analysis()
            
        except Exception as e:
            logger.error(f"All answer analysis methods failed: {e}")
            return self._get_fallback_analysis()
    
    def _get_fallback_questions(self, role: str, count: int) -> List[Dict[str, Any]]:
        """Get fallback questions when all services fail using centralized fallback manager."""
        fallback_response = get_fallback_response("question_generation", role=role, count=count)
        
        return [
            {
                "id": f"fallback_{i}",
                "text": question,
                "type": "fallback",
                "source": "fallback",
                "metadata": fallback_response.get("metadata", {"service": "fallback", "reason": "all_services_failed"})
            }
            for i, question in enumerate(fallback_response["questions"][:count])
        ]
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Get fallback analysis when all services fail using centralized fallback manager."""
        return get_fallback_response("answer_analysis")
    
    def _format_multi_agent_response(self, analysis) -> Dict[str, Any]:
        """Format multi-agent analysis response."""
        return {
            "analysis": f"Content: {analysis.content_agent.feedback}\n\nDelivery: {analysis.delivery_agent.feedback}\n\nTechnical: {analysis.technical_agent.feedback}",
            "score": {
                "clarity": analysis.delivery_agent.score,
                "confidence": analysis.content_agent.score,
                "technical": analysis.technical_agent.score,
                "overall": analysis.overall_score
            },
            "suggestions": analysis.recommendations,
            "multi_agent_analysis": analysis.dict()
        }
    
    def _format_ollama_response(self, ollama_response) -> Dict[str, Any]:
        """Format Ollama analysis response."""
        return {
            "analysis": ollama_response.analysis,
            "score": {
                "clarity": ollama_response.score.clarity,
                "confidence": ollama_response.score.confidence,
                "technical": 7.0,  # Default technical score
                "overall": (ollama_response.score.clarity + ollama_response.score.confidence) / 2
            },
            "suggestions": ollama_response.improvements,
            "multi_agent_analysis": None
        }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get comprehensive service health information."""
        health_status = {}
        
        for service_name, health in self.service_health.items():
            circuit_breaker = self.circuit_breakers[service_name]
            
            health_status[service_name] = {
                "status": health.status.value,
                "circuit_breaker_state": circuit_breaker.state,
                "consecutive_failures": health.consecutive_failures,
                "last_check": health.last_check,
                "can_execute": circuit_breaker.can_execute()
            }
        
        return health_status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all services."""
        health_results = {}
        
        # Check Ollama service
        try:
            if self.circuit_breakers["ollama"].can_execute():
                await self._execute_with_retry(
                    self.ollama_service.list_available_models,
                    "ollama"
                )
                health_results["ollama"] = {"status": "healthy", "error": None}
            else:
                health_results["ollama"] = {"status": "circuit_open", "error": "Circuit breaker open"}
        except Exception as e:
            health_results["ollama"] = {"status": "unhealthy", "error": str(e)}
        
        # Check multi-agent service
        try:
            if self.circuit_breakers["multi_agent"].can_execute():
                await self._execute_with_retry(
                    get_multi_agent_scoring_service().get_agent_status,
                    "multi_agent"
                )
                health_results["multi_agent"] = {"status": "healthy", "error": None}
            else:
                health_results["multi_agent"] = {"status": "circuit_open", "error": "Circuit breaker open"}
        except Exception as e:
            health_results["multi_agent"] = {"status": "unhealthy", "error": str(e)}
        
        # Check question service
        if self.question_service:
            try:
                if self.circuit_breakers["question_service"].can_execute():
                    # Simple health check - try to query database
                    self.question_service.db.query(self.question_service.db.query().first())
                    health_results["question_service"] = {"status": "healthy", "error": None}
                else:
                    health_results["question_service"] = {"status": "circuit_open", "error": "Circuit breaker open"}
            except Exception as e:
                health_results["question_service"] = {"status": "unhealthy", "error": str(e)}
        else:
            health_results["question_service"] = {"status": "unavailable", "error": "No database session"}
        
        return health_results


# Async version of the unified AI service
class AsyncUnifiedAIService(UnifiedAIService):
    """Async version of the unified AI service."""
    
    def __init__(self, db_session=None):
        super().__init__(db_session)
        # Async-specific initialization if needed
    
    async def generate_questions(self, role: str, job_description: str, count: int = 10) -> List[Dict[str, Any]]:
        """Async version of question generation."""
        return await super().generate_questions(role, job_description, count)
    
    async def analyze_answer(self, job_description: str, answer: str, question: str = "", role: str = "") -> Dict[str, Any]:
        """Async version of answer analysis."""
        return await super().analyze_answer(job_description, answer, question, role)
