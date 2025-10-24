"""
Unified Service Factory for Confida

This factory consolidates all service instantiation patterns into a single,
consistent service factory that eliminates redundancy and provides a clean
interface for service creation.
"""
from typing import Any, Dict, Optional, TypeVar
from functools import lru_cache
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

class ServiceFactory:
    """Unified service factory for creating and managing service instances."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize the service factory."""
        if self._initialized:
            return
        
        # Initialize core services
        self._initialize_core_services()
        self._initialized = True
        logger.info("✅ Service factory initialized successfully")
    
    def _initialize_core_services(self):
        """Initialize core services that don't require database sessions."""
        try:
            # Store service class names for lazy initialization to avoid circular imports
            service_class_names = {
                'ai_service': 'app.services.ai_service.UnifiedAIService',
                'analytics_service': 'app.services.analytics_service.UnifiedAnalyticsService',
                'vector_service': 'app.services.vector_service.UnifiedVectorService',
                'embedding_service': 'app.services.embedding_service.EmbeddingService',
                'ollama_service': 'app.services.ollama_service.OllamaService',
                'speech_service': 'app.services.speech_service.SpeechToTextService',
                'file_service': 'app.services.file_service.FileService',
                'multi_agent_scoring': 'app.services.multi_agent_scoring.MultiAgentScoringService',
                'smart_token_optimizer': 'app.services.smart_token_optimizer.SmartTokenOptimizer',
                'cost_tracker': 'app.services.cost_tracker.CostTracker',
                'health_service': 'app.services.health_service.HealthService',
                'scenario_service': 'app.services.scenario_service.ScenarioService',
                'auth_service': 'app.services.auth_service.AuthService',
                'validation_service': 'app.utils.validation.ValidationService',
                'error_handling_service': 'app.utils.error_handling.ErrorHandlingService',
                'fallback_service': 'app.utils.fallback.FallbackService',
            }
            
            # Store in instance variable
            self._service_class_names = service_class_names
            logger.info("✅ Core service class names registered")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize core services: {e}")
            raise
    
    def get_service(self, service_name: str, db_session: Optional[Session] = None) -> Any:
        """Get a service instance by name."""
        if not self._initialized:
            self.initialize()
        
        # Create cache key
        cache_key = f"{service_name}_{id(db_session) if db_session else 'no_db'}"
        
        # Return cached instance if available
        if cache_key in self._services:
            return self._services[cache_key]
        
        # Create new instance
        if not hasattr(self, '_service_class_names') or service_name not in self._service_class_names:
            raise ValueError(f"Unknown service: {service_name}")
        
        # Lazy import to avoid circular dependencies
        class_path = self._service_class_names[service_name]
        module_path, class_name = class_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        service_class = getattr(module, class_name)
        
        try:
            # Create service instance with appropriate parameters
            if service_name in ['file_service'] and db_session:
                instance = service_class(db_session)
            elif service_name in ['ai_service', 'analytics_service'] and db_session:
                instance = service_class(db_session)
            else:
                instance = service_class()
            
            # Cache the instance
            self._services[cache_key] = instance
            logger.debug(f"✅ Created service instance: {service_name}")
            return instance
            
        except Exception as e:
            logger.error(f"❌ Failed to create service {service_name}: {e}")
            raise
    
    def get_async_service(self, service_name: str, async_db_session: Optional[AsyncSession] = None) -> Any:
        """Get an async service instance by name."""
        if not self._initialized:
            self.initialize()
        
        # Create cache key
        cache_key = f"async_{service_name}_{id(async_db_session) if async_db_session else 'no_db'}"
        
        # Return cached instance if available
        if cache_key in self._services:
            return self._services[cache_key]
        
        # Create new instance
        if not hasattr(self, '_service_class_names') or service_name not in self._service_class_names:
            raise ValueError(f"Unknown service: {service_name}")
        
        # Lazy import to avoid circular dependencies
        class_path = self._service_class_names[service_name]
        module_path, class_name = class_path.rsplit('.', 1)
        module = __import__(module_path, fromlist=[class_name])
        service_class = getattr(module, class_name)
        
        try:
            # Create async service instance
            if service_name == 'ai_service' and async_db_session:
                from app.services.ai_service import AsyncUnifiedAIService
                instance = AsyncUnifiedAIService(async_db_session)
            elif service_name in ['ai_service', 'analytics_service'] and async_db_session:
                instance = service_class(async_db_session)
            else:
                instance = service_class()
            
            # Cache the instance
            self._services[cache_key] = instance
            logger.debug(f"✅ Created async service instance: {service_name}")
            return instance
            
        except Exception as e:
            logger.error(f"❌ Failed to create async service {service_name}: {e}")
            raise
    
    def clear_cache(self):
        """Clear the service cache."""
        self._services.clear()
        logger.info("✅ Service cache cleared")
    
    def get_available_services(self) -> list:
        """Get list of available service names."""
        if not self._initialized:
            self.initialize()
        return list(self._service_class_names.keys()) if hasattr(self, '_service_class_names') else []
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available."""
        if not self._initialized:
            self.initialize()
        return hasattr(self, '_service_class_names') and service_name in self._service_class_names

# Global service factory instance
service_factory = ServiceFactory()

# Convenience functions
@lru_cache(maxsize=128)
def get_service(service_name: str, db_session: Optional[Session] = None) -> Any:
    """Get a service instance (cached)."""
    return service_factory.get_service(service_name, db_session)

def get_async_service(service_name: str, async_db_session: Optional[AsyncSession] = None) -> Any:
    """Get an async service instance."""
    return service_factory.get_async_service(service_name, async_db_session)

def get_ai_service(db_session: Optional[Session] = None) -> Any:
    """Get AI service instance."""
    return get_service('ai_service', db_session)

def get_async_ai_service(async_db_session: Optional[AsyncSession] = None) -> Any:
    """Get async AI service instance."""
    return get_async_service('ai_service', async_db_session)

def get_analytics_service(db_session: Optional[Session] = None) -> Any:
    """Get analytics service instance."""
    return get_service('analytics_service', db_session)

def get_vector_service() -> Any:
    """Get vector service instance."""
    return get_service('vector_service')

def get_embedding_service() -> Any:
    """Get embedding service instance."""
    return get_service('embedding_service')

def get_ollama_service() -> Any:
    """Get Ollama service instance."""
    return get_service('ollama_service')

def get_speech_service() -> Any:
    """Get speech service instance."""
    return get_service('speech_service')

def get_file_service(db_session: Session) -> Any:
    """Get file service instance."""
    return get_service('file_service', db_session)

def get_multi_agent_scoring_service() -> Any:
    """Get multi-agent scoring service instance."""
    return get_service('multi_agent_scoring')

def get_validation_service() -> Any:
    """Get validation service instance."""
    return get_service('validation_service')

def get_error_handling_service() -> Any:
    """Get error handling service instance."""
    return get_service('error_handling_service')

def get_fallback_service() -> Any:
    """Get fallback service instance."""
    return get_service('fallback_service')

def get_auth_service() -> Any:
    """Get auth service instance."""
    return get_service('auth_service')

def get_health_service() -> Any:
    """Get health service instance."""
    return get_service('health_service')

def get_scenario_service() -> Any:
    """Get scenario service instance."""
    return get_service('scenario_service')

def get_smart_token_optimizer() -> Any:
    """Get smart token optimizer instance."""
    return get_service('smart_token_optimizer')

def get_cost_tracker() -> Any:
    """Get cost tracker instance."""
    return get_service('cost_tracker')

# Initialize factory on import
service_factory.initialize()
