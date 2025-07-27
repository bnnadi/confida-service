import os
from dotenv import load_dotenv
from typing import Dict, List

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
    def is_ollama_configured(self) -> bool:
        return bool(self.OLLAMA_BASE_URL)
    
    @property
    def is_openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)
    
    @property
    def is_anthropic_configured(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)
    
    @property
    def available_services(self) -> Dict[str, bool]:
        return {
            "ollama": self.is_ollama_configured,
            "openai": self.is_openai_configured,
            "anthropic": self.is_anthropic_configured
        }
    
    @property
    def service_priority(self) -> List[str]:
        """Get service priority based on configuration."""
        priority = []
        
        if self.is_ollama_configured:
            priority.append("ollama")
        
        if self.is_openai_configured:
            priority.append("openai")
        
        if self.is_anthropic_configured:
            priority.append("anthropic")
        
        return priority if priority else ["ollama"]

settings = Settings() 