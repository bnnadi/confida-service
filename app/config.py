import os
from dotenv import load_dotenv
from typing import Dict, List, Any, Tuple
from functools import lru_cache

load_dotenv()

class Settings:
    # Database Settings - PostgreSQL as default for development
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    DATABASE_POOL_TIMEOUT: int = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    DATABASE_POOL_RECYCLE: int = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
    
    # Connection Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    
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
    
    # Security Headers Settings
    SECURITY_HEADERS_ENABLED: bool = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true"
    
    # Development/Debug Routes Settings
    ENABLE_DEBUG_ROUTES: bool = os.getenv("ENABLE_DEBUG_ROUTES", "false").lower() == "true"
    ENABLE_SECURITY_ROUTES: bool = os.getenv("ENABLE_SECURITY_ROUTES", "false").lower() == "true"
    ENABLE_ADMIN_ROUTES: bool = os.getenv("ENABLE_ADMIN_ROUTES", "true").lower() == "true"
    
    # CORS Configuration for HTTPS
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "https://localhost:3001,https://127.0.0.1:3001,https://interviewiq.com").split(",")
    CORS_METHODS: List[str] = os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS,PATCH").split(",")
    CORS_HEADERS: List[str] = os.getenv("CORS_HEADERS", "Content-Type,Authorization,API-Version,X-Requested-With").split(",")
    CORS_MAX_AGE: int = int(os.getenv("CORS_MAX_AGE", "86400"))  # 24 hours
    
    # Content Security Policy
    CSP_POLICY: str = os.getenv("CSP_POLICY", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'")
    
    # HTTPS Security Settings
    HSTS_MAX_AGE: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = os.getenv("HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
    HSTS_PRELOAD: bool = os.getenv("HSTS_PRELOAD", "true").lower() == "true"
    
    @property
    def security_headers(self) -> Dict[str, str]:
        """Get security headers configuration."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
            "Strict-Transport-Security": self._get_hsts_header(),
            "Content-Security-Policy": self.CSP_POLICY,
            "X-Permitted-Cross-Domain-Policies": "none",
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin"
        }
    
    def _get_hsts_header(self) -> str:
        """Generate HSTS header value."""
        hsts = f"max-age={self.HSTS_MAX_AGE}"
        if self.HSTS_INCLUDE_SUBDOMAINS:
            hsts += "; includeSubDomains"
        if self.HSTS_PRELOAD:
            hsts += "; preload"
        return hsts
    
    @property
    def cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": True,
            "allow_methods": self.CORS_METHODS,
            "allow_headers": self.CORS_HEADERS,
            "expose_headers": [
                "X-RateLimit-Limit", 
                "X-RateLimit-Remaining", 
                "X-RateLimit-Window",
                "X-RateLimit-Reset",
                "API-Version",
                "X-Request-ID"
            ],
            "max_age": self.CORS_MAX_AGE
        }
    
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
            },
            "/api/v1/files/upload": {
                "requests": int(os.getenv("RATE_LIMIT_FILE_UPLOAD_REQUESTS", "10")),
                "window": int(os.getenv("RATE_LIMIT_FILE_UPLOAD_WINDOW", "3600"))
            },
            "/api/v1/auth/login": {
                "requests": int(os.getenv("RATE_LIMIT_AUTH_LOGIN_REQUESTS", "5")),
                "window": int(os.getenv("RATE_LIMIT_AUTH_LOGIN_WINDOW", "300"))  # 5 minutes
            },
            "/api/v1/auth/register": {
                "requests": int(os.getenv("RATE_LIMIT_AUTH_REGISTER_REQUESTS", "3")),
                "window": int(os.getenv("RATE_LIMIT_AUTH_REGISTER_WINDOW", "3600"))
            },
            "/api/v1/admin": {
                "requests": int(os.getenv("RATE_LIMIT_ADMIN_REQUESTS", "20")),
                "window": int(os.getenv("RATE_LIMIT_ADMIN_WINDOW", "3600"))
            }
        }
    
    def get_rate_limit_for_endpoint(self, endpoint: str) -> Dict[str, int]:
        """Get rate limiting configuration for a specific endpoint."""
        return self.rate_limit_per_endpoint.get(endpoint, {
            "requests": self.RATE_LIMIT_DEFAULT_REQUESTS,
            "window": self.RATE_LIMIT_DEFAULT_WINDOW
        })

    @property
    def rate_limit_per_user_type(self) -> Dict[str, Dict[str, int]]:
        """Define rate limits for different user types."""
        return {
            "free": {
                "requests": int(os.getenv("RATE_LIMIT_FREE_REQUESTS", "10")),
                "window": int(os.getenv("RATE_LIMIT_FREE_WINDOW", "3600"))
            },
            "premium": {
                "requests": int(os.getenv("RATE_LIMIT_PREMIUM_REQUESTS", "100")),
                "window": int(os.getenv("RATE_LIMIT_PREMIUM_WINDOW", "3600"))
            },
            "enterprise": {
                "requests": int(os.getenv("RATE_LIMIT_ENTERPRISE_REQUESTS", "1000")),
                "window": int(os.getenv("RATE_LIMIT_ENTERPRISE_WINDOW", "3600"))
            }
        }

    def get_rate_limit_for_user_type(self, user_type: str) -> Dict[str, int]:
        """Get rate limiting configuration for a specific user type."""
        return self.rate_limit_per_user_type.get(user_type, {
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
        from app.utils.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        errors, warnings = validator.validate_all()
        
        # Return only errors for backward compatibility
        return errors
    
    def validate_configuration_with_warnings(self) -> Dict[str, Any]:
        """Validate configuration and return both errors and warnings."""
        from app.utils.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        errors, warnings = validator.validate_all()
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0,
            "total_issues": len(errors) + len(warnings)
        }
    
    def validate_specific_setting(self, setting_name: str) -> Tuple[bool, List[str]]:
        """Validate a specific configuration setting."""
        from app.utils.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        return validator.validate_specific_setting(setting_name)
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a comprehensive validation summary."""
        from app.utils.config_validator import ConfigValidator
        
        validator = ConfigValidator()
        return validator.get_validation_summary()

@lru_cache()
def get_settings():
    return Settings()

settings = Settings() 