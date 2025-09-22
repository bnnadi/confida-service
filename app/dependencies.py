"""
Dependency injection utilities for InterviewIQ application.
"""

from functools import lru_cache
from typing import Optional
from app.services.hybrid_ai_service import HybridAIService
from app.utils.logger import get_logger

logger = get_logger(__name__)

@lru_cache()
def get_ai_service() -> Optional[HybridAIService]:
    """Get AI service instance with caching."""
    try:
        return HybridAIService()
    except Exception as e:
        logger.warning(f"Could not initialize HybridAIService: {e}")
        return None
