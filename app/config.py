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
    
    @property
    def is_ollama_configured(self) -> bool:
        return self.configured_services["ollama"]
    
    @property
    def is_openai_configured(self) -> bool:
        return self.configured_services["openai"]
    
    @property
    def is_anthropic_configured(self) -> bool:
        return self.configured_services["anthropic"]
    
    
    @property
    def service_priority(self) -> List[str]:
        """Get service priority based on configuration."""
        configured = [service for service, is_configured in self.configured_services.items() if is_configured]
        return configured if configured else ["ollama"]
    
    @lru_cache(maxsize=1)
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get cached Ollama configuration."""
        return {
            "base_url": self.OLLAMA_BASE_URL,
            "model": self.OLLAMA_MODEL,
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
            "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
            "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2000")),
            "timeout": int(os.getenv("OLLAMA_TIMEOUT", "60"))
        }
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if not any(self.configured_services.values()):
            issues.append("No AI services configured")
        
        if self.is_openai_configured and not self.OPENAI_API_KEY.startswith('sk-'):
            issues.append("Invalid OpenAI API key format")
        
        if self.is_anthropic_configured and not self.ANTHROPIC_API_KEY.startswith('sk-ant-'):
            issues.append("Invalid Anthropic API key format")
        
        return issues

settings = Settings() 