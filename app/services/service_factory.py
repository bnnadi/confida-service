"""
Service Factory for creating and initializing AI services.

This factory simplifies service initialization by centralizing service creation logic
and reducing complexity in the HybridAIService constructor.
"""
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.ollama_service import OllamaService
from app.services.question_bank_service import QuestionBankService
from app.services.role_analysis_service import RoleAnalysisService
from app.services.dynamic_prompt_service import DynamicPromptService
from app.services.intelligent_question_selector import IntelligentQuestionSelector
from app.services.ai_fallback_service import AIFallbackService
from app.services.ai_service_orchestrator import AIServiceOrchestrator, AIServiceType
from app.utils.service_initializer import ServiceInitializer
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ServiceFactory:
    """Factory for creating and initializing AI services."""
    
    @staticmethod
    def create_services(db_session: Optional[Session], settings: Any) -> Dict[str, Any]:
        """
        Create all required services for HybridAIService.
        
        Args:
            db_session: Database session (optional)
            settings: Application settings
            
        Returns:
            Dictionary containing all initialized services
        """
        services = {}
        
        # Core AI services
        services['ollama_service'] = OllamaService()
        services['openai_client'] = ServiceInitializer.init_openai_client()
        services['anthropic_client'] = ServiceInitializer.init_anthropic_client()
        
        # Database-dependent services
        if db_session:
            services['question_bank_service'] = QuestionBankService(db_session)
            services['intelligent_selector'] = IntelligentQuestionSelector(db_session)
            services['ai_fallback_service'] = AIFallbackService(db_session)
        else:
            services['question_bank_service'] = None
            services['intelligent_selector'] = IntelligentQuestionSelector(None)
            services['ai_fallback_service'] = AIFallbackService(None)
        
        # Analysis services (no database dependency)
        services['role_analysis_service'] = RoleAnalysisService()
        services['dynamic_prompt_service'] = DynamicPromptService()
        
        # Service priority configuration
        services['service_priority'] = ServiceFactory._get_service_priority()
        
        logger.info("All services initialized successfully")
        return services
    
    @staticmethod
    def create_orchestrator(services: Dict[str, Any]) -> AIServiceOrchestrator:
        """
        Create AI service orchestrator with available services.
        
        Args:
            services: Dictionary of initialized services
            
        Returns:
            Configured AIServiceOrchestrator instance
        """
        # Collect available AI services
        ai_services = [services['ollama_service']]
        
        if services['openai_client']:
            ai_services.append(services['openai_client'])
        if services['anthropic_client']:
            ai_services.append(services['anthropic_client'])
        
        orchestrator = AIServiceOrchestrator(ai_services, services['service_priority'])
        logger.info(f"Orchestrator created with {len(ai_services)} AI services")
        return orchestrator
    
    @staticmethod
    def _get_service_priority() -> List[AIServiceType]:
        """Get service priority based on available configuration."""
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
