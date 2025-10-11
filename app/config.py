import os
from dotenv import load_dotenv
from typing import Dict, List, Any
from functools import lru_cache

load_dotenv()

class Settings:
    # Database Settings - PostgreSQL as default for development
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev")
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Authentication Settings
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_REQUIRE_UPPERCASE: bool = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
    PASSWORD_REQUIRE_LOWERCASE: bool = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
    PASSWORD_REQUIRE_DIGITS: bool = os.getenv("PASSWORD_REQUIRE_DIGITS", "true").lower() == "true"
    PASSWORD_REQUIRE_SPECIAL_CHARS: bool = os.getenv("PASSWORD_REQUIRE_SPECIAL_CHARS", "false").lower() == "true"
    
    # Account Settings
    ACCOUNT_VERIFICATION_REQUIRED: bool = os.getenv("ACCOUNT_VERIFICATION_REQUIRED", "false").lower() == "true"
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    
    # File Upload Settings
    FILE_UPLOAD_DIR: str = os.getenv("FILE_UPLOAD_DIR", "uploads")
    FILE_EXPIRATION_HOURS: int = int(os.getenv("FILE_EXPIRATION_HOURS", "24"))
    FILE_CLEANUP_INTERVAL_HOURS: int = int(os.getenv("FILE_CLEANUP_INTERVAL_HOURS", "6"))
    FILE_MAX_SIZE_AUDIO: int = int(os.getenv("FILE_MAX_SIZE_AUDIO", "52428800"))  # 50MB
    FILE_MAX_SIZE_DOCUMENT: int = int(os.getenv("FILE_MAX_SIZE_DOCUMENT", "10485760"))  # 10MB
    FILE_MAX_SIZE_IMAGE: int = int(os.getenv("FILE_MAX_SIZE_IMAGE", "5242880"))  # 5MB
    FILE_ALLOWED_AUDIO_TYPES: List[str] = os.getenv("FILE_ALLOWED_AUDIO_TYPES", "audio/mpeg,audio/wav,audio/mp4,audio/ogg,audio/flac").split(",")
    FILE_ALLOWED_DOCUMENT_TYPES: List[str] = os.getenv("FILE_ALLOWED_DOCUMENT_TYPES", "application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document").split(",")
    FILE_ALLOWED_IMAGE_TYPES: List[str] = os.getenv("FILE_ALLOWED_IMAGE_TYPES", "image/jpeg,image/png,image/gif,image/webp").split(",")
    FILE_VIRUS_SCANNING_ENABLED: bool = os.getenv("FILE_VIRUS_SCANNING_ENABLED", "false").lower() == "true"
    FILE_CLOUD_STORAGE_ENABLED: bool = os.getenv("FILE_CLOUD_STORAGE_ENABLED", "false").lower() == "true"
    FILE_CLOUD_STORAGE_BUCKET: str = os.getenv("FILE_CLOUD_STORAGE_BUCKET", "")
    FILE_CLOUD_STORAGE_REGION: str = os.getenv("FILE_CLOUD_STORAGE_REGION", "us-east-1")

    
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
    
    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_BACKEND: str = os.getenv("RATE_LIMIT_BACKEND", "memory")  # "memory" or "redis"
    RATE_LIMIT_REDIS_URL: str = os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379")
    RATE_LIMIT_DEFAULT_REQUESTS: int = int(os.getenv("RATE_LIMIT_DEFAULT_REQUESTS", "100"))
    RATE_LIMIT_DEFAULT_WINDOW: int = int(os.getenv("RATE_LIMIT_DEFAULT_WINDOW", "3600"))  # seconds
    
    @property
    def rate_limit_per_endpoint(self) -> Dict[str, Dict[str, int]]:
        """Get rate limiting configuration per endpoint."""
        return {
            "/api/v1/parse-jd": {
                "requests": int(os.getenv("RATE_LIMIT_PARSE_JD_REQUESTS", "50")),
                "window": int(os.getenv("RATE_LIMIT_PARSE_JD_WINDOW", "3600"))
            },
            "/api/v1/analyze-answer": {
                "requests": int(os.getenv("RATE_LIMIT_ANALYZE_ANSWER_REQUESTS", "30")),
                "window": int(os.getenv("RATE_LIMIT_ANALYZE_ANSWER_WINDOW", "3600"))
            },
            "/api/v1/transcribe": {
                "requests": int(os.getenv("RATE_LIMIT_TRANSCRIBE_REQUESTS", "10")),
                "window": int(os.getenv("RATE_LIMIT_TRANSCRIBE_WINDOW", "3600"))
            },
            "/api/v1/supported-formats": {
                "requests": int(os.getenv("RATE_LIMIT_SUPPORTED_FORMATS_REQUESTS", "200")),
                "window": int(os.getenv("RATE_LIMIT_SUPPORTED_FORMATS_WINDOW", "3600"))
            }
        }
    
    def get_rate_limit_for_endpoint(self, endpoint: str) -> Dict[str, int]:
        """Get rate limiting configuration for a specific endpoint."""
        return self.rate_limit_per_endpoint.get(endpoint, {
            "requests": self.RATE_LIMIT_DEFAULT_REQUESTS,
            "window": self.RATE_LIMIT_DEFAULT_WINDOW
        })
    
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
        
        # Validate rate limiting configuration
        if self.RATE_LIMIT_ENABLED:
            if self.RATE_LIMIT_BACKEND not in ["memory", "redis"]:
                issues.append("RATE_LIMIT_BACKEND must be 'memory' or 'redis'")
            
            if self.RATE_LIMIT_BACKEND == "redis" and not self.RATE_LIMIT_REDIS_URL.startswith(('redis://', 'rediss://')):
                issues.append("RATE_LIMIT_REDIS_URL must be a valid Redis URL")
            
            if self.RATE_LIMIT_DEFAULT_REQUESTS <= 0:
                issues.append("RATE_LIMIT_DEFAULT_REQUESTS must be positive")
            
            if self.RATE_LIMIT_DEFAULT_WINDOW <= 0:
                issues.append("RATE_LIMIT_DEFAULT_WINDOW must be positive")
        
        return issues

@lru_cache()
def get_settings():
    return Settings()

settings = Settings() 