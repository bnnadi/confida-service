import os
from typing import List, Tuple
from urllib.parse import urlparse
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Configuration validation utility."""
    
    def __init__(self):
        self.settings = get_settings()
        self.validation_errors = []
        self.validation_warnings = []
        
        # Validation rules
        self.api_key_patterns = {
            'openai': ('sk-', 20),
            'anthropic': ('sk-ant-', 30)
        }
        
        self.valid_models = {
            'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 'gpt-3.5-turbo'],
            'anthropic': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
            'ollama': ['llama2', 'mistral', 'codellama', 'phi']
        }
    
    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Validate all configuration settings."""
        self.validation_errors = []
        self.validation_warnings = []
        
        # Run all validations
        self._validate_ai_services()
        self._validate_api_keys()
        self._validate_urls()
        self._validate_models()
        self._validate_numeric_values()
        
        return self.validation_errors, self.validation_warnings
    
    def _validate_ai_services(self) -> None:
        """Validate AI service configuration."""
        configured_count = sum(1 for configured in self.settings.configured_services.values() if configured)
        if configured_count == 0:
            self.validation_errors.append("No AI services are properly configured")
        elif configured_count == 1:
            self.validation_warnings.append("Only one AI service is configured - consider adding fallback services")
    
    def _validate_api_keys(self) -> None:
        """Validate API key formats."""
        for service, (prefix, min_length) in self.api_key_patterns.items():
            if getattr(self.settings, f'is_{service}_configured', False):
                api_key = getattr(self.settings, f'{service.upper()}_API_KEY', '')
                if not api_key:
                    self.validation_errors.append(f"{service.title()} API key is required")
                elif not api_key.startswith(prefix):
                    self.validation_errors.append(f"Invalid {service.title()} API key format - should start with '{prefix}'")
                elif len(api_key) < min_length:
                    self.validation_errors.append(f"{service.title()} API key appears to be too short")
    
    def _validate_urls(self) -> None:
        """Validate URL formats for external services."""
        if not self._is_valid_url(self.settings.OLLAMA_BASE_URL):
            self.validation_errors.append(f"Invalid Ollama URL format: {self.settings.OLLAMA_BASE_URL}")
        elif not self.settings.OLLAMA_BASE_URL.startswith(('http://', 'https://')):
            self.validation_errors.append("Ollama URL must use HTTP or HTTPS protocol")
        
        # Check for localhost in production
        if os.getenv("ENVIRONMENT") == "production" and "localhost" in self.settings.OLLAMA_BASE_URL:
            self.validation_warnings.append("Ollama URL uses localhost - this may not work in production")
    
    def _validate_models(self) -> None:
        """Validate AI model names."""
        for service, valid_models in self.valid_models.items():
            if getattr(self.settings, f'is_{service}_configured', False):
                model = getattr(self.settings, f'{service.upper()}_MODEL', '')
                if model not in valid_models:
                    self.validation_warnings.append(
                        f"{service.title()} model '{model}' may not be valid. "
                        f"Valid models: {', '.join(valid_models[:3])}..."
                    )
    
    def _validate_numeric_values(self) -> None:
        """Validate numeric configuration values."""
        if not (0.0 <= self.settings.TEMPERATURE <= 2.0):
            self.validation_errors.append(f"Temperature must be between 0.0 and 2.0, got {self.settings.TEMPERATURE}")
        
        if self.settings.MAX_TOKENS <= 0:
            self.validation_errors.append(f"MAX_TOKENS must be positive, got {self.settings.MAX_TOKENS}")
        elif self.settings.MAX_TOKENS > 4000:
            self.validation_warnings.append(f"MAX_TOKENS is very high ({self.settings.MAX_TOKENS}) - this may cause performance issues")
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False