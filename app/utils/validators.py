"""
Input validation utilities for API endpoints.
"""
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, Query
from enum import Enum
import re

class AIServiceType(str, Enum):
    """Valid AI service types."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class LanguageCode(str, Enum):
    """Valid language codes for speech recognition."""
    EN_US = "en-US"
    EN_GB = "en-GB"
    ES_ES = "es-ES"
    FR_FR = "fr-FR"
    DE_DE = "de-DE"
    IT_IT = "it-IT"
    PT_BR = "pt-BR"
    JA_JP = "ja-JP"
    KO_KR = "ko-KR"
    ZH_CN = "zh-CN"

class InputValidator:
    """Centralized input validation utilities."""
    
    # Allowed values for validation
    ALLOWED_SERVICES = [service.value for service in AIServiceType]
    ALLOWED_LANGUAGES = [lang.value for lang in LanguageCode]
    
    # Text length limits
    MAX_ROLE_LENGTH = 200
    MAX_JOB_DESCRIPTION_LENGTH = 10000
    MAX_QUESTION_LENGTH = 1000
    MAX_ANSWER_LENGTH = 5000
    MAX_SESSION_DESCRIPTION_LENGTH = 5000
    
    # Minimum lengths
    MIN_ROLE_LENGTH = 1
    MIN_JOB_DESCRIPTION_LENGTH = 10
    MIN_QUESTION_LENGTH = 5
    MIN_ANSWER_LENGTH = 1
    
    @staticmethod
    def validate_service(service: Optional[str]) -> Optional[str]:
        """
        Validate AI service parameter.
        
        Args:
            service: Service name to validate
            
        Returns:
            Validated service name in lowercase
            
        Raises:
            HTTPException: If service is invalid
        """
        if service is None:
            return None
        
        service_lower = service.lower().strip()
        if service_lower not in InputValidator.ALLOWED_SERVICES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid service parameter",
                    "message": f"Service '{service}' is not supported",
                    "allowed_services": InputValidator.ALLOWED_SERVICES,
                    "received": service
                }
            )
        
        return service_lower
    
    @staticmethod
    def validate_language(language: Optional[str]) -> str:
        """
        Validate language code parameter.
        
        Args:
            language: Language code to validate
            
        Returns:
            Validated language code (defaults to en-US)
            
        Raises:
            HTTPException: If language is invalid
        """
        if language is None:
            return LanguageCode.EN_US.value
        
        if language not in InputValidator.ALLOWED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid language parameter",
                    "message": f"Language '{language}' is not supported",
                    "allowed_languages": InputValidator.ALLOWED_LANGUAGES,
                    "received": language
                }
            )
        
        return language
    
    @staticmethod
    def validate_text_length(
        text: str, 
        field_name: str, 
        min_length: int = None, 
        max_length: int = None
    ) -> str:
        """
        Validate text field length.
        
        Args:
            text: Text to validate
            field_name: Name of the field for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            
        Returns:
            Validated text
            
        Raises:
            HTTPException: If text length is invalid
        """
        if not isinstance(text, str):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid text format",
                    "message": f"{field_name} must be a string",
                    "received_type": type(text).__name__
                }
            )
        
        text = text.strip()
        
        if min_length is not None and len(text) < min_length:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Text too short",
                    "message": f"{field_name} must be at least {min_length} characters",
                    "received_length": len(text),
                    "minimum_length": min_length
                }
            )
        
        if max_length is not None and len(text) > max_length:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Text too long",
                    "message": f"{field_name} must be no more than {max_length} characters",
                    "received_length": len(text),
                    "maximum_length": max_length
                }
            )
        
        return text
    
    @staticmethod
    def validate_role(role: str) -> str:
        """Validate job role field."""
        return InputValidator.validate_text_length(
            role, 
            "Role", 
            min_length=InputValidator.MIN_ROLE_LENGTH,
            max_length=InputValidator.MAX_ROLE_LENGTH
        )
    
    @staticmethod
    def validate_job_description(job_description: str) -> str:
        """Validate job description field."""
        return InputValidator.validate_text_length(
            job_description, 
            "Job description", 
            min_length=InputValidator.MIN_JOB_DESCRIPTION_LENGTH,
            max_length=InputValidator.MAX_JOB_DESCRIPTION_LENGTH
        )
    
    @staticmethod
    def validate_question(question: str) -> str:
        """Validate question field."""
        return InputValidator.validate_text_length(
            question, 
            "Question", 
            min_length=InputValidator.MIN_QUESTION_LENGTH,
            max_length=InputValidator.MAX_QUESTION_LENGTH
        )
    
    @staticmethod
    def validate_answer(answer: str) -> str:
        """Validate answer field."""
        return InputValidator.validate_text_length(
            answer, 
            "Answer", 
            min_length=InputValidator.MIN_ANSWER_LENGTH,
            max_length=InputValidator.MAX_ANSWER_LENGTH
        )
    
    @staticmethod
    def validate_question_id(question_id: int) -> int:
        """
        Validate question ID parameter.
        
        Args:
            question_id: Question ID to validate
            
        Returns:
            Validated question ID
            
        Raises:
            HTTPException: If question ID is invalid
        """
        if not isinstance(question_id, int):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid question ID format",
                    "message": "Question ID must be an integer",
                    "received_type": type(question_id).__name__
                }
            )
        
        if question_id <= 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid question ID",
                    "message": "Question ID must be a positive integer",
                    "received": question_id
                }
            )
        
        return question_id
    
    @staticmethod
    def validate_session_id(session_id: int) -> int:
        """
        Validate session ID parameter.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            Validated session ID
            
        Raises:
            HTTPException: If session ID is invalid
        """
        if not isinstance(session_id, int):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid session ID format",
                    "message": "Session ID must be an integer",
                    "received_type": type(session_id).__name__
                }
            )
        
        if session_id <= 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid session ID",
                    "message": "Session ID must be a positive integer",
                    "received": session_id
                }
            )
        
        return session_id
    
    @staticmethod
    def validate_pagination_params(limit: int = None, offset: int = None) -> Dict[str, int]:
        """
        Validate pagination parameters.
        
        Args:
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            Dictionary with validated limit and offset
            
        Raises:
            HTTPException: If pagination parameters are invalid
        """
        if limit is not None:
            if not isinstance(limit, int) or limit <= 0:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid limit parameter",
                        "message": "Limit must be a positive integer",
                        "received": limit
                    }
                )
            if limit > 100:  # Reasonable upper limit
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Limit too high",
                        "message": "Limit cannot exceed 100",
                        "received": limit,
                        "maximum": 100
                    }
                )
        
        if offset is not None:
            if not isinstance(offset, int) or offset < 0:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid offset parameter",
                        "message": "Offset must be a non-negative integer",
                        "received": offset
                    }
                )
        
        return {
            "limit": limit or 10,
            "offset": offset or 0
        }
    
    @staticmethod
    def validate_audio_file_size(file_size: int, max_size_mb: int = 10) -> None:
        """
        Validate audio file size.
        
        Args:
            file_size: File size in bytes
            max_size_mb: Maximum allowed size in MB
            
        Raises:
            HTTPException: If file is too large
        """
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "File too large",
                    "message": f"Audio file must be smaller than {max_size_mb}MB",
                    "received_size_mb": round(file_size / (1024 * 1024), 2),
                    "maximum_size_mb": max_size_mb
                }
            )
    
    @staticmethod
    def validate_audio_file_type(filename: str, allowed_extensions: List[str] = None) -> str:
        """
        Validate audio file type.
        
        Args:
            filename: Name of the uploaded file
            allowed_extensions: List of allowed file extensions
            
        Returns:
            Validated file extension
            
        Raises:
            HTTPException: If file type is not allowed
        """
        if allowed_extensions is None:
            allowed_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
        
        if not filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No filename provided",
                    "message": "Audio file must have a filename"
                }
            )
        
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        if not file_extension or f'.{file_extension}' not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "message": f"Audio file must be one of: {', '.join(allowed_extensions)}",
                    "received": filename,
                    "allowed_types": allowed_extensions
                }
            )
        
        return file_extension

def create_service_query_param(description: str = "Preferred AI service") -> Query:
    """Create a standardized service query parameter with validation."""
    return Query(
        None, 
        description=f"{description}: {', '.join(InputValidator.ALLOWED_SERVICES)}"
    )

def create_language_query_param(description: str = "Language code for processing") -> Query:
    """Create a standardized language query parameter with validation."""
    return Query(
        LanguageCode.EN_US.value,
        description=f"{description}: {', '.join(InputValidator.ALLOWED_LANGUAGES)}"
    )
