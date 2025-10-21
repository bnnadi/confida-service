from typing import List, Tuple
from app.utils.unified_validation_service import UnifiedValidationService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ConfigValidator:
    """Configuration validation utility using unified validation service."""
    
    def __init__(self):
        self.validation_service = UnifiedValidationService()
    
    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Validate all configuration settings using unified validation service."""
        return self.validation_service.validate_configuration()
