"""
Dependency injection utilities for Confida application.

This module now uses the unified services for consistent dependency injection.
"""

from typing import Optional, AsyncGenerator, Any
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.service_factory import get_ai_service, get_async_ai_service
from app.services.database_service import get_db, get_async_db
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

def get_ai_service_dependency(db: Session = Depends(get_db)) -> Optional[Any]:
    """Get AI service instance with database session for question bank integration."""
    try:
        return get_ai_service(db_session=db)
    except Exception as e:
        logger.warning(f"Could not initialize AI service: {e}")
        return None

async def get_async_ai_service_dependency(db: AsyncSession = Depends(get_async_db)) -> Optional[Any]:
    """Get AI service instance with async database session for question bank integration."""
    try:
        return get_async_ai_service(async_db_session=db)
    except Exception as e:
        logger.warning(f"Could not initialize async AI service: {e}")
        return None

def get_database_session() -> Session:
    """Get synchronous database session."""
    return Depends(get_db)

async def get_async_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async for session in get_async_db():
        yield session

# Choose database session based on configuration
def get_database_dependency():
    """Get appropriate database dependency based on configuration."""
    if settings.ASYNC_DATABASE_ENABLED:
        return get_async_database_session
    else:
        return get_database_session

def get_ai_service_dependency_wrapper():
    """Get appropriate AI service dependency based on configuration."""
    if settings.ASYNC_DATABASE_ENABLED:
        return get_async_ai_service_dependency
    else:
        return get_ai_service_dependency
