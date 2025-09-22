import os
from dotenv import load_dotenv
from typing import Dict, List, Any
from functools import lru_cache

load_dotenv()

class Settings:
    # Ollama Settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    
    # Anthropic Settings
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
    
    # Application Settings
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7
    
    @property
    def configured_services(self) -> Dict[str, bool]:
        """Get all service configuration status at once."""
        return {
            "ollama": bool(self.OLLAMA_BASE_URL),
            "openai": bool(self.OPENAI_API_KEY),
            "anthropic": bool(self.ANTHROPIC_API_KEY)
        }
    
    def is_service_configured(self, service: str) -> bool:
        """Check if a specific service is configured."""
        return self.configured_services.get(service, False)
    
    # Backward compatibility properties
    @property
    def is_ollama_configured(self) -> bool:
        return self.is_service_configured("ollama")
    
    @property
    def is_openai_configured(self) -> bool:
        return self.is_service_configured("openai")
    
    @property
    def is_anthropic_configured(self) -> bool:
        return self.is_service_configured("anthropic")
    
    
    @property
    def service_priority(self) -> List[str]:
        """Get service priority based on configuration."""
        configured = [service for service, is_configured in self.configured_services.items() if is_configured]
        return configured if configured else ["ollama"]
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama configuration."""
        if not hasattr(self, '_ollama_config_cache'):
            self._ollama_config_cache = {
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL,
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
                "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2000")),
                "timeout": int(os.getenv("OLLAMA_TIMEOUT", "60"))
            }
        return self._ollama_config_cache
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if not any(self.configured_services.values()):
            issues.append("No AI services configured")
        
        # Validate API keys
        if self.is_openai_configured and not self.OPENAI_API_KEY.startswith('sk-'):
            issues.append("Invalid OpenAI API key format")
        
        if self.is_anthropic_configured and not self.ANTHROPIC_API_KEY.startswith('sk-ant-'):
            issues.append("Invalid Anthropic API key format")
        
        # Validate numeric values
        if self.MAX_TOKENS <= 0:
            issues.append("MAX_TOKENS must be positive")
        
        if not 0 <= self.TEMPERATURE <= 2:
            issues.append("TEMPERATURE must be between 0 and 2")
        
        # Validate URLs
        if self.OLLAMA_BASE_URL and not self.OLLAMA_BASE_URL.startswith(('http://', 'https://')):
            issues.append("OLLAMA_BASE_URL must be a valid URL")
        
        return issues

settings = Settings() 