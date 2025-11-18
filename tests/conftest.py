"""
Test configuration for Confida tests.

This module provides test fixtures and configuration for the testing infrastructure.
"""
# Set test environment variables BEFORE any imports that might use them
import os
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")  # Disable rate limiting in tests
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_confida.db")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app

# Replace JSONB with JSON for SQLite compatibility
# This must happen before importing models
import sqlalchemy.dialects.sqlite.base
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

# Patch JSONB class to handle SQLite
if (
    JSONB is not None
    and hasattr(JSONB, 'load_dialect_impl')
    and not hasattr(JSONB, '_patched_for_sqlite')
):
    original_impl = JSONB.load_dialect_impl
    
    def _patched_load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(JSON())
        return original_impl(self, dialect)
    
    JSONB.load_dialect_impl = _patched_load_dialect_impl
    JSONB._patched_for_sqlite = True

# Patch UUID class to handle SQLite
if (
    UUID is not None
    and hasattr(UUID, 'load_dialect_impl')
    and not hasattr(UUID, '_patched_for_sqlite')
):
    original_uuid_impl = UUID.load_dialect_impl

    def _patched_uuid_load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(String(36))
        return original_uuid_impl(self, dialect)

    UUID.load_dialect_impl = _patched_uuid_load_dialect_impl
    UUID._patched_for_sqlite = True

# Patch SQLite compiler to handle JSONB
sqlite_type_compiler = sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler

if not hasattr(sqlite_type_compiler, '_patched_for_jsonb'):
    def visit_JSONB(self, type_, **kw):
        return self.visit_JSON(type_, **kw)

    sqlite_type_compiler.visit_JSONB = visit_JSONB
    sqlite_type_compiler._patched_for_jsonb = True

if not hasattr(sqlite_type_compiler, '_patched_for_uuid'):
    def visit_UUID(self, type_, **kw):
        return "CHAR(36)"

    sqlite_type_compiler.visit_UUID = visit_UUID
    sqlite_type_compiler._patched_for_uuid = True

from app.database.models import Base

# Set up basic test environment
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up basic test environment."""
    # Set additional environment variables (some are set at module level)
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    
    # Clear settings cache to ensure new environment variables are picked up
    from app.config import get_settings
    get_settings.cache_clear()
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    os.environ.setdefault("PYTHONPATH", str(project_root))
    
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
    from app.database.models import Base, User, InterviewSession, Question, SessionQuestion, Answer
    # Clean database before each test
    Base.metadata.drop_all(bind=test_db_engine)
    Base.metadata.create_all(bind=test_db_engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    try:
        yield session
        # Clean up after test
        session.rollback()
    finally:
        session.close()

@pytest.fixture
def db_session(test_db_session):
    """Alias for test_db_session."""
    return test_db_session

# FastAPI client fixture
@pytest.fixture
def client(db_session):
    """Create FastAPI test client with database dependency override."""
    from app.services.database_service import get_db
    client = TestClient(app)
    # Override get_db to use test database session
    client.app.dependency_overrides[get_db] = lambda: db_session
    yield client
    # Clean up overrides after test
    client.app.dependency_overrides.clear()

# Test fixtures for integration tests
@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    from app.database.models import User
    from werkzeug.security import generate_password_hash
    existing = db_session.query(User).filter(User.email == "test@example.com").first()
    if existing:
        return existing
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

@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    from app.database.models import User
    from werkzeug.security import generate_password_hash
    user = User(
        email="admin@example.com",
        name="Admin User",
        password_hash=generate_password_hash("adminpass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_user_token(db_session, admin_user):
    """Create an admin user token for testing."""
    from app.services.auth_service import AuthService
    
    auth_service = AuthService(db_session)
    # Create token directly
    token = auth_service.create_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        role="admin"
    )
    return token

# TTS Test Fixtures
@pytest.fixture
def mock_tts_settings():
    """Fixture for TTS service settings."""
    from unittest.mock import patch, MagicMock
    
    with patch("app.services.tts.service.get_settings") as mock_settings:
        settings = MagicMock()
        settings.TTS_PROVIDER = "coqui"
        settings.TTS_FALLBACK_PROVIDER = ""
        settings.TTS_RETRY_ATTEMPTS = 3
        settings.TTS_DEFAULT_VOICE_ID = "test-voice"
        settings.TTS_DEFAULT_FORMAT = "mp3"
        settings.CACHE_ENABLED = False
        settings.TTS_CACHE_TTL = 604800
        settings.TTS_TIMEOUT = 30
        settings.TTS_VOICE_VERSION = 1
        settings.ELEVENLABS_API_KEY = ""
        settings.PLAYHT_API_KEY = ""
        settings.PLAYHT_USER_ID = ""
        mock_settings.return_value = settings
        yield settings

@pytest.fixture
def tts_service_with_providers(mock_tts_settings):
    """Fixture that creates TTSService with mocked providers."""
    from unittest.mock import patch
    from app.services.tts.service import TTSService, CircuitBreaker
    
    def _create(primary_provider, fallback_provider=None, primary_name="coqui", fallback_name="elevenlabs"):
        with patch("app.services.tts.service.TTSProviderFactory.create_provider") as mock_factory:
            def create_provider_side_effect(provider_name):
                if provider_name == primary_name:
                    return primary_provider
                elif fallback_provider and provider_name == fallback_name:
                    return fallback_provider
                raise ValueError(f"Unknown provider: {provider_name}")
            
            mock_factory.side_effect = create_provider_side_effect
            
            service = TTSService()
            service.primary_provider = primary_provider
            service.primary_provider_name = primary_name
            service.circuit_breakers[primary_name] = CircuitBreaker()
            
            if fallback_provider:
                service.fallback_provider = fallback_provider
                service.fallback_provider_name = fallback_name
                service.circuit_breakers[fallback_name] = CircuitBreaker()
            
            return service
    
    return _create
