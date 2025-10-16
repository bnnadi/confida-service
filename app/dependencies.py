"""
Dependency injection utilities for InterviewIQ application.
"""

from functools import lru_cache
from typing import Optional, AsyncGenerator
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.unified_ai_service import UnifiedAIService, AsyncUnifiedAIService
from app.utils.logger import get_logger
from app.database.connection import get_db
from app.database.async_connection import get_async_db
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

def get_ai_service(db: Session = Depends(get_db)) -> Optional[UnifiedAIService]:
    """Get AI service instance with database session for question bank integration."""
    try:
        return UnifiedAIService(db_session=db)
    except Exception as e:
        logger.warning(f"Could not initialize UnifiedAIService: {e}")
        return None

async def get_async_ai_service(db: AsyncSession = Depends(get_async_db)) -> Optional[AsyncUnifiedAIService]:
    """Get AI service instance with async database session for question bank integration."""
    try:
        return AsyncUnifiedAIService(db_session=db)
    except Exception as e:
        logger.warning(f"Could not initialize AsyncUnifiedAIService with async session: {e}")
        return None

def get_database_session() -> Session:
    """Get synchronous database session."""
    return Depends(get_db)

async def get_async_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with get_async_db() as session:
        yield session

# Choose database session based on configuration
def get_database_dependency():
    """Get appropriate database dependency based on configuration."""
    if settings.ASYNC_DATABASE_ENABLED:
        return get_async_database_session
    else:
        return get_database_session

def get_ai_service_dependency():
    """Get appropriate AI service dependency based on configuration."""
    if settings.ASYNC_DATABASE_ENABLED:
        return get_async_ai_service
    else:
        return get_ai_service
