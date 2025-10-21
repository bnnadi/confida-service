"""
Simplified File Validator using Unified Validation Service

This replaces the complex file_validator.py with a simplified version
that uses the unified validation service.
"""
from typing import List, Tuple
from fastapi import UploadFile
from app.models.schemas import FileType
from app.utils.unified_validation_service import UnifiedValidationService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class FileValidator:
    """Simplified file validator using unified validation service."""
    
    def __init__(self):
        self.validation_service = UnifiedValidationService()
    
    def validate_file(self, file: UploadFile, file_type: FileType) -> Tuple[bool, List[str]]:
        """Validate file using unified validation service."""
        return self.validation_service.validate_file(file, file_type)
    
    def validate_file_type(self, file: UploadFile, expected_type: FileType) -> Tuple[bool, str]:
        """Validate file type using unified validation service."""
        return self.validation_service.validate_file_type(file, expected_type)
    
    def validate_file_size(self, file: UploadFile, file_type: FileType) -> Tuple[bool, str]:
        """Validate file size using unified validation service."""
        return self.validation_service.validate_file_size(file, file_type)
    
    def validate_file_content(self, file: UploadFile) -> Tuple[bool, str]:
        """Validate file content using unified validation service."""
        return self.validation_service.validate_file_content(file)
