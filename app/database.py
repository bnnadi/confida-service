from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from app.config import get_settings

settings = get_settings()

# Database URL configuration with PostgreSQL as default for development
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://interviewiq_dev:dev_password@localhost:5432/interviewiq_dev"
)

# Determine if we're using SQLite
is_sqlite = "sqlite" in DATABASE_URL.lower()

# Create engine with appropriate configuration
if is_sqlite:
    # SQLite configuration for testing only
    engine = create_engine(
        DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration for development and production
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()