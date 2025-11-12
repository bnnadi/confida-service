"""
Test configuration for Confida tests.

This module provides test fixtures and configuration for the testing infrastructure.
"""
import pytest
import os
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app

# Replace JSONB with JSON for SQLite compatibility
# This must happen before importing models
import sqlalchemy.dialects.sqlite.base
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# Patch JSONB class to handle SQLite
if JSONB is not None and not hasattr(JSONB, '_patched_for_sqlite'):
    original_impl = JSONB.load_dialect_impl
    
    def _patched_load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(JSON())
        return original_impl(self, dialect)
    
    JSONB.load_dialect_impl = _patched_load_dialect_impl
    JSONB._patched_for_sqlite = True

# Patch SQLite compiler to handle JSONB
if not hasattr(sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler, '_patched_for_jsonb'):
    def visit_JSONB(self, type_, **kw):
        return self.visit_JSON(type_, **kw)
    
    sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler.visit_JSONB = visit_JSONB
    sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler._patched_for_jsonb = True

from app.database.models import Base

# Set up basic test environment
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up basic test environment."""
    # Set environment variables
    os.environ["DATABASE_URL"] = "sqlite:///./test_confida.db"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["ENVIRONMENT"] = "test"
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    os.environ["PYTHONPATH"] = str(project_root)
    
    yield
    
    # Cleanup
    test_db_path = Path("test_confida.db")
    if test_db_path.exists():
        test_db_path.unlink()

@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "age": 30
    }

@pytest.fixture
def mock_service():
    """Mock service for testing."""
    class MockService:
        def __init__(self):
            self.calls = []
        
        def method(self, value):
            self.calls.append(value)
            return f"processed_{value}"
    
    return MockService()

# Database fixtures
@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///./test_confida.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def test_db_session(test_db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def db_session(test_db_session):
    """Alias for test_db_session."""
    return test_db_session

# FastAPI client fixture
@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)

# Test fixtures for integration tests
@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    from app.database.models import User
    from werkzeug.security import generate_password_hash
    user = User(
        email="test@example.com",
        name="Test User",
        password_hash=generate_password_hash("testpass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing."""
    from unittest.mock import AsyncMock
    client = AsyncMock()
    client.generate_questions = AsyncMock(return_value=[
        {"text": "What is Python?", "type": "technical"},
        {"text": "Explain decorators.", "type": "technical"},
        {"text": "What is your experience with Django?", "type": "experience"},
        {"text": "How do you handle database migrations?", "type": "technical"},
        {"text": "Describe your debugging process.", "type": "behavioral"}
    ])
    client.analyze_answer = AsyncMock(return_value={
        "score": 0.85,
        "feedback": "Good answer",
        "strengths": ["Clear explanation"],
        "improvements": ["Could provide more detail"]
    })
    return client

@pytest.fixture
def sample_parse_request():
    """Sample request data for parsing job description."""
    return {
        "role": "Python Developer",
        "jobDescription": "We are looking for a Python developer with 5+ years of experience in Django and Flask. Strong debugging skills required.",
        "service": "openai"
    }

@pytest.fixture
def sample_analyze_request():
    """Sample request data for analyzing answer."""
    return {
        "question": "What is Python?",
        "answer": "Python is a high-level programming language known for its simplicity and readability.",
        "service": "openai"
    }

@pytest.fixture
def sample_interview_session(db_session, sample_user):
    """Create a sample interview session."""
    from app.database.models import InterviewSession
    session = InterviewSession(
        user_id=sample_user.id,
        role="Python Developer",
        job_description="Test job description",
        status="active",
        total_questions=5,
        completed_questions=0
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session

@pytest.fixture
def sample_question(db_session):
    """Create a sample question."""
    from app.database.models import Question
    import json
    question = Question(
        question_text="What is Python?",
        question_metadata={"source": "test"},
        difficulty_level="easy",
        category="python",
        subcategory="basics",
        compatible_roles=["python_developer"],
        required_skills=["python"],
        industry_tags=["tech"]
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    return question

@pytest.fixture
def sample_session_question(db_session, sample_interview_session, sample_question):
    """Create a sample session question."""
    from app.database.models import SessionQuestion
    session_question = SessionQuestion(
        session_id=sample_interview_session.id,
        question_id=sample_question.id,
        question_order=1,
        session_specific_context={"context": "test"}
    )
    db_session.add(session_question)
    db_session.commit()
    db_session.refresh(session_question)
    return session_question

@pytest.fixture
def mock_question_bank_service():
    """Mock question bank service for testing."""
    from unittest.mock import Mock
    service = Mock()
    service.get_questions_for_role = Mock(return_value=[
        {"text": "Question 1", "type": "technical"},
        {"text": "Question 2", "type": "behavioral"}
    ])
    return service

@pytest.fixture
def generate_test_sessions():
    """Fixture to generate test sessions."""
    def _generate(count=5):
        sessions = []
        for i in range(count):
            sessions.append({
                "id": f"session-{i}",
                "user_id": f"user-{i}",
                "role": f"Developer {i}",
                "status": "active",
                "total_questions": 10,
                "completed_questions": i
            })
        return sessions
    return _generate
