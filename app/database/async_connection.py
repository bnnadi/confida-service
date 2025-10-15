"""
Async database connection and session management with connection pooling.

This module provides async database operations with proper connection pooling,
monitoring, and health checks for high-performance applications.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
from app.config import get_settings
from app.utils.logger import get_logger
import time
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = get_logger(__name__)
settings = get_settings()

@dataclass
class ConnectionPoolStats:
    """Connection pool statistics for monitoring."""
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int
    created_at: datetime
    last_checked: datetime

class AsyncDatabaseManager:
    """Async database manager with connection pooling and monitoring."""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._stats: Optional[ConnectionPoolStats] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_enabled = True
        self._lock = threading.Lock()
    
    async def initialize(self) -> None:
        """Initialize async database engine and session factory."""
        try:
            # Convert sync database URL to async
            database_url = self._convert_to_async_url(settings.DATABASE_URL)
            
            # Create async engine with connection pooling
            if database_url.startswith("sqlite+aiosqlite"):
                # SQLite async configuration
                self.engine = create_async_engine(
                    database_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False}
                )
            else:
                # PostgreSQL async configuration with advanced pooling
                self.engine = create_async_engine(
                    database_url,
                    echo=False,
                    pool_size=settings.ASYNC_DATABASE_POOL_SIZE,
                    max_overflow=settings.ASYNC_DATABASE_MAX_OVERFLOW,
                    pool_timeout=settings.ASYNC_DATABASE_POOL_TIMEOUT,
                    pool_recycle=settings.ASYNC_DATABASE_POOL_RECYCLE,
                    pool_pre_ping=True
                )
            
            # Create async session factory
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Set up connection pool event listeners for monitoring
            self._setup_pool_monitoring()
            
            # Start monitoring task
            if self._monitoring_enabled and settings.ASYNC_DATABASE_MONITORING_ENABLED:
                self._monitoring_task = asyncio.create_task(self._monitor_connections())
                
                # Start database monitor
                from app.services.async_database_monitor import async_db_monitor
                asyncio.create_task(async_db_monitor.start_monitoring())
            
            logger.info("✅ Async database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize async database: {e}")
            raise
    
    def _convert_to_async_url(self, sync_url: str) -> str:
        """Convert synchronous database URL to async URL."""
        if sync_url.startswith("postgresql://"):
            return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif sync_url.startswith("sqlite:///"):
            return sync_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        elif sync_url.startswith("mysql://"):
            return sync_url.replace("mysql://", "mysql+aiomysql://", 1)
        else:
            return sync_url
    
    def _setup_pool_monitoring(self) -> None:
        """Set up connection pool event listeners for monitoring."""
        if not self.engine:
            return
        
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Log when a new connection is created."""
            logger.debug("🔗 New database connection created")
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log when a connection is checked out from the pool."""
            logger.debug("📤 Database connection checked out")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Log when a connection is checked back into the pool."""
            logger.debug("📥 Database connection checked in")
        
        @event.listens_for(self.engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Log when a connection is invalidated."""
            logger.warning(f"⚠️ Database connection invalidated: {exception}")
    
    async def _monitor_connections(self) -> None:
        """Monitor connection pool health and statistics."""
        while self._monitoring_enabled:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._update_pool_stats()
                
                # Log pool statistics periodically
                if self._stats:
                    logger.debug(f"📊 Pool stats - Size: {self._stats.pool_size}, "
                               f"Checked out: {self._stats.checked_out}, "
                               f"Overflow: {self._stats.overflow}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error monitoring connections: {e}")
    
    async def _update_pool_stats(self) -> None:
        """Update connection pool statistics."""
        if not self.engine:
            return
        
        try:
            pool = self.engine.pool
            self._stats = ConnectionPoolStats(
                pool_size=pool.size(),
                checked_in=pool.checkedin(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
                invalid=pool.invalid(),
                created_at=datetime.utcnow(),
                last_checked=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"❌ Error updating pool stats: {e}")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with proper cleanup."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def check_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            if not self.session_factory:
                return False
            
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
            logger.debug("✅ Async database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Async database connection failed: {e}")
            return False
    
    async def get_pool_stats(self) -> Optional[ConnectionPoolStats]:
        """Get current connection pool statistics."""
        await self._update_pool_stats()
        return self._stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive database health check."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "connection_check": False,
            "pool_stats": None,
            "errors": []
        }
        
        try:
            # Test connection
            health_status["connection_check"] = await self.check_connection()
            
            # Get pool statistics
            health_status["pool_stats"] = await self.get_pool_stats()
            
            # Check for potential issues
            if health_status["pool_stats"]:
                stats = health_status["pool_stats"]
                if stats.overflow > 0:
                    health_status["errors"].append(f"Connection pool overflow: {stats.overflow}")
                if stats.invalid > 0:
                    health_status["errors"].append(f"Invalid connections: {stats.invalid}")
                if stats.checked_out > stats.pool_size * 0.8:
                    health_status["errors"].append("High connection usage detected")
            
            if health_status["errors"]:
                health_status["status"] = "degraded"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["errors"].append(str(e))
        
        return health_status
    
    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        try:
            self._monitoring_enabled = False
            
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            if self.engine:
                await self.engine.dispose()
                logger.info("✅ Async database connections closed")
                
        except Exception as e:
            logger.error(f"❌ Error closing database connections: {e}")

# Global async database manager instance
async_db_manager = AsyncDatabaseManager()

# Dependency function for FastAPI
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get async database session."""
    if not async_db_manager.session_factory:
        raise RuntimeError("Async database not initialized. Call init_async_db() first.")
    
    async with async_db_manager.session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            await session.close()

# Initialize database on startup
async def init_async_db() -> None:
    """Initialize async database on application startup."""
    await async_db_manager.initialize()
    
    # Import all models to ensure they're registered
    from app.database import models
    
    # Create all tables
    async with async_db_manager.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    logger.info("✅ Async database tables created successfully")

# Health check endpoint data
async def get_db_health() -> Dict[str, Any]:
    """Get database health status for monitoring endpoints."""
    return await async_db_manager.health_check()

# Connection pool statistics
async def get_connection_pool_stats() -> Optional[ConnectionPoolStats]:
    """Get connection pool statistics for monitoring."""
    return await async_db_manager.get_pool_stats()
