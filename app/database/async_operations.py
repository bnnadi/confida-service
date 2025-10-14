"""
Async database operations utilities.

This module provides common async database operations and utilities
for working with async SQLAlchemy sessions.
"""
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from app.utils.logger import get_logger
import asyncio
from datetime import datetime

logger = get_logger(__name__)

T = TypeVar('T')

class AsyncDatabaseOperations:
    """Async database operations utility class."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, model: Type[T], **kwargs) -> T:
        """Create a new record asynchronously."""
        try:
            instance = model(**kwargs)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            logger.debug(f"✅ Created {model.__name__} record: {instance.id}")
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Error creating {model.__name__}: {e}")
            raise
    
    async def get_by_id(self, model: Type[T], record_id: Any) -> Optional[T]:
        """Get a record by ID asynchronously."""
        try:
            result = await self.session.execute(
                select(model).where(model.id == record_id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting {model.__name__} by ID {record_id}: {e}")
            raise
    
    async def get_by_field(self, model: Type[T], field_name: str, field_value: Any) -> Optional[T]:
        """Get a record by field value asynchronously."""
        try:
            field = getattr(model, field_name)
            result = await self.session.execute(
                select(model).where(field == field_value)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting {model.__name__} by {field_name}: {e}")
            raise
    
    async def get_all(
        self, 
        model: Type[T], 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[T]:
        """Get all records with optional filtering and pagination."""
        try:
            query = select(model)
            
            # Apply filters
            if filters:
                for field_name, field_value in filters.items():
                    if hasattr(model, field_name):
                        field = getattr(model, field_name)
                        query = query.where(field == field_value)
            
            # Apply ordering
            if order_by and hasattr(model, order_by):
                order_field = getattr(model, order_by)
                query = query.order_by(order_field)
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting all {model.__name__}: {e}")
            raise
    
    async def update_by_id(self, model: Type[T], record_id: Any, **kwargs) -> Optional[T]:
        """Update a record by ID asynchronously."""
        try:
            # First get the record
            record = await self.get_by_id(model, record_id)
            if not record:
                return None
            
            # Update fields
            for field_name, field_value in kwargs.items():
                if hasattr(record, field_name):
                    setattr(record, field_name, field_value)
            
            await self.session.commit()
            await self.session.refresh(record)
            logger.debug(f"✅ Updated {model.__name__} record: {record_id}")
            return record
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Error updating {model.__name__} {record_id}: {e}")
            raise
    
    async def delete_by_id(self, model: Type[T], record_id: Any) -> bool:
        """Delete a record by ID asynchronously."""
        try:
            result = await self.session.execute(
                delete(model).where(model.id == record_id)
            )
            await self.session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.debug(f"✅ Deleted {model.__name__} record: {record_id}")
            return deleted
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Error deleting {model.__name__} {record_id}: {e}")
            raise
    
    async def count(self, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filtering."""
        try:
            query = select(func.count(model.id))
            
            if filters:
                for field_name, field_value in filters.items():
                    if hasattr(model, field_name):
                        field = getattr(model, field_name)
                        query = query.where(field == field_value)
            
            result = await self.session.execute(query)
            return result.scalar()
        except SQLAlchemyError as e:
            logger.error(f"❌ Error counting {model.__name__}: {e}")
            raise
    
    async def exists(self, model: Type[T], filters: Dict[str, Any]) -> bool:
        """Check if a record exists with given filters."""
        try:
            query = select(model.id)
            
            for field_name, field_value in filters.items():
                if hasattr(model, field_name):
                    field = getattr(model, field_name)
                    query = query.where(field == field_value)
            
            query = query.limit(1)
            result = await self.session.execute(query)
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            logger.error(f"❌ Error checking existence of {model.__name__}: {e}")
            raise
    
    async def bulk_create(self, model: Type[T], records: List[Dict[str, Any]]) -> List[T]:
        """Create multiple records in bulk asynchronously."""
        try:
            instances = [model(**record_data) for record_data in records]
            self.session.add_all(instances)
            await self.session.commit()
            
            # Refresh all instances to get their IDs
            for instance in instances:
                await self.session.refresh(instance)
            
            logger.debug(f"✅ Bulk created {len(instances)} {model.__name__} records")
            return instances
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Error bulk creating {model.__name__}: {e}")
            raise
    
    async def bulk_update(self, model: Type[T], updates: List[Dict[str, Any]]) -> int:
        """Update multiple records in bulk asynchronously."""
        try:
            updated_count = 0
            
            for update_data in updates:
                record_id = update_data.pop('id', None)
                if record_id:
                    result = await self.session.execute(
                        update(model)
                        .where(model.id == record_id)
                        .values(**update_data)
                    )
                    updated_count += result.rowcount
            
            await self.session.commit()
            logger.debug(f"✅ Bulk updated {updated_count} {model.__name__} records")
            return updated_count
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Error bulk updating {model.__name__}: {e}")
            raise
    
    async def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute raw SQL query asynchronously."""
        try:
            result = await self.session.execute(text(query), params or {})
            await self.session.commit()
            return result
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Error executing raw query: {e}")
            raise
    
    async def get_with_relationships(
        self, 
        model: Type[T], 
        record_id: Any, 
        relationships: List[str]
    ) -> Optional[T]:
        """Get a record with specified relationships loaded."""
        try:
            query = select(model).where(model.id == record_id)
            
            # Add relationship loading
            for relationship in relationships:
                if hasattr(model, relationship):
                    query = query.options(selectinload(getattr(model, relationship)))
            
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"❌ Error getting {model.__name__} with relationships: {e}")
            raise
    
    async def paginate(
        self,
        model: Type[T],
        page: int = 1,
        per_page: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Paginate records with metadata."""
        try:
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Get total count
            total = await self.count(model, filters)
            
            # Get records for current page
            records = await self.get_all(
                model=model,
                limit=per_page,
                offset=offset,
                filters=filters,
                order_by=order_by
            )
            
            # Calculate pagination metadata
            total_pages = (total + per_page - 1) // per_page
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                "records": records,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev,
                    "next_page": page + 1 if has_next else None,
                    "prev_page": page - 1 if has_prev else None
                }
            }
        except SQLAlchemyError as e:
            logger.error(f"❌ Error paginating {model.__name__}: {e}")
            raise

