# Development Setup Guide

This guide explains the recommended development setup to avoid issues when moving from development to production.

## 🚨 **Why Not Use SQLite in Development?**

Using SQLite in development can cause several issues when moving to PostgreSQL in production:

### 1. **Data Type Mismatches**
- SQLite is dynamically typed and forgiving
- PostgreSQL is strictly typed and will reject invalid data
- Example: Invalid enum values work in SQLite but fail in PostgreSQL

### 2. **SQL Syntax Differences**
- SQLite has limited SQL features
- PostgreSQL has more advanced features and stricter syntax
- Example: Different handling of string operations and data types

### 3. **Constraint Enforcement**
- SQLite ignores some constraints by default
- PostgreSQL enforces all constraints strictly
- Example: Foreign key constraints behave differently

### 4. **Transaction Behavior**
- Different transaction isolation levels
- Different locking mechanisms
- Example: Concurrent access handling differs

## 🛠️ **Recommended Development Setup**

### Option 1: PostgreSQL in Development (Recommended)

This is the **best practice** to ensure production parity.

#### 1. Install PostgreSQL

```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

#### 2. Create Development Database

```bash
# Create development database
createdb interviewiq_dev

# Create user for development
psql -d interviewiq_dev -c "CREATE USER interviewiq_dev WITH PASSWORD 'dev_password';"
psql -d interviewiq_dev -c "GRANT ALL PRIVILEGES ON DATABASE interviewiq_dev TO interviewiq_dev;"
```

#### 3. Configure Environment

Create `.env` file:

```env
# Development Database
DATABASE_URL=postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev

# JWT Configuration
SECRET_KEY=dev-secret-key-not-for-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Service Configuration (optional for development)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

#### 4. Run Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### Option 2: Docker PostgreSQL (Alternative)

For easier setup and consistency across team members.

#### 1. Create Docker Compose File

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: interviewiq_dev
      POSTGRES_USER: interviewiq_dev
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U interviewiq_dev -d interviewiq_dev"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

#### 2. Start Database

```bash
docker-compose -f docker-compose.dev.yml up -d
```

#### 3. Configure Environment

```env
DATABASE_URL=postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev
```

## 🌱 **Demo Data & Seed Scripts**

### Seed Data for Local Development

The project includes a comprehensive seed data script that populates your development database with:

- **Demo Users**: Pre-configured test accounts with different roles
- **Sample Interview Sessions**: Complete interview scenarios for different job roles
- **Questions & Answers**: Realistic interview questions and sample responses
- **Performance Data**: User performance tracking and analytics
- **Agent Configurations**: AI agent setup for evaluation and analysis

#### Demo Users Created

| Email | Password | Role | Description |
|-------|----------|------|-------------|
| `demo@interviewiq.com` | `demo123456` | User | Main demo account |
| `john.doe@example.com` | `password123` | User | Sample user 1 |
| `jane.smith@example.com` | `password123` | User | Sample user 2 |
| `admin@interviewiq.com` | `admin123456` | Admin | Admin account |

#### Running Seed Data

```bash
# Run the seed data script
python seed_data.py

# Or use the convenience script
python run_seed.py
```

#### What Gets Created

- **4 Demo Users** with hashed passwords
- **4 Interview Sessions** for different job roles (Software Engineer, Data Scientist, Product Manager, DevOps Engineer)
- **20+ Interview Questions** with varying difficulty levels
- **Sample Answers** with AI analysis results and scoring
- **Performance Tracking Data** for analytics
- **Analytics Events** for user interaction tracking
- **Agent Configurations** for AI evaluation systems

#### Sample Interview Sessions

1. **Senior Software Engineer** - Technical questions about architecture, code quality, and cloud platforms
2. **Data Scientist** - ML model building, data preprocessing, and statistical analysis
3. **Product Manager** - Product strategy, user feedback, and cross-functional collaboration
4. **DevOps Engineer** - Infrastructure, security, monitoring, and deployment strategies

#### Resetting Demo Data

