# Async Database Operations Guide

## Overview

This guide covers the implementation of asynchronous database operations in Confida, including connection pooling, monitoring, and performance optimization.

## Features

### 1. Async Database Connection Pooling
- **Connection Pool Management**: Advanced connection pooling with configurable pool size, overflow, and timeout settings
- **Automatic Connection Recovery**: Built-in connection health checks and automatic reconnection
- **Performance Optimization**: Optimized for high-concurrency scenarios

### 2. Async Database Operations
- **Async/Await Support**: All database operations use async/await for non-blocking I/O
- **Transaction Management**: Proper async transaction handling with rollback support
- **Query Optimization**: Efficient async query execution with connection reuse

### 3. Connection Pool Monitoring
- **Real-time Metrics**: Live monitoring of connection pool status and performance
- **Health Checks**: Comprehensive health status reporting
- **Performance Tracking**: Response time and throughput monitoring

## Configuration

### Environment Variables

```bash
# Async Database Settings
ASYNC_DATABASE_ENABLED=true
ASYNC_DATABASE_POOL_SIZE=20
ASYNC_DATABASE_MAX_OVERFLOW=30
ASYNC_DATABASE_POOL_TIMEOUT=30
ASYNC_DATABASE_POOL_RECYCLE=3600
ASYNC_DATABASE_MONITORING_ENABLED=true
```

### Database URLs

```bash
# PostgreSQL (Production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/database

# SQLite (Development/Testing)
DATABASE_URL=sqlite+aiosqlite:///./database.db
```

## Architecture

### Core Components

1. **AsyncDatabaseManager**: Manages async engine and session factory
2. **AsyncDatabaseOperations**: Utility functions for common database operations
3. **AsyncQuestionBankService**: Async operations for question bank management
4. **AsyncHybridAIService**: Async AI service with database integration
5. **AsyncSessionService**: Async session management
6. **AsyncDatabaseMonitor**: Connection pool monitoring and health checks

### Service Layer

```python
# Async Service Example
class AsyncQuestionBankService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.db_ops = AsyncDatabaseOperations(db_session)
    
    async def get_questions_for_role(self, role: str, job_description: str, count: int = 10):
        # Async database operations
        result = await self.db_session.execute(query)
        return result.scalars().all()
```

### API Layer

```python
# Async Endpoint Example
@router.post("/parse-jd")
async def parse_job_description(request: ParseJDRequest):
    if settings.ASYNC_DATABASE_ENABLED:
        async with get_async_db() as db:
            ai_service = await get_async_ai_service(db)
            response = await ai_service.generate_interview_questions(...)
            return response
    else:
        # Fallback to sync operations
        db = next(get_db())
        ai_service = get_ai_service(db)
        response = ai_service.generate_interview_questions(...)
        return response
```

## Usage Examples

### 1. Basic Async Database Operations

```python
from app.database.async_connection import get_async_db
from app.services.async_question_bank_service import AsyncQuestionBankService

async def get_questions():
    async with get_async_db() as db:
        service = AsyncQuestionBankService(db)
        questions = await service.get_questions_for_role("developer", "Python developer role")
        return questions
```

### 2. Transaction Management

```python
async def create_session_with_questions(user_id: str, role: str, questions: List[str]):
    async with get_async_db() as db:
        try:
            # Create session
            session = await session_service.create_session(user_id, role, "Job description")
            
            # Add questions
            await session_service.add_questions_to_session(session.id, questions, user_id)
            
            # Commit transaction
            await db.commit()
            return session
            
        except Exception as e:
            # Rollback on error
            await db.rollback()
            raise
```

### 3. Connection Pool Monitoring

```python
from app.services.async_database_monitor import async_db_monitor

async def check_database_health():
    health_status = await async_db_monitor.get_health_status()
    pool_status = await async_db_monitor.get_connection_pool_status()
    performance_metrics = await async_db_monitor.get_performance_metrics()
    
    return {
        "health": health_status,
        "pool": pool_status,
        "performance": performance_metrics
    }
```

## Monitoring and Health Checks

### Health Check Endpoints

- **`/health`**: Comprehensive health check including async database status
- **`/monitoring/database`**: Detailed database monitoring information
- **`/ready`**: Readiness check for Kubernetes deployments

### Monitoring Data

