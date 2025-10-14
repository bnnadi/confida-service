# Async Database Migration - Quick Reference

## 🚀 **Quick Start**

### Enable Async Mode
```bash
export ASYNC_DATABASE_ENABLED=true
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db
```

### Disable Async Mode (Rollback)
```bash
export ASYNC_DATABASE_ENABLED=false
```

## 📁 **File Structure**

```
app/
├── database/
│   ├── async_connection.py          # NEW: Async DB connections
│   ├── async_operations.py          # NEW: Async DB utilities
│   └── connection.py                # EXISTING: Sync DB connections
├── services/
│   ├── async_question_bank_service.py    # NEW: Async question bank
│   ├── async_hybrid_ai_service.py        # NEW: Async AI service
│   ├── async_session_service.py          # NEW: Async session service
│   ├── async_database_monitor.py         # NEW: DB monitoring
│   ├── question_bank_service.py          # EXISTING: Sync question bank
│   └── hybrid_ai_service.py              # EXISTING: Sync AI service
└── routers/
    └── interview.py                       # MODIFIED: Dual mode support
```

## 🔧 **Configuration**

### Environment Variables
```bash
# Async Database Settings
ASYNC_DATABASE_ENABLED=true
ASYNC_DATABASE_POOL_SIZE=20
ASYNC_DATABASE_MAX_OVERFLOW=30
ASYNC_DATABASE_POOL_TIMEOUT=30
ASYNC_DATABASE_POOL_RECYCLE=3600
ASYNC_DATABASE_MONITORING_ENABLED=true

# Database URLs
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db  # Async
DATABASE_URL=postgresql://user:pass@localhost:5432/db          # Sync
```

## 🎯 **Key Endpoints**

| Endpoint | Purpose | Async Support |
|----------|---------|---------------|
| `POST /api/v1/parse-jd` | Generate questions | ✅ |
| `POST /api/v1/analyze-answer` | Analyze answers | ✅ |
| `GET /api/v1/services` | Service status | ✅ |
| `GET /health` | Health check | ✅ |
| `GET /monitoring/database` | DB monitoring | ✅ |

## 📊 **Monitoring**

### Health Check
```bash
curl http://localhost:8000/health | jq '.async_database'
```

### Database Monitoring
```bash
curl http://localhost:8000/monitoring/database | jq
```

### Connection Pool Status
```bash
curl http://localhost:8000/monitoring/database | jq '.connection_pool_status'
```

## 🔄 **Code Patterns**

### Async Service Usage
```python
# Async service
async with get_async_db() as db:
    service = AsyncQuestionBankService(db)
    questions = await service.get_questions_for_role("developer", "Python role")
```

### Sync Service Usage (Fallback)
```python
# Sync service
db = next(get_db())
service = QuestionBankService(db)
questions = service.get_questions_for_role("developer", "Python role")
```

### Dual Mode API Endpoint
```python
@router.post("/endpoint")
async def endpoint(request: Request):
    if settings.ASYNC_DATABASE_ENABLED:
        # Async path
        async with get_async_db() as db:
            service = await get_async_service(db)
            result = await service.operation()
    else:
        # Sync path
        db = next(get_db())
        service = get_sync_service(db)
        result = service.operation()
    
    return result
```

## 🚨 **Troubleshooting**

### Common Issues

| Issue | Solution |
|-------|----------|
| Connection pool exhausted | Increase `ASYNC_DATABASE_POOL_SIZE` |
| Slow response times | Check database indexes and query optimization |
| Async context errors | Ensure proper `async with` usage |
| Import errors | Check Python path and module imports |

### Debug Commands
```bash
# Test async infrastructure
python -c "from app.database.async_connection import AsyncDatabaseManager; print('✅ Async ready')"

# Test database connection
python -c "
import asyncio
from app.database.async_connection import get_async_db
async def test(): 
    async with get_async_db() as db: 
        result = await db.execute('SELECT 1')
        print('✅ DB connected')
asyncio.run(test())
"

# Check service availability
curl http://localhost:8000/api/v1/services
```

## 📈 **Performance Expectations**

| Metric | Sync Mode | Async Mode | Improvement |
|--------|-----------|------------|-------------|
| Concurrent Requests | 50-100 | 500-1000 | 5-10x |
| Response Time | 200-500ms | 50-150ms | 2-4x faster |
| Memory Usage | Higher | Lower | 20-30% reduction |
| CPU Usage | Higher | Lower | 15-25% reduction |

## 🔄 **Migration Steps**

1. **Deploy with async disabled** (`ASYNC_DATABASE_ENABLED=false`)
2. **Validate deployment** - Test all endpoints
3. **Enable async in staging** (`ASYNC_DATABASE_ENABLED=true`)
4. **Run performance tests** - Compare sync vs async
5. **Enable async in production** - Gradual rollout
6. **Monitor metrics** - Watch for issues
7. **Rollback if needed** - Set `ASYNC_DATABASE_ENABLED=false`

## 📞 **Support**

- **Documentation**: `docs/ASYNC_DATABASE_GUIDE.md`
- **Migration Guide**: `docs/ASYNC_MIGRATION_GUIDE.md`
- **Health Check**: `http://localhost:8000/health`
- **Monitoring**: `http://localhost:8000/monitoring/database`

## ⚡ **Quick Commands**

```bash
# Enable async mode
export ASYNC_DATABASE_ENABLED=true && docker-compose restart

# Check status
curl http://localhost:8000/health | jq '.async_database.status'

# Monitor in real-time
watch -n 1 'curl -s http://localhost:8000/monitoring/database | jq ".connection_pool_status"'

# Rollback to sync
export ASYNC_DATABASE_ENABLED=false && docker-compose restart
```
