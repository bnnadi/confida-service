"""
Async Database Connection Management with Connection Pooling.

This module provides async database connection management with connection pooling
for optimal performance and resource management.
"""
import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncDatabaseConfig:
    """Configuration for async database operations."""
    
    def __init__(self):
        settings = get_settings()
        self.pool_size = getattr(settings, 'DB_POOL_SIZE', 20)
        self.max_overflow = getattr(settings, 'DB_MAX_OVERFLOW', 30)
        self.pool_timeout = getattr(settings, 'DB_POOL_TIMEOUT', 30)
        self.pool_recycle = getattr(settings, 'DB_POOL_RECYCLE', 3600)
        self.echo = getattr(settings, 'DB_ECHO', False)
        self.database_url = settings.DATABASE_URL


class ConnectionPoolMetrics:
    """Metrics for connection pool monitoring."""
    
    def __init__(self):
        self.total_connections = 0
        self.active_connections = 0
        self.idle_connections = 0
        self.connection_requests = 0
        self.connection_timeouts = 0
        self.connection_errors = 0
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pool metrics."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "connection_requests": self.connection_requests,
            "connection_timeouts": self.connection_timeouts,
            "connection_errors": self.connection_errors,
            "pool_utilization": self.active_connections / max(self.total_connections, 1)
        }


class AsyncDatabasePoolManager:
    """Manages async database connection pool."""
    
    def __init__(self):
        self.config = AsyncDatabaseConfig()
        self.pool: Optional[asyncpg.Pool] = None
        self.metrics = ConnectionPoolMetrics()
        self._initialized = False
    
    async def initialize_pool(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return
        
        try:
            logger.info(f"Initializing async database pool with size {self.config.pool_size}")
            
            self.pool = await asyncpg.create_pool(
                self.config.database_url,
                min_size=self.config.pool_size,
                max_size=self.config.max_overflow,
                command_timeout=self.config.pool_timeout,
                server_settings={
                    'application_name': 'interviewiq_service',
                    'jit': 'off'  # Disable JIT for better connection stability
                }
            )
            
            self.metrics.total_connections = self.config.pool_size
            self._initialized = True
            
            logger.info(f"✅ Async database pool initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize async database pool: {e}")
            raise
    
    async def close_pool(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._initialized = False
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if not self._initialized:
            await self.initialize_pool()
        
        connection = None
        try:
            self.metrics.connection_requests += 1
            connection = await self.pool.acquire()
            self.metrics.active_connections += 1
            self.metrics.idle_connections = max(0, self.metrics.idle_connections - 1)
            
            yield connection
            
        except asyncio.TimeoutError:
            self.metrics.connection_timeouts += 1
            logger.warning("Connection request timed out")
            raise
        except Exception as e:
            self.metrics.connection_errors += 1
            logger.error(f"Connection error: {e}")
            raise
        finally:
            if connection:
                await self.pool.release(connection)
                self.metrics.active_connections = max(0, self.metrics.active_connections - 1)
                self.metrics.idle_connections += 1
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        async with self.get_connection() as conn:
            try:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a command and return the result."""
        async with self.get_connection() as conn:
            try:
                result = await conn.execute(command, *args)
                return result
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row."""
        async with self.get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"Fetch one failed: {e}")
                raise
    
    async def fetch_many(self, query: str, *args, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch multiple rows with limit."""
        async with self.get_connection() as conn:
            try:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows[:limit]]
            except Exception as e:
                logger.error(f"Fetch many failed: {e}")
                raise
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and metrics."""
        if not self.pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "active",
            "pool_size": self.pool.get_size(),
            "pool_min_size": self.pool.get_min_size(),
            "pool_max_size": self.pool.get_max_size(),
            "pool_idle_size": self.pool.get_idle_size(),
            "metrics": self.metrics.get_metrics()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database connection."""
        try:
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                return {
                    "status": "healthy",
                    "database_connected": True,
                    "test_query_result": result
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "database_connected": False,
                "error": str(e)
            }


# Global pool manager instance
_pool_manager: Optional[AsyncDatabasePoolManager] = None


async def get_async_db_pool() -> AsyncDatabasePoolManager:
    """Get the global async database pool manager."""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = AsyncDatabasePoolManager()
        await _pool_manager.initialize_pool()
    return _pool_manager


async def close_async_db_pool() -> None:
    """Close the global async database pool."""
    global _pool_manager
    if _pool_manager:
        await _pool_manager.close_pool()
        _pool_manager = None


@asynccontextmanager
async def get_async_db_connection():
    """Get an async database connection from the global pool."""
    pool_manager = await get_async_db_pool()
    async with pool_manager.get_connection() as conn:
        yield conn


# Dependency for FastAPI
async def get_async_db():
    """FastAPI dependency for async database connection."""
    pool_manager = await get_async_db_pool()
    async with pool_manager.get_connection() as conn:
        yield conn