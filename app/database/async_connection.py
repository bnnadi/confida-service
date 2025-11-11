"""
Async Database Connection Manager.

This module provides a compatibility layer for async database operations,
wrapping the unified database_service to provide the expected async_db_manager interface.
"""
from sqlalchemy.ext.asyncio import AsyncEngine
from app.services.database_service import database_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncDatabaseManager:
    """
    Compatibility wrapper for async database operations.
    
    This class provides the async_db_manager interface expected by
    async_database_monitor and other services, while using the
    unified database_service under the hood.
    """
    
    def __init__(self):
        self._database_service = database_service
    
    @property
    def engine(self) -> AsyncEngine:
        """
        Get the async database engine.
        
        Returns:
            AsyncEngine: The async SQLAlchemy engine
            
        Raises:
            RuntimeError: If database service is not initialized
        """
        engine = self._database_service.async_engine
        if not engine:
            raise RuntimeError("Async database engine not initialized")
        return engine
    
    async def close(self) -> None:
        """
        Close async database connections.
        
        This method disposes of the async engine and closes all connections.
        """
        await self._database_service.close_async()
        logger.info("✅ Async database manager closed")


# Global instance for compatibility with existing code
async_db_manager = AsyncDatabaseManager()

