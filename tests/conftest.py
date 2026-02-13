"""
Test configuration for Confida tests.

This module provides test fixtures and configuration for the testing infrastructure.
"""
import pytest
import os
import uuid
from pathlib import Path

# Disable rate limiting, monitoring, and async DB before importing the app
# (settings are cached on first access)
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["MONITORING_ENABLED"] = "false"
os.environ["ASYNC_DATABASE_ENABLED"] = "false"
os.environ["ASYNC_DATABASE_MONITORING_ENABLED"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.models import Base
from app.middleware.auth_middleware import get_current_user_required, get_current_admin
from app.dependencies import get_ai_client_dependency
from app.services.database_service import get_db

# Set up basic test environment
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up basic test environment.
    
    Uses setdefault so CI-provided values (e.g. PostgreSQL) are respected.
    Falls back to SQLite for local development.
    """
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_confida.db")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    os.environ.setdefault("ENVIRONMENT", "test")
    
    # Add project root to Python path
    project_root = Path(__file__).parent.parent
    os.environ["PYTHONPATH"] = str(project_root)
    
    yield
    
    # Cleanup SQLite file if used
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
    """Create test database engine using DATABASE_URL from environment."""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./test_confida.db")
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(db_url, connect_args=connect_args)
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture
def test_db_session(test_db_engine):
    """Create test database session with transaction rollback for isolation."""
    connection = test_db_engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    # Start a nested savepoint so session.commit() inside tests doesn't
    # actually commit the outer transaction
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture
def db_session(test_db_session):
    """Alias for test_db_session."""
    return test_db_session

# FastAPI client fixture - function-scoped with get_db override for consistency
@pytest.fixture
def client(db_session):
    """Create FastAPI test client with get_db overridden to use test db_session.
    
    Ensures the app sees fixture data (sample_user, etc.) in the same transaction.
    Integration and E2E conftests provide their own client; this is the default.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client_with_db(client):
    """Alias for client - both now use get_db override."""
    return client

# --- Auth dependency override helpers ---

@pytest.fixture
def override_auth(client):
    """Fixture to override auth dependency for tests.
    
    Usage:
        def test_something(self, client, override_auth, mock_current_user):
            override_auth(mock_current_user)
            response = client.get("/api/v1/...")
    
    Automatically clears the override after the test.
    """
    def _override(user_dict):
        client.app.dependency_overrides[get_current_user_required] = lambda: user_dict
    yield _override
    client.app.dependency_overrides.pop(get_current_user_required, None)


@pytest.fixture
def override_admin_auth(client):
    """Fixture to override get_current_admin dependency for admin-only endpoints.
    
    Usage:
        def test_something(self, client, override_admin_auth, admin_user):
            override_admin_auth({"id": str(admin_user.id), "email": admin_user.email, "is_admin": True, "role": "admin"})
            response = client.post("/api/v1/questions", json=...)
    
    Automatically clears the override after the test.
    """
    def _override(user_dict):
        client.app.dependency_overrides[get_current_admin] = lambda: user_dict
    yield _override
    client.app.dependency_overrides.pop(get_current_admin, None)


@pytest.fixture
def override_ai_client(client):
    """Fixture to override AI client dependency for tests.
    
    Usage:
        def test_something(self, client, override_ai_client, mock_ai_client):
            override_ai_client(mock_ai_client)
            response = client.post("/api/v1/parse-jd", json=...)
    
    Automatically clears the override after the test.
    """
    def _override(ai_client):
        client.app.dependency_overrides[get_ai_client_dependency] = lambda: ai_client
    yield _override
    client.app.dependency_overrides.pop(get_ai_client_dependency, None)


# Test fixtures for integration tests
@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    from app.database.models import User
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    user = User(
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
        password_hash=auth_service.get_password_hash("testpass123"),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_auth_user(sample_user, is_admin: bool = False) -> dict:
    """Helper to build auth dict for override_auth. Use when you need to customize per-test."""
    result = {
        "id": str(sample_user.id),
        "email": sample_user.email,
        "is_admin": is_admin,
    }
    if is_admin:
        result["role"] = "admin"
    return result


@pytest.fixture
def mock_current_user(sample_user):
    """Build auth dict from sample_user for override_auth. Use 'id' to match auth middleware."""
    return make_auth_user(sample_user, is_admin=False)


@pytest.fixture
def mock_admin_user(sample_user):
    """Admin variant for admin-only endpoints."""
    return make_auth_user(sample_user, is_admin=True)


@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing."""
    from unittest.mock import AsyncMock
    questions_data = [
        {"text": "What is Python?", "type": "technical"},
        {"text": "Explain decorators.", "type": "technical"},
        {"text": "What is your experience with Django?", "type": "experience"},
        {"text": "How do you handle database migrations?", "type": "technical"},
        {"text": "Describe your debugging process.", "type": "behavioral"}
    ]
    client = AsyncMock()
    client.generate_questions = AsyncMock(return_value=questions_data)
    client.generate_questions_structured = AsyncMock(return_value={
        "questions": questions_data,
        "embedding_vectors": {}
    })
    client.analyze_answer = AsyncMock(return_value={
        "score": {"clarity": 8, "confidence": 7, "relevance": 8, "overall": 8},
        "analysis": "Good answer",
        "suggestions": ["Could provide more detail"]
    })
    client.health_check = AsyncMock(return_value=True)
    client.base_url = "http://test-ai-service"
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
        "jobDescription": "Looking for a Python developer with 5+ years of experience.",
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
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    user = User(
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        name="Admin User",
        password_hash=auth_service.get_password_hash("adminpass123"),
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
    """Fixture for TTS service settings.
    
    Also mocks asyncio.sleep in the TTS service module to prevent
    real delays during retry backoff (which cause 10+ second waits
    and event-loop hangs under pytest-xdist).
    """
    from unittest.mock import patch, MagicMock, AsyncMock
    
    with patch("app.services.tts.service.get_settings") as mock_settings, \
         patch("app.services.tts.factory.get_settings", new=mock_settings), \
         patch("app.services.tts.service.asyncio.sleep", new_callable=AsyncMock):
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