# Utility functions for common async database operations
async def async_create_record(session: AsyncSession, model: Type[T], **kwargs) -> T:
    """Create a record using async database operations."""
    db_ops = AsyncDatabaseOperations(session)
    return await db_ops.create(model, **kwargs)

async def async_get_record_by_id(session: AsyncSession, model: Type[T], record_id: Any) -> Optional[T]:
    """Get a record by ID using async database operations."""
    db_ops = AsyncDatabaseOperations(session)
    return await db_ops.get_by_id(model, record_id)

async def async_get_records(
    session: AsyncSession, 
    model: Type[T], 
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    filters: Optional[Dict[str, Any]] = None
) -> List[T]:
    """Get records using async database operations."""
    db_ops = AsyncDatabaseOperations(session)
    return await db_ops.get_all(model, limit, offset, filters=filters)

async def async_update_record(session: AsyncSession, model: Type[T], record_id: Any, **kwargs) -> Optional[T]:
    """Update a record using async database operations."""
    db_ops = AsyncDatabaseOperations(session)
    return await db_ops.update_by_id(model, record_id, **kwargs)

async def async_delete_record(session: AsyncSession, model: Type[T], record_id: Any) -> bool:
    """Delete a record using async database operations."""
    db_ops = AsyncDatabaseOperations(session)
    return await db_ops.delete_by_id(model, record_id)

async def async_count_records(session: AsyncSession, model: Type[T], filters: Optional[Dict[str, Any]] = None) -> int:
    """Count records using async database operations."""
    db_ops = AsyncDatabaseOperations(session)
    return await db_ops.count(model, filters)

# Transaction management utilities
async def async_transaction(session: AsyncSession):
    """Context manager for async database transactions."""
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise

async def async_bulk_operation(session: AsyncSession, operations: List[callable]):
    """Execute multiple async database operations in a single transaction."""
    try:
        results = []
        for operation in operations:
            result = await operation(session)
            results.append(result)
        await session.commit()
        return results
    except Exception:
        await session.rollback()
        raise
