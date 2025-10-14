"""
Dependency injection utilities for InterviewIQ application.
"""

from functools import lru_cache
from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session
from app.services.hybrid_ai_service import HybridAIService
from app.utils.logger import get_logger
from app.database.connection import get_db

logger = get_logger(__name__)

def get_ai_service(db: Session = Depends(get_db)) -> Optional[HybridAIService]:
    """Get AI service instance with database session for question bank integration."""
    try:
        return HybridAIService(db_session=db)
    except Exception as e:
        logger.warning(f"Could not initialize HybridAIService: {e}")
        return None
