from typing import List, Tuple, Optional
from app.utils.validation import ValidationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigValidator:
    """Configuration validation utility using unified validation service."""

    def __init__(self, validation_service: Optional[ValidationService] = None):
        """Initialize with optional ValidationService (injectable for testability)."""
        self.validation_service = validation_service or ValidationService()
    
    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Validate all configuration settings using unified validation service."""
        return self.validation_service.validate_configuration()