```json
{
  "health_status": {
    "status": "healthy",
    "connectivity": {
      "connected": true,
      "response_time_ms": 15.2
    },
    "pool_statistics": {
      "pool_size": 20,
      "checked_out": 5,
      "overflow": 0
    }
  },
  "performance_metrics": {
    "average_response_time_ms": 12.5,
    "average_active_connections": 3.2,
    "average_queries_per_second": 45.8
  }
}
```

## Performance Optimization

### Connection Pool Tuning

```python
# Production settings
ASYNC_DATABASE_POOL_SIZE=20          # Base pool size
ASYNC_DATABASE_MAX_OVERFLOW=30       # Additional connections
ASYNC_DATABASE_POOL_TIMEOUT=30       # Connection timeout
ASYNC_DATABASE_POOL_RECYCLE=3600     # Connection recycle time
```

### Query Optimization

```python
# Use selectinload for eager loading
result = await db.execute(
    select(Question)
    .options(selectinload(Question.session_questions))
    .where(Question.category == "technical")
)

# Use bulk operations for multiple inserts
await db.execute(
    insert(Question),
    [{"question_text": q, "category": "technical"} for q in questions]
)
```

## Error Handling

### Connection Errors

```python
try:
    async with get_async_db() as db:
        result = await db.execute(query)
        return result.scalars().all()
except Exception as e:
    logger.error(f"Database operation failed: {e}")
    raise HTTPException(status_code=500, detail="Database error")
```

### Transaction Rollback

```python
async def safe_database_operation():
    async with get_async_db() as db:
        try:
            # Database operations
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
```

## Testing

### Async Test Setup

```python
import pytest
from app.database.async_connection import get_async_db

@pytest.fixture
async def async_db_session():
    async with get_async_db() as session:
        yield session

@pytest.mark.asyncio
async def test_async_question_retrieval(async_db_session):
    service = AsyncQuestionBankService(async_db_session)
    questions = await service.get_questions_for_role("developer", "Python role")
    assert len(questions) > 0
```

## Migration from Sync to Async

### Step 1: Update Dependencies

```python
# Old sync dependency
def get_ai_service(db: Session = Depends(get_db)):
    return HybridAIService(db_session=db)

# New async dependency
async def get_async_ai_service(db: AsyncSession = Depends(get_async_db)):
    return AsyncHybridAIService(db_session=db)
```

### Step 2: Update Service Methods

```python
# Old sync method
def get_questions_for_role(self, role: str, job_description: str):
    result = self.db_session.query(Question).filter(...).all()
    return result

# New async method
async def get_questions_for_role(self, role: str, job_description: str):
    result = await self.db_session.execute(select(Question).where(...))
    return result.scalars().all()
```

### Step 3: Update API Endpoints

```python
# Old sync endpoint
@router.post("/parse-jd")
def parse_job_description(request: ParseJDRequest, db: Session = Depends(get_db)):
    # Sync operations
    pass

# New async endpoint
@router.post("/parse-jd")
async def parse_job_description(request: ParseJDRequest):
    if settings.ASYNC_DATABASE_ENABLED:
        async with get_async_db() as db:
            # Async operations
            pass
    else:
        # Fallback to sync
        pass
```

## Troubleshooting

### Common Issues

1. **Connection Pool Exhaustion**
   - Increase `ASYNC_DATABASE_POOL_SIZE`
   - Check for connection leaks
   - Monitor connection usage

2. **Slow Query Performance**
   - Check database indexes
   - Optimize query structure
   - Monitor response times

3. **Transaction Deadlocks**
   - Review transaction scope
   - Check for long-running transactions
   - Implement proper error handling

### Debugging

```python
# Enable SQL logging
DATABASE_ECHO=true

# Monitor connection pool
curl http://localhost:8000/monitoring/database

# Check health status
curl http://localhost:8000/health
```

## Best Practices

1. **Always use async context managers** for database sessions
2. **Implement proper error handling** with rollback support
3. **Monitor connection pool usage** to prevent exhaustion
4. **Use connection pooling** for better performance
5. **Implement health checks** for production monitoring
6. **Test async operations** thoroughly before deployment

## Future Enhancements

- [ ] Connection pool auto-scaling
- [ ] Advanced query caching
- [ ] Database sharding support
- [ ] Real-time performance dashboards
- [ ] Automated performance tuning
