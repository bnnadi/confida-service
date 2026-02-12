"""
Unified Database Service for Confida

This service consolidates all database operations, connection management,
and session handling into a single, comprehensive database service.
"""
import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Callable, AsyncGenerator
from sqlalchemy import create_engine, text, select, update, delete, func, JSON
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from datetime import datetime
from app.config import get_settings
from app.utils.logger import get_logger

# Patch JSONB for SQLite compatibility before importing models
try:
    from sqlalchemy.dialects.postgresql import JSONB
    import sqlalchemy.dialects.sqlite.base
    
    # Patch JSONB class to handle SQLite
    if JSONB is not None and not hasattr(JSONB, '_patched_for_sqlite'):
        # SQLAlchemy 2.x renamed load_dialect_impl to _gen_dialect_impl
        _impl_attr = 'load_dialect_impl' if hasattr(JSONB, 'load_dialect_impl') else '_gen_dialect_impl'
        original_impl = getattr(JSONB, _impl_attr)
        
        def _patched_load_dialect_impl(self, dialect):
            if dialect.name == 'sqlite':
                return dialect.type_descriptor(JSON())
            return original_impl(self, dialect)
        
        setattr(JSONB, _impl_attr, _patched_load_dialect_impl)
        JSONB._patched_for_sqlite = True
    
    # Patch SQLite compiler to handle JSONB
    if not hasattr(sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler, '_patched_for_jsonb'):
        def visit_JSONB(self, type_, **kw):
            return self.visit_JSON(type_, **kw)
        
        sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler.visit_JSONB = visit_JSONB
        sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler._patched_for_jsonb = True
except ImportError:
    # JSONB not available, skip patching
    pass

logger = get_logger(__name__)
settings = get_settings()

T = TypeVar('T')
Base = declarative_base()

