import os
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Comprehensive configuration validation utility."""
    
    def __init__(self):
        self.settings = get_settings()
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Validate all configuration settings."""
        self.validation_errors = []
        self.validation_warnings = []
        
        # Service configuration validation
        self._validate_ai_services()
        
        # API key validation
        self._validate_api_keys()
        
        # URL validation
        self._validate_urls()
        
        # Model validation
        self._validate_models()
        
        # Numeric validation
        self._validate_numeric_values()
        
        # Environment-specific validation
        self._validate_environment_specific()
        
        # Database validation
        self._validate_database_config()
        
        # File upload validation
        self._validate_file_upload_config()
        
        # Rate limiting validation
        self._validate_rate_limiting_config()
        
        return self.validation_errors, self.validation_warnings
    
    def _validate_ai_services(self) -> None:
        """Validate AI service configuration."""
        if not any(self.settings.configured_services.values()):
            self.validation_errors.append("No AI services configured - at least one AI service must be available")
        
        # Check if any service is properly configured
        configured_count = sum(1 for configured in self.settings.configured_services.values() if configured)
        if configured_count == 0:
            self.validation_errors.append("No AI services are properly configured")
        elif configured_count == 1:
            self.validation_warnings.append("Only one AI service is configured - consider adding fallback services")
    
    def _validate_api_keys(self) -> None:
        """Validate API key formats."""
        # OpenAI API key validation
        if self.settings.is_openai_configured:
            if not self.settings.OPENAI_API_KEY:
                self.validation_errors.append("OpenAI API key is required when OpenAI is configured")
            elif not self.settings.OPENAI_API_KEY.startswith('sk-'):
                self.validation_errors.append("Invalid OpenAI API key format - should start with 'sk-'")
            elif len(self.settings.OPENAI_API_KEY) < 20:
                self.validation_errors.append("OpenAI API key appears to be too short")
        
        # Anthropic API key validation
        if self.settings.is_anthropic_configured:
            if not self.settings.ANTHROPIC_API_KEY:
                self.validation_errors.append("Anthropic API key is required when Anthropic is configured")
            elif not self.settings.ANTHROPIC_API_KEY.startswith('sk-ant-'):
                self.validation_errors.append("Invalid Anthropic API key format - should start with 'sk-ant-'")
            elif len(self.settings.ANTHROPIC_API_KEY) < 30:
                self.validation_errors.append("Anthropic API key appears to be too short")
    
    def _validate_urls(self) -> None:
        """Validate URL formats for external services."""
        # Ollama URL validation
        if not self._is_valid_url(self.settings.OLLAMA_BASE_URL):
            self.validation_errors.append(f"Invalid Ollama URL format: {self.settings.OLLAMA_BASE_URL}")
        elif not self.settings.OLLAMA_BASE_URL.startswith(('http://', 'https://')):
            self.validation_errors.append("Ollama URL must use HTTP or HTTPS protocol")
        
        # Check for localhost in production
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and "localhost" in self.settings.OLLAMA_BASE_URL:
            self.validation_warnings.append("Ollama URL uses localhost - this may not work in production")
    
    def _validate_models(self) -> None:
        """Validate AI model names."""
        # OpenAI model validation
        if self.settings.is_openai_configured:
            valid_openai_models = [
                'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 'gpt-4-1106-preview',
                'gpt-3.5-turbo', 'gpt-3.5-turbo-16k', 'gpt-3.5-turbo-1106'
            ]
            if self.settings.OPENAI_MODEL not in valid_openai_models:
                self.validation_warnings.append(
                    f"OpenAI model '{self.settings.OPENAI_MODEL}' may not be valid. "
                    f"Valid models: {', '.join(valid_openai_models)}"
                )
        
        # Anthropic model validation
        if self.settings.is_anthropic_configured:
            valid_anthropic_models = [
                'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307',
                'claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'
            ]
            if self.settings.ANTHROPIC_MODEL not in valid_anthropic_models:
                self.validation_warnings.append(
                    f"Anthropic model '{self.settings.ANTHROPIC_MODEL}' may not be valid. "
                    f"Valid models: {', '.join(valid_anthropic_models)}"
                )
        
        # Ollama model validation
        valid_ollama_models = [
            'llama2', 'llama2:7b', 'llama2:13b', 'llama2:70b',
            'mistral', 'mistral:7b', 'codellama', 'codellama:7b',
            'phi', 'neural-chat', 'starling-lm'
        ]
        if self.settings.OLLAMA_MODEL not in valid_ollama_models:
            self.validation_warnings.append(
                f"Ollama model '{self.settings.OLLAMA_MODEL}' may not be available. "
                f"Common models: {', '.join(valid_ollama_models[:5])}..."
            )
    
    def _validate_numeric_values(self) -> None:
        """Validate numeric configuration values."""
        # Temperature validation
        if not (0.0 <= self.settings.TEMPERATURE <= 2.0):
            self.validation_errors.append(
                f"Temperature must be between 0.0 and 2.0, got {self.settings.TEMPERATURE}"
            )
        
        # Max tokens validation
        if self.settings.MAX_TOKENS <= 0:
            self.validation_errors.append(f"MAX_TOKENS must be positive, got {self.settings.MAX_TOKENS}")
        elif self.settings.MAX_TOKENS > 4000:
            self.validation_warnings.append(
                f"MAX_TOKENS is very high ({self.settings.MAX_TOKENS}) - this may cause performance issues"
            )
        
        # Token expiration validation
        if self.settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            self.validation_errors.append(
                f"ACCESS_TOKEN_EXPIRE_MINUTES must be positive, got {self.settings.ACCESS_TOKEN_EXPIRE_MINUTES}"
            )
        elif self.settings.ACCESS_TOKEN_EXPIRE_MINUTES > 1440:  # 24 hours
            self.validation_warnings.append(
                f"ACCESS_TOKEN_EXPIRE_MINUTES is very high ({self.settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes) - consider shorter expiration for security"
            )
        
        # Refresh token validation
        if self.settings.REFRESH_TOKEN_EXPIRE_DAYS <= 0:
            self.validation_errors.append(
                f"REFRESH_TOKEN_EXPIRE_DAYS must be positive, got {self.settings.REFRESH_TOKEN_EXPIRE_DAYS}"
            )
        elif self.settings.REFRESH_TOKEN_EXPIRE_DAYS > 30:
            self.validation_warnings.append(
                f"REFRESH_TOKEN_EXPIRE_DAYS is very high ({self.settings.REFRESH_TOKEN_EXPIRE_DAYS} days) - consider shorter expiration for security"
            )
    
    def _validate_environment_specific(self) -> None:
        """Validate environment-specific configuration."""
        env = os.getenv("ENVIRONMENT", "development")
        
        if env == "production":
            # Production-specific validations
            if not self.settings.OPENAI_API_KEY and not self.settings.ANTHROPIC_API_KEY:
                self.validation_errors.append("At least one AI service API key is required in production")
            
            if self.settings.SECRET_KEY == "your-secret-key-change-this-in-production":
                self.validation_errors.append("SECRET_KEY must be changed from default value in production")
            
            if self.settings.OLLAMA_BASE_URL == "http://localhost:11434":
                self.validation_warnings.append("Ollama URL should not be localhost in production")
            
            if self.settings.DATABASE_URL == "postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev":
                self.validation_warnings.append("Database URL appears to be using development defaults in production")
        
        elif env == "development":
            # Development-specific validations
            if not self.settings.OPENAI_API_KEY and not self.settings.ANTHROPIC_API_KEY:
                self.validation_warnings.append("No AI service API keys configured - some features may not work")
    
    def _validate_database_config(self) -> None:
        """Validate database configuration."""
        if not self.settings.DATABASE_URL:
            self.validation_errors.append("DATABASE_URL is required")
        elif not self._is_valid_database_url(self.settings.DATABASE_URL):
            self.validation_errors.append(f"Invalid DATABASE_URL format: {self.settings.DATABASE_URL}")
        
        # Check for development defaults in production
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and "dev_password" in self.settings.DATABASE_URL:
            self.validation_warnings.append("Database URL contains development password in production")
    
    def _validate_file_upload_config(self) -> None:
        """Validate file upload configuration."""
        # File size limits validation
        if self.settings.FILE_MAX_SIZE_AUDIO <= 0:
            self.validation_errors.append("FILE_MAX_SIZE_AUDIO must be positive")
        elif self.settings.FILE_MAX_SIZE_AUDIO > 100 * 1024 * 1024:  # 100MB
            self.validation_warnings.append("FILE_MAX_SIZE_AUDIO is very large - consider reducing for performance")
        
        if self.settings.FILE_MAX_SIZE_DOCUMENT <= 0:
            self.validation_errors.append("FILE_MAX_SIZE_DOCUMENT must be positive")
        
        if self.settings.FILE_MAX_SIZE_IMAGE <= 0:
            self.validation_errors.append("FILE_MAX_SIZE_IMAGE must be positive")
        
        # File expiration validation
        if self.settings.FILE_EXPIRATION_HOURS <= 0:
            self.validation_errors.append("FILE_EXPIRATION_HOURS must be positive")
        elif self.settings.FILE_EXPIRATION_HOURS > 168:  # 1 week
            self.validation_warnings.append("FILE_EXPIRATION_HOURS is very long - consider shorter expiration for storage management")
    
    def _validate_rate_limiting_config(self) -> None:
        """Validate rate limiting configuration."""
        if self.settings.RATE_LIMIT_ENABLED:
            if self.settings.RATE_LIMIT_BACKEND not in ["memory", "redis"]:
                self.validation_errors.append(
                    f"RATE_LIMIT_BACKEND must be 'memory' or 'redis', got {self.settings.RATE_LIMIT_BACKEND}"
                )
            
            if self.settings.RATE_LIMIT_BACKEND == "redis":
                if not self.settings.RATE_LIMIT_REDIS_URL:
                    self.validation_errors.append("RATE_LIMIT_REDIS_URL is required when using Redis backend")
                elif not self._is_valid_redis_url(self.settings.RATE_LIMIT_REDIS_URL):
                    self.validation_errors.append(f"Invalid Redis URL format: {self.settings.RATE_LIMIT_REDIS_URL}")
            
            if self.settings.RATE_LIMIT_DEFAULT_REQUESTS <= 0:
                self.validation_errors.append("RATE_LIMIT_DEFAULT_REQUESTS must be positive")
            
            if self.settings.RATE_LIMIT_DEFAULT_WINDOW <= 0:
                self.validation_errors.append("RATE_LIMIT_DEFAULT_WINDOW must be positive")
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_valid_database_url(self, url: str) -> bool:
        """Check if database URL is valid."""
        try:
            result = urlparse(url)
            return result.scheme in ['postgresql', 'postgres', 'sqlite', 'mysql']
        except Exception:
            return False
    
    def _is_valid_redis_url(self, url: str) -> bool:
        """Check if Redis URL is valid."""
        try:
            result = urlparse(url)
            return result.scheme in ['redis', 'rediss']
        except Exception:
            return False
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of validation results."""
        return {
            "total_errors": len(self.validation_errors),
            "total_warnings": len(self.validation_warnings),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "is_valid": len(self.validation_errors) == 0
        }
    
    def validate_specific_setting(self, setting_name: str) -> Tuple[bool, List[str]]:
        """Validate a specific setting."""
        errors = []
        
        if setting_name == "OPENAI_API_KEY":
            if self.settings.is_openai_configured:
                if not self.settings.OPENAI_API_KEY:
                    errors.append("OpenAI API key is required")
                elif not self.settings.OPENAI_API_KEY.startswith('sk-'):
                    errors.append("Invalid OpenAI API key format")
        
        elif setting_name == "ANTHROPIC_API_KEY":
            if self.settings.is_anthropic_configured:
                if not self.settings.ANTHROPIC_API_KEY:
                    errors.append("Anthropic API key is required")
                elif not self.settings.ANTHROPIC_API_KEY.startswith('sk-ant-'):
                    errors.append("Invalid Anthropic API key format")
        
        elif setting_name == "OLLAMA_BASE_URL":
            if not self._is_valid_url(self.settings.OLLAMA_BASE_URL):
                errors.append("Invalid Ollama URL format")
        
        elif setting_name == "DATABASE_URL":
            if not self._is_valid_database_url(self.settings.DATABASE_URL):
                errors.append("Invalid database URL format")
        
        return len(errors) == 0, errors
