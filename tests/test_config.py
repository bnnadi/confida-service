"""
Test configuration for InterviewIQ tests.

This module provides test-specific database models that work with SQLite
for testing purposes.
"""
import pytest
import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Test-specific base for SQLite compatibility
TestBase = declarative_base()

# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test_interviewiq.db"

class TestUser(TestBase):
    """Test user model compatible with SQLite."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TestInterviewSession(TestBase):
    """Test interview session model compatible with SQLite."""
    __tablename__ = "interview_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String, default="active")
    total_questions = Column(Integer, default=0)
    completed_questions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TestQuestion(TestBase):
    """Test question model compatible with SQLite."""
    __tablename__ = "questions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_text = Column(Text, nullable=False)
    question_metadata = Column(JSON)
    difficulty_level = Column(String)
    category = Column(String, nullable=False)
    subcategory = Column(String)
    compatible_roles = Column(JSON)
    required_skills = Column(JSON)
    industry_tags = Column(JSON)
    usage_count = Column(Integer, default=0)
    average_score = Column(Integer)
    success_rate = Column(Integer)
    ai_service_used = Column(String)
    generation_prompt_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TestSessionQuestion(TestBase):
    """Test session question model compatible with SQLite."""
    __tablename__ = "session_questions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    question_id = Column(String, nullable=False)
    question_order = Column(Integer, nullable=False)
    session_specific_context = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class TestAnswer(TestBase):
    """Test answer model compatible with SQLite."""
    __tablename__ = "answers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = Column(String, nullable=False)
    answer_text = Column(Text, nullable=False)
    analysis_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine

@pytest.fixture(scope="session")
def test_db_session_factory(test_engine):
    """Create test database session factory."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    return TestingSessionLocal

@pytest.fixture(scope="function")
def test_db_session(test_engine, test_db_session_factory):
    """Create a fresh database session for each test."""
    # Create all tables
    TestBase.metadata.create_all(bind=test_engine)
    
    # Create session
    session = test_db_session_factory()
    
    yield session
    
    # Clean up
    session.close()
    TestBase.metadata.drop_all(bind=test_engine)
