"""
AI Service Orchestrator for simplified service management.
Replaces complex generic orchestration patterns with clean, testable code.
"""

from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from app.utils.logger import get_logger
from app.exceptions import ServiceUnavailableError
from app.utils.fallback_responses import FallbackResponses

logger = get_logger(__name__)

class AIServiceType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class AIServiceOrchestrator:
    """Simplified AI service orchestration with clean error handling."""
    
    def __init__(self, services: List[Any], service_priority: List[AIServiceType] = None):
        self.services = services
        self.service_priority = service_priority or [AIServiceType.OLLAMA, AIServiceType.OPENAI, AIServiceType.ANTHROPIC]
        self.service_map = {service.__class__.__name__.lower().replace('service', ''): service for service in services}
    
    def try_services(self, operation: str, preferred_service: Optional[str] = None, **kwargs) -> Any:
        """Try services in priority order with clean error handling."""
        services_to_try = self._get_services_to_try(preferred_service)
        
        for service_type in services_to_try:
            if result := self._try_service(service_type, operation, **kwargs):
                logger.info(f"✅ Successfully used {service_type.value} for {operation}")
                return result
        
        logger.warning(f"⚠️ All services failed for {operation}, using fallback")
        return self._get_fallback(operation, **kwargs)
    
    def _get_services_to_try(self, preferred_service: Optional[str] = None) -> List[AIServiceType]:
        """Get ordered list of services to try."""
        if preferred_service:
            try:
                preferred = AIServiceType(preferred_service.lower())
                return [preferred] + [s for s in self.service_priority if s != preferred]
            except ValueError:
                logger.warning(f"Unknown preferred service: {preferred_service}")
        
        return self.service_priority
    
    def _try_service(self, service_type: AIServiceType, operation: str, **kwargs) -> Optional[Any]:
        """Try a specific service with error handling."""
        try:
            service = self._get_service(service_type)
            if not service:
                return None
            
            method = getattr(service, operation, None)
            if not method:
                logger.warning(f"Service {service_type.value} doesn't support {operation}")
                return None
            
            return method(**kwargs)
            
        except ServiceUnavailableError as e:
            logger.warning(f"Service {service_type.value} unavailable: {e}")
            return None
        except Exception as e:
            logger.error(f"Error with {service_type.value}: {e}")
            return None
    
    def _get_service(self, service_type: AIServiceType) -> Optional[Any]:
        """Get service instance by type."""
        service_name = service_type.value
        return self.service_map.get(service_name)
    
    def _get_fallback(self, operation: str, **kwargs) -> Any:
        """Get fallback response based on operation type."""
        if operation == "generate_interview_questions":
            role = kwargs.get('role', 'unknown')
            return FallbackResponses.get_fallback_questions(role)
        elif operation == "analyze_answer":
            return FallbackResponses.get_fallback_analysis()
        else:
            logger.error(f"No fallback available for operation: {operation}")
            raise ServiceUnavailableError(f"No fallback available for {operation}")

class ServiceOperation:
    """Represents a service operation with metadata."""
    
    def __init__(self, name: str, method: str, fallback_func: Callable = None):
        self.name = name
        self.method = method
        self.fallback_func = fallback_func or (lambda **kwargs: None)
    
    def execute(self, orchestrator: AIServiceOrchestrator, **kwargs) -> Any:
        """Execute the operation using the orchestrator."""
        result = orchestrator.try_services(self.method, **kwargs)
        if not result:
            return self.fallback_func(**kwargs)
        return result