To reset the demo data:

```bash
# Drop and recreate database
dropdb interviewiq_dev
createdb interviewiq_dev
psql -d interviewiq_dev -c "CREATE USER interviewiq_dev WITH PASSWORD 'dev_password';"
psql -d interviewiq_dev -c "GRANT ALL PRIVILEGES ON DATABASE interviewiq_dev TO interviewiq_dev;"

# Run migrations
alembic upgrade head

# Seed with demo data
python seed_data.py
```

## 🧪 **Testing Strategy**

### Unit Tests with SQLite

For fast unit tests, you can still use SQLite:

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.connection import Base
from app.models.user import User

@pytest.fixture
def test_db():
    # Use SQLite for fast unit tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()
```

### Integration Tests with PostgreSQL

For integration tests, use the same PostgreSQL setup as development:

```python
# tests/integration/conftest.py
import pytest
from app.database.connection import get_db
from app.models.user import User

@pytest.fixture
def integration_db():
    # Use PostgreSQL for integration tests
    db = next(get_db())
    yield db
    db.close()
```

## 🔄 **Database Migration Strategy**

### 1. Always Use Alembic

```bash
# Create migration
alembic revision --autogenerate -m "Add user profile fields"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### 2. Test Migrations

```bash
# Test migration on development database
alembic upgrade head

# Test rollback
alembic downgrade -1
alembic upgrade head
```

### 3. Production Deployment

```bash
# Production migration
alembic upgrade head
```

## 🚀 **Quick Start Commands**

### Development Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL
brew services start postgresql  # macOS
# or
sudo systemctl start postgresql  # Linux

# 3. Create development database
createdb interviewiq_dev
psql -d interviewiq_dev -c "CREATE USER interviewiq_dev WITH PASSWORD 'dev_password';"
psql -d interviewiq_dev -c "GRANT ALL PRIVILEGES ON DATABASE interviewiq_dev TO interviewiq_dev;"

# 4. Configure environment
cp env.example .env
# Edit .env with development database URL

# 5. Run migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# 6. Seed database with demo data (optional)
python seed_data.py

# 7. Start development server
uvicorn app.main:app --reload
```

### Testing Setup

```bash
# Run unit tests (with SQLite)
pytest tests/unit/

# Run integration tests (with PostgreSQL)
pytest tests/integration/

# Run all tests
pytest
```

## 📋 **Environment Configuration**

### Development (.env)

```env
# Database
DATABASE_URL=postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev

# JWT
SECRET_KEY=dev-secret-key-not-for-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services (optional)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Testing (.env.test)

```env
# Database
DATABASE_URL=sqlite:///./test_interviewiq.db

# JWT
SECRET_KEY=test-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=5
```

### Production (.env.prod)

```env
# Database
DATABASE_URL=postgresql://interviewiq:secure_password@prod-db-host:5432/interviewiq_prod

# JWT
SECRET_KEY=super-secure-production-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Services
OPENAI_API_KEY=prod-openai-api-key
ANTHROPIC_API_KEY=prod-anthropic-api-key
```

## ✅ **Best Practices**

1. **Always use PostgreSQL in development** to match production
2. **Use SQLite only for fast unit tests** that don't test database-specific features
3. **Test migrations thoroughly** before deploying to production
4. **Use environment-specific configurations** for different deployment stages
5. **Document database changes** in migration messages
6. **Backup production data** before running migrations
7. **Test rollback procedures** regularly

## 🚨 **Common Pitfalls to Avoid**

1. **Don't use SQLite in development** if you plan to use PostgreSQL in production
2. **Don't ignore migration testing** - always test on a copy of production data
3. **Don't hardcode database URLs** - always use environment variables
4. **Don't skip constraint validation** - PostgreSQL will catch issues SQLite misses
5. **Don't assume SQLite behavior** - test with PostgreSQL early and often

## 📚 **Additional Resources**

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [FastAPI Database Documentation](https://fastapi.tiangolo.com/tutorial/sql-databases/)
