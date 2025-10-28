"""
Unified Validation Service for Confida

This service consolidates all validation functionality from multiple validator classes
into a single, comprehensive validation service that eliminates code duplication.
"""
import re
from typing import List, Tuple, Union
from pathlib import Path
from urllib.parse import urlparse
from fastapi import UploadFile
from app.models.schemas import FileType
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ValidationService:
    """Validation service that consolidates all validation functionality."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # File validation constants
        self.FILE_SIZE_LIMITS = {
            FileType.IMAGE: 10 * 1024 * 1024,  # 10MB
            FileType.DOCUMENT: 50 * 1024 * 1024,  # 50MB
            FileType.AUDIO: 100 * 1024 * 1024,  # 100MB
        }
        
        self.ALLOWED_EXTENSIONS = {
            FileType.IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            FileType.DOCUMENT: ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
            FileType.AUDIO: ['.mp3', '.wav', '.ogg', '.m4a', '.aac'],
        }
        
        # Security validation patterns
        self.SECURITY_PATTERNS = {
            'sql_injection': [r'(\bunion\b.*\bselect\b)', r'(\bselect\b.*\bfrom\b)', r'(\binsert\b.*\binto\b)'],
            'xss': [r'<script[^>]*>.*?</script>', r'javascript:', r'on\w+\s*='],
            'path_traversal': [r'\.\./', r'\.\.\\', r'%2e%2e%2f', r'%2e%2e%5c'],
            'command_injection': [r'[;&|`$]', r'\b(rm|del|format|shutdown)\b']
        }
        
        # API key patterns
        self.API_KEY_PATTERNS = {
            'openai': ('sk-', 20),
            'anthropic': ('sk-ant-', 30)
        }
        
        # Valid models
        self.VALID_MODELS = {
            'openai': ['gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview', 'gpt-3.5-turbo'],
            'anthropic': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
            'ollama': ['llama2', 'mistral', 'codellama', 'phi']
        }
    
    # Text Validation Methods
    def validate_text_length(self, text: str, min_length: int = 20, max_length: int = 500) -> bool:
        """Validate text length within specified bounds."""
        return min_length <= len(text) <= max_length
    
    def validate_word_count(self, text: str, min_words: int = 5, max_words: int = 100) -> bool:
        """Validate word count within specified bounds."""
        word_count = len(text.split())
        return min_words <= word_count <= max_words
    
    def validate_quality(self, text: str, min_length: int = 20, max_length: int = 500, 
                        min_words: int = 5, max_words: int = 100) -> Tuple[bool, List[str]]:
        """Comprehensive quality validation with detailed feedback."""
        issues = []
        
        if not self.validate_text_length(text, min_length, max_length):
            issues.append(f"Text length must be between {min_length} and {max_length} characters")
        
        if not self.validate_word_count(text, min_words, max_words):
            issues.append(f"Word count must be between {min_words} and {max_words} words")
        
        return len(issues) == 0, issues
    
    def contains_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text contains any of the specified patterns."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in patterns)
    
    def contains_regex_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the specified regex patterns."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    # Security Validation Methods
    def validate_security(self, text: str) -> Tuple[bool, List[str]]:
        """Validate text for security threats."""
        threats = []
        
        for threat_type, patterns in self.SECURITY_PATTERNS.items():
            if self.contains_regex_patterns(text, patterns):
                threats.append(f"Potential {threat_type} detected")
        
        return len(threats) == 0, threats
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    # File Validation Methods
    def validate_file_type(self, file: UploadFile, expected_type: FileType) -> Tuple[bool, str]:
        """Validate file type matches expected type."""
        if not file.filename:
            return False, "No filename provided"
        
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = self.ALLOWED_EXTENSIONS.get(expected_type, [])
        
        if file_ext not in allowed_extensions:
            return False, f"File type {file_ext} not allowed for {expected_type.value}"
        
        return True, "Valid file type"
    
    def validate_file_size(self, file: UploadFile, file_type: FileType) -> Tuple[bool, str]:
        """Validate file size within limits."""
        if not file.file:
            return False, "No file content provided"
        
        # Get file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        max_size = self.FILE_SIZE_LIMITS.get(file_type, 10 * 1024 * 1024)  # Default 10MB
        
        if file_size > max_size:
            return False, f"File size {file_size} exceeds limit of {max_size} bytes"
        
        return True, "Valid file size"
    
    def validate_file_content(self, file: UploadFile) -> Tuple[bool, str]:
        """Validate file content for security."""
        if not file.file:
            return False, "No file content provided"
        
        # Read first 1KB for content validation
        file.file.seek(0)
        content = file.file.read(1024)
        file.file.seek(0)  # Reset
        
        # Check for malicious content
        content_str = content.decode('utf-8', errors='ignore')
        is_safe, threats = self.validate_security(content_str)
        
        if not is_safe:
            return False, f"File content validation failed: {', '.join(threats)}"
        
        return True, "File content is safe"
    
    def validate_file(self, file: UploadFile, file_type: FileType) -> Tuple[bool, List[str]]:
        """Comprehensive file validation."""
        errors = []
        
        # Validate file type
        is_valid_type, type_error = self.validate_file_type(file, file_type)
        if not is_valid_type:
            errors.append(type_error)
        
        # Validate file size
        is_valid_size, size_error = self.validate_file_size(file, file_type)
        if not is_valid_size:
            errors.append(size_error)
        
        # Validate file content
        is_valid_content, content_error = self.validate_file_content(file)
        if not is_valid_content:
            errors.append(content_error)
        
        return len(errors) == 0, errors
    
    # Configuration Validation Methods
    def validate_api_key(self, api_key: str, service: str) -> Tuple[bool, str]:
        """Validate API key format for specific service."""
        if not api_key:
            return False, f"{service.title()} API key is required"
        
        if service not in self.API_KEY_PATTERNS:
            return True, "API key format not validated for this service"
        
        prefix, min_length = self.API_KEY_PATTERNS[service]
        
        if not api_key.startswith(prefix):
            return False, f"Invalid {service.title()} API key format - should start with '{prefix}'"
        
        if len(api_key) < min_length:
            return False, f"{service.title()} API key appears to be too short"
        
        return True, "Valid API key format"
    
    def validate_model(self, model: str, service: str) -> Tuple[bool, str]:
        """Validate AI model name for specific service."""
        if service not in self.VALID_MODELS:
            return True, "Model validation not configured for this service"
        
        valid_models = self.VALID_MODELS[service]
        if model not in valid_models:
            return False, f"Model '{model}' may not be valid for {service}. Valid models: {', '.join(valid_models[:3])}..."
        
        return True, "Valid model"
    
    def validate_numeric_value(self, value: Union[int, float], min_val: float = None, 
                             max_val: float = None, name: str = "Value") -> Tuple[bool, str]:
        """Validate numeric value within bounds."""
        if min_val is not None and value < min_val:
            return False, f"{name} must be >= {min_val}, got {value}"
        
        if max_val is not None and value > max_val:
            return False, f"{name} must be <= {max_val}, got {value}"
        
        return True, "Valid numeric value"
    
    # Configuration Validation
    def validate_configuration(self) -> Tuple[List[str], List[str]]:
        """Validate all configuration settings."""
        errors = []
        warnings = []
        
        # Validate AI services
        configured_count = sum(1 for configured in self.settings.configured_services.values() if configured)
        if configured_count == 0:
            errors.append("No AI services are properly configured")
        elif configured_count == 1:
            warnings.append("Only one AI service is configured - consider adding fallback services")
        
        # Validate API keys
        for service in ['openai', 'anthropic']:
            if getattr(self.settings, f'is_{service}_configured', False):
                api_key = getattr(self.settings, f'{service.upper()}_API_KEY', '')
                is_valid, error = self.validate_api_key(api_key, service)
                if not is_valid:
                    errors.append(error)
        
        # Validate AI service microservice URL
        if not self.validate_url(self.settings.AI_SERVICE_URL):
            errors.append(f"Invalid AI service URL format: {self.settings.AI_SERVICE_URL}")
        elif not self.settings.AI_SERVICE_URL.startswith(('http://', 'https://')):
            errors.append("AI service URL must use HTTP or HTTPS protocol")
        
        # Validate numeric values
        temp_valid, temp_error = self.validate_numeric_value(
            self.settings.TEMPERATURE, 0.0, 2.0, "Temperature"
        )
        if not temp_valid:
            errors.append(temp_error)
        
        tokens_valid, tokens_error = self.validate_numeric_value(
            self.settings.MAX_TOKENS, 1, 4000, "MAX_TOKENS"
        )
        if not tokens_valid:
            errors.append(tokens_error)
        elif self.settings.MAX_TOKENS > 4000:
            warnings.append(f"MAX_TOKENS is very high ({self.settings.MAX_TOKENS}) - this may cause performance issues")
        
        return errors, warnings
