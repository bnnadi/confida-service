"""
Dependency injection utilities for Confida application.

This module now uses the unified services for consistent dependency injection.
"""

from typing import Optional, AsyncGenerator, Any
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.service_factory import get_ai_client
from app.services.database_service import get_db, get_async_db
from app.services.file_service import FileService
from app.services.dashboard_service import DashboardService
from app.services.analytics_service import AnalyticsService
from app.services.tts.service import TTSService, get_tts_service
from app.utils.validation import ValidationService
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

def get_file_service(db: Session = Depends(get_db)) -> FileService:
    """Dependency to get file service."""
    return FileService(db)

def get_validation_service() -> ValidationService:
    """Dependency to get validation service."""
    return ValidationService()

def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """Dependency to get dashboard service."""
    return DashboardService(db)

def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    """Dependency to get analytics service."""
    return AnalyticsService(db)

def get_ai_client_dependency() -> Optional[Any]:
    """Get AI service client instance."""
    try:
        return get_ai_client()
    except Exception as e:
        logger.warning(f"Could not initialize AI service client: {e}")
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

# Note: AI service dependencies simplified to use only AI service client
