"""
Unified AI Request Handler

Provides a clean, unified interface for creating AI service requests
instead of duplicate methods in UnifiedAIService.
"""

import os
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from app.utils.logger import get_logger
from app.utils.prompt_templates import PromptTemplates

logger = get_logger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for an AI service."""
    client: Any
    model: str
    method_name: str
    system_key: str = "system"
    messages_key: str = "messages"
    max_tokens_key: str = "max_tokens"
    temperature_key: str = "temperature"
    temperature_value: float = 0.7

class AIRequestHandler:
    """
    Unified AI request handler that eliminates duplication across services.
    Provides a clean, configuration-driven approach to AI service requests.
    """
    
    def __init__(self):
        self.service_configs = self._initialize_service_configs()
    
    def create_request(self, service_type: str, max_tokens: int, role: str, job_description: str) -> Any:
        """
        Create a unified AI request for any service type.
        
        Args:
            service_type: Type of AI service ('openai', 'anthropic', etc.)
            max_tokens: Maximum tokens for the request
            role: Job role for question generation
            job_description: Job description text
            
        Returns:
            AI service response
        """
        try:
            config = self._get_service_config(service_type)
            prompt = self._generate_prompt(role, job_description)
            
            return self._execute_request(config, prompt, max_tokens)
            
        except Exception as e:
            logger.error(f"Error creating {service_type} request: {e}")
            raise
    
    def _initialize_service_configs(self) -> Dict[str, ServiceConfig]:
        """Initialize service configurations."""
        return {
            'openai': ServiceConfig(
                client=None,  # Will be set by UnifiedAIService
                model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                method_name="chat.completions.create",
                system_key="messages",
                messages_key="messages",
                max_tokens_key="max_tokens",
                temperature_key="temperature"
            ),
            'anthropic': ServiceConfig(
                client=None,  # Will be set by UnifiedAIService
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                method_name="messages.create",
                system_key="system",
                messages_key="messages",
                max_tokens_key="max_tokens",
                temperature_key="temperature"
            )
        }
    
    def _get_service_config(self, service_type: str) -> ServiceConfig:
        """Get service configuration."""
        if service_type not in self.service_configs:
            raise ValueError(f"Unknown service type: {service_type}")
        return self.service_configs[service_type]
    
    def _generate_prompt(self, role: str, job_description: str) -> str:
        """Generate prompt using centralized templates."""
        return PromptTemplates.get_question_generation_prompt(role, job_description)
    
    def _execute_request(self, config: ServiceConfig, prompt: str, max_tokens: int) -> Any:
        """Execute the AI request using service configuration."""
        if not config.client:
            raise ValueError(f"Client not initialized for service")
        
        # Build request parameters based on service type
        request_params = self._build_request_params(config, prompt, max_tokens)
        
        # Execute the request
        method = self._get_method(config.client, config.method_name)
        return method(**request_params)
    
    def _build_request_params(self, config: ServiceConfig, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Build request parameters based on service configuration."""
        params = {
            "model": config.model,
            config.max_tokens_key: max_tokens,
            config.temperature_key: config.temperature_value
        }
        
        # Handle different message structures
        if config.system_key == "messages":
            # OpenAI-style: system message in messages array
            params[config.messages_key] = [
                {"role": "system", "content": PromptTemplates.QUESTION_GENERATION_SYSTEM},
                {"role": "user", "content": prompt}
            ]
        else:
            # Anthropic-style: separate system parameter
            params[config.system_key] = PromptTemplates.QUESTION_GENERATION_SYSTEM
            params[config.messages_key] = [{"role": "user", "content": prompt}]
        
        return params
    
    def _get_method(self, client: Any, method_name: str) -> Callable:
        """Get method from client using dot notation."""
        method = client
        for attr in method_name.split('.'):
            method = getattr(method, attr)
        return method
    
    def set_client(self, service_type: str, client: Any):
        """Set client for a service type."""
        if service_type in self.service_configs:
            self.service_configs[service_type].client = client
        else:
            logger.warning(f"Unknown service type for client setting: {service_type}")
    
    def get_supported_services(self) -> list:
        """Get list of supported service types."""
        return list(self.service_configs.keys())
