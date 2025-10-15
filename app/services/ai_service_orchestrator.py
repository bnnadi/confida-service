"""
AI Service Orchestrator for simplified service management.
Replaces complex generic orchestration patterns with clean, testable code.
"""

from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from collections import deque
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
        
        # Priority queue for service selection
        self.service_queue = deque(self.service_priority)
        
        # Service health tracking
        self.service_health = {service_type: True for service_type in self.service_priority}
        self.failure_counts = {service_type: 0 for service_type in self.service_priority}
        self.max_failures = 3  # Mark service as unhealthy after 3 consecutive failures
    
    def try_services(self, operation: str, preferred_service: Optional[str] = None, **kwargs) -> Any:
        """Try services using priority queue with health-aware selection."""
        services_to_try = self._get_healthy_services(preferred_service)
        
        for service_type in services_to_try:
            if result := self._try_service_with_health_tracking(service_type, operation, **kwargs):
                logger.info(f"✅ Successfully used {service_type.value} for {operation}")
                return result
        
        logger.warning(f"⚠️ All services failed for {operation}, using fallback")
        return self._get_fallback(operation, **kwargs)
    
    def _get_healthy_services(self, preferred_service: Optional[str] = None) -> List[AIServiceType]:
        """Get ordered list of healthy services to try."""
        if preferred_service:
            try:
                preferred = AIServiceType(preferred_service.lower())
                if self.service_health.get(preferred, True):
                    return [preferred] + [s for s in self.service_priority if s != preferred and self.service_health.get(s, True)]
            except ValueError:
                logger.warning(f"Unknown preferred service: {preferred_service}")
        
        # Return only healthy services in priority order
        return [s for s in self.service_priority if self.service_health.get(s, True)]
    
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
    
    def _try_service_with_health_tracking(self, service_type: AIServiceType, operation: str, **kwargs) -> Optional[Any]:
        """Try a specific service with health tracking."""
        try:
            service = self._get_service(service_type)
            if not service:
                self._mark_service_failure(service_type)
                return None
            
            method = getattr(service, operation, None)
            if not method:
                logger.warning(f"Service {service_type.value} doesn't support {operation}")
                self._mark_service_failure(service_type)
                return None
            
            result = method(**kwargs)
            if result:
                self._mark_service_success(service_type)
                return result
            else:
                self._mark_service_failure(service_type)
                
        except Exception as e:
            logger.warning(f"Service {service_type.value} failed for {operation}: {e}")
            self._mark_service_failure(service_type)
        
        return None
    
    def _mark_service_success(self, service_type: AIServiceType):
        """Mark service as successful and reset failure count."""
        self.service_health[service_type] = True
        self.failure_counts[service_type] = 0
    
    def _mark_service_failure(self, service_type: AIServiceType):
        """Mark service failure and update health status."""
        self.failure_counts[service_type] += 1
        if self.failure_counts[service_type] >= self.max_failures:
            self.service_health[service_type] = False
            logger.warning(f"Service {service_type.value} marked as unhealthy after {self.max_failures} failures")
    
    def get_service_health_status(self) -> Dict[str, Any]:
        """Get current health status of all services."""
        return {
            "service_health": dict(self.service_health),
            "failure_counts": dict(self.failure_counts),
            "healthy_services": [s.value for s in self.service_priority if self.service_health.get(s, True)]
        }

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