class DatabaseService:
    """Unified database service that handles both sync and async operations."""
    
    def __init__(self):
        self.settings = settings
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database engines and session factories."""
        if self._initialized:
            return
        
        # Initialize sync engine
        self._sync_engine = self._create_sync_engine()
        self._sync_session_factory = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self._sync_engine
        )
        
        # Initialize async engine
        self._async_engine = self._create_async_engine()
        self._async_session_factory = async_sessionmaker(
            self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self._initialized = True
        logger.info("✅ Database service initialized successfully")
    
    def _create_sync_engine(self):
        """Create synchronous database engine."""
        database_url = self.settings.DATABASE_URL
        
        if database_url.startswith("sqlite"):
            return create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            return create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=self.settings.DATABASE_POOL_SIZE,
                max_overflow=self.settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=self.settings.DATABASE_POOL_TIMEOUT,
                pool_recycle=self.settings.DATABASE_POOL_RECYCLE
            )
    
    def _create_async_engine(self):
        """Create asynchronous database engine."""
        database_url = self.settings.DATABASE_URL
        
        # Convert sync URL to async URL
        if database_url.startswith("postgresql://"):
            async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("sqlite://"):
            async_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        else:
            async_url = database_url
        
        if async_url.startswith("sqlite+aiosqlite://"):
            return create_async_engine(
                async_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            return create_async_engine(
                async_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=self.settings.ASYNC_DATABASE_POOL_SIZE,
                max_overflow=self.settings.ASYNC_DATABASE_MAX_OVERFLOW,
                pool_timeout=self.settings.ASYNC_DATABASE_POOL_TIMEOUT,
                pool_recycle=self.settings.ASYNC_DATABASE_POOL_RECYCLE
            )
    
    # Session Management
    def get_sync_session(self) -> Session:
        """Get synchronous database session."""
        if not self._initialized:
            self.initialize()
        return self._sync_session_factory()
    
    def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session."""
        if not self._initialized:
            self.initialize()
        return self._async_session_factory()
    
    async def get_async_session_generator(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async session as generator for FastAPI dependency."""
        async with self._async_session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Database session error: {e}")
                raise
            finally:
                await session.close()
    
    # CRUD Operations - Sync
    def create_sync(self, model: Type[T], **kwargs) -> T:
        """Create a new record synchronously."""
        session = self.get_sync_session()
        try:
            instance = model(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            logger.debug(f"✅ Created {model.__name__} record: {instance.id}")
            return instance
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"❌ Failed to create {model.__name__}: {e}")
            raise
        finally:
            session.close()
    
    def get_by_id_sync(self, model: Type[T], record_id: Any) -> Optional[T]:
        """Get record by ID synchronously."""
        session = self.get_sync_session()
        try:
            return session.query(model).filter(model.id == record_id).first()
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get {model.__name__} by ID {record_id}: {e}")
            raise
        finally:
            session.close()
    
    def update_sync(self, model: Type[T], record_id: Any, **updates) -> Optional[T]:
        """Update record synchronously."""
        session = self.get_sync_session()
        try:
            instance = session.query(model).filter(model.id == record_id).first()
            if instance:
                for key, value in updates.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                logger.debug(f"✅ Updated {model.__name__} record: {record_id}")
                return instance
            return None
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"❌ Failed to update {model.__name__} {record_id}: {e}")
            raise
        finally:
            session.close()
    
    def delete_sync(self, model: Type[T], record_id: Any) -> bool:
        """Delete record synchronously."""
        session = self.get_sync_session()
        try:
            instance = session.query(model).filter(model.id == record_id).first()
            if instance:
                session.delete(instance)
                session.commit()
                logger.debug(f"✅ Deleted {model.__name__} record: {record_id}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"❌ Failed to delete {model.__name__} {record_id}: {e}")
            raise
        finally:
            session.close()
    
    # CRUD Operations - Async
    async def create_async(self, session: AsyncSession, model: Type[T], **kwargs) -> T:
        """Create a new record asynchronously."""
        try:
            instance = model(**kwargs)
            session.add(instance)
            await session.flush()
            await session.refresh(instance)
            logger.debug(f"✅ Created {model.__name__} record: {instance.id}")
            return instance
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"❌ Failed to create {model.__name__}: {e}")
            raise
    
    async def get_by_id_async(self, session: AsyncSession, model: Type[T], record_id: Any) -> Optional[T]:
        """Get record by ID asynchronously."""
        try:
            result = await session.execute(
                select(model).where(model.id == record_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to get {model.__name__} by ID {record_id}: {e}")
            raise
    
    async def update_async(self, session: AsyncSession, model: Type[T], record_id: Any, **updates) -> Optional[T]:
        """Update record asynchronously."""
        try:
            result = await session.execute(
                select(model).where(model.id == record_id)
            )
            instance = result.scalar_one_or_none()
            if instance:
                for key, value in updates.items():
                    setattr(instance, key, value)
                await session.flush()
                await session.refresh(instance)
                logger.debug(f"✅ Updated {model.__name__} record: {record_id}")
                return instance
            return None
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"❌ Failed to update {model.__name__} {record_id}: {e}")
            raise
    
    async def delete_async(self, session: AsyncSession, model: Type[T], record_id: Any) -> bool:
        """Delete record asynchronously."""
        try:
            result = await session.execute(
                select(model).where(model.id == record_id)
            )
            instance = result.scalar_one_or_none()
            if instance:
                await session.delete(instance)
                await session.flush()
                logger.debug(f"✅ Deleted {model.__name__} record: {record_id}")
                return True
            return False
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"❌ Failed to delete {model.__name__} {record_id}: {e}")
            raise
    
    # Query Operations
    async def execute_query_async(self, session: AsyncSession, query: Any) -> Any:
        """Execute raw query asynchronously."""
        try:
            result = await session.execute(query)
            return result
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to execute query: {e}")
            raise
    
    def execute_query_sync(self, query: Any) -> Any:
        """Execute raw query synchronously."""
        session = self.get_sync_session()
        try:
            result = session.execute(query)
            return result
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to execute query: {e}")
            raise
        finally:
            session.close()
    
    # Health Check
    async def health_check_async(self) -> Dict[str, Any]:
        """Check database health asynchronously."""
        try:
            async with self._async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                return {
                    "status": "healthy",
                    "async_connection": True,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"❌ Async database health check failed: {e}")
            return {
                "status": "unhealthy",
                "async_connection": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def health_check_sync(self) -> Dict[str, Any]:
        """Check database health synchronously."""
        try:
            session = self.get_sync_session()
            session.execute(text("SELECT 1"))
            session.close()
            return {
                "status": "healthy",
                "sync_connection": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Sync database health check failed: {e}")
            return {
                "status": "unhealthy",
                "sync_connection": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # Database Initialization
    def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            self.initialize()
        
        from app.database.models import Base
        Base.metadata.create_all(bind=self._sync_engine)
        logger.info("✅ Database tables created successfully")
    
    def drop_tables(self):
        """Drop all database tables."""
        if not self._initialized:
            self.initialize()
        
        from app.database.models import Base
        Base.metadata.drop_all(bind=self._sync_engine)
        logger.info("✅ Database tables dropped successfully")
    
    # Engine Access (Public API)
    @property
    def async_engine(self) -> Optional[AsyncEngine]:
        """
        Get the async database engine.
        
        Returns:
            Optional[AsyncEngine]: The async SQLAlchemy engine, or None if not initialized
        """
        if not self._initialized:
            self.initialize()
        return self._async_engine
    
    @property
    def is_initialized(self) -> bool:
        """Check if the database service is initialized."""
        return self._initialized
    
    # Cleanup
    async def close_async(self):
        """Close async database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("✅ Async database connections closed")
    
    def close_sync(self):
        """Close sync database connections."""
        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("✅ Sync database connections closed")

# Global database service instance
database_service = DatabaseService()

# FastAPI dependency functions
def get_db() -> Session:
    """FastAPI dependency to get sync database session."""
    return database_service.get_sync_session()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get async database session."""
    async for session in database_service.get_async_session_generator():
        yield session

# Convenience functions
def init_database():
    """Initialize database with tables."""
    try:
        database_service.initialize()
        database_service.create_tables()
        logger.info("✅ Database initialization completed successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

async def init_async_database():
    """Initialize async database."""
    try:
        database_service.initialize()
        logger.info("✅ Async database initialization completed successfully")
    except Exception as e:
        logger.error(f"❌ Async database initialization failed: {e}")
        raise

# Alias for backward compatibility
async def init_async_db():
    """Alias for init_async_database() for backward compatibility."""
    return await init_async_database()

async def get_db_health() -> Dict[str, Any]:
    """Get async database health status."""
    return await database_service.health_check_async()
