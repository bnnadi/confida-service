"""
Comprehensive test configuration and fixtures for Confida API tests.

This module provides all necessary fixtures, mocks, and test utilities
for unit, integration, and end-to-end testing.
"""
import pytest
import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.dependencies import get_ai_service, get_db
from app.database.connection import Base, get_db as get_db_connection
from app.database.models import User, InterviewSession, Question, SessionQuestion, Answer
from app.services.hybrid_ai_service import HybridAIService
from app.services.question_service import QuestionService
from app.config import get_settings
from faker import Faker

# Initialize Faker for generating test data
fake = Faker()

# Test database configuration
TEST_DATABASE_URL = "sqlite:///./test_confida.db"


class TestDataFactory:
    """Factory for creating test data with consistent patterns."""
    
    @staticmethod
    def create_mock_ai_service(service_type: str = "openai"):
        """Create mock AI service with consistent interface."""
        class MockAIService:
            def __init__(self, service_type: str):
                self.service_type = service_type
                self.question_bank_service = None
            
            async def generate_interview_questions(self, role: str, job_description: str, **kwargs):
                return TestDataFactory.get_sample_questions_response()
            
            async def analyze_answer(self, job_description: str, question: str, answer: str, **kwargs):
                return TestDataFactory.get_sample_analysis_response()
        
        return MockAIService(service_type)
    
    @staticmethod
    def get_sample_questions_response():
        """Get consistent sample questions response."""
        return {
            "questions": [
                "What is your experience with Python?",
                "How do you handle debugging complex issues?",
                "Describe a challenging project you worked on."
            ],
            "role": "Software Engineer",
            "jobDescription": "Test job description"
        }
    
    @staticmethod
    def get_sample_analysis_response():
        """Get consistent sample analysis response."""
        return {
            "analysis": "Good answer with room for improvement",
            "score": {"clarity": 7, "confidence": 6},
            "suggestions": ["Provide more specific examples", "Include metrics"]
        }

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

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
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    session = test_db_session_factory()
    
    yield session
    
    # Clean up
    session.close()
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client(test_db_session):
    """Create test client with database session override."""
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def mock_ai_service():
    """Comprehensive mock AI service for testing.
    
    Note: This could be simplified using TestDataFactory.create_mock_ai_service()
    for basic testing scenarios, but this comprehensive version is kept for
    complex integration tests that need detailed mock responses.
    """
    class MockAIService:
        def __init__(self):
            self.service_type = "openai"
            self.question_bank_service = None
        
        async def generate_interview_questions(self, role: str, job_description: str, preferred_service: str = None):
            return {
                "questions": [
                    "Tell me about yourself and your experience with Python",
                    "What is your experience with Django and Flask frameworks?",
                    "How do you approach debugging complex issues?",
                    "Can you explain the difference between synchronous and asynchronous programming?",
                    "What's your experience with database optimization in Python applications?"
                ],
                "service_used": "openai",
                "timestamp": datetime.utcnow().isoformat(),
                "question_bank_used": True,
                "questions_from_bank": 3,
                "questions_generated": 2
            }
        
        async def analyze_answer(self, job_description: str, question: str, answer: str, preferred_service: str = None):
            return {
                "score": {
                    "clarity": 8.5,
                    "confidence": 7.8,
                    "relevance": 9.0,
                    "overall": 8.4
                },
                "missingKeywords": ["Django", "Flask", "debugging"],
                "improvements": [
                    "Provide more specific examples of your Python experience",
                    "Mention specific frameworks you've worked with",
                    "Include details about your debugging process"
                ],
                "idealAnswer": "I have 5 years of Python experience working primarily with Django and Flask frameworks. For debugging, I use a systematic approach starting with log analysis, then interactive debugging with pdb, and finally performance profiling when needed.",
                "service_used": "openai",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        async def get_available_services(self):
            return {
                "available_services": ["openai", "anthropic", "ollama"],
                "service_priority": ["openai", "anthropic", "ollama"],
                "service_status": {
                    "openai": "available",
                    "anthropic": "available", 
                    "ollama": "unavailable"
                },
                "question_bank_stats": {
                    "total_questions": 150,
                    "questions_by_category": {"technical": 80, "behavioral": 50, "system_design": 20},
                    "questions_by_difficulty": {"easy": 30, "medium": 80, "hard": 40}
                }
            }
        
        async def list_models(self, service: str = None):
            return {
                "models": {
                    "openai": ["gpt-4", "gpt-3.5-turbo"],
                    "anthropic": ["claude-3-sonnet", "claude-3-haiku"],
                    "ollama": ["llama2", "codellama"]
                },
                "default_models": {
                    "openai": "gpt-3.5-turbo",
                    "anthropic": "claude-3-haiku",
                    "ollama": "llama2"
                }
            }
    
    return MockAIService()

@pytest.fixture
def mock_question_bank_service():
    """Mock question bank service for testing."""
    class MockQuestionBankService:
        def __init__(self):
            self.questions = []
        
        def get_questions_for_role(self, role: str, job_description: str, count: int = 10):
            return [
                Mock(
                    id=str(uuid.uuid4()),
                    question_text="Tell me about your Python experience",
                    category="technical",
                    difficulty_level="medium",
                    usage_count=5,
                    average_score=8.5
                ),
                Mock(
                    id=str(uuid.uuid4()),
                    question_text="How do you handle debugging?",
                    category="technical",
                    difficulty_level="easy",
                    usage_count=3,
                    average_score=7.8
                )
            ]
        
        def store_generated_questions(self, questions: List[str], role: str, job_description: str, ai_service_used: str, prompt_hash: str):
            for q_text in questions:
                self.questions.append({
                    "question_text": q_text,
                    "role": role,
                    "ai_service_used": ai_service_used
                })
        
        def get_question_bank_stats(self):
            return {
                "total_questions": len(self.questions),
                "questions_by_category": {"technical": 10, "behavioral": 5},
                "questions_by_difficulty": {"easy": 5, "medium": 8, "hard": 2},
                "last_updated": datetime.utcnow().isoformat()
            }
    
    return MockQuestionBankService()

@pytest.fixture
def mock_speech_service():
    """Mock speech service for testing."""
    class MockSpeechService:
        async def transcribe_audio(self, audio_data: bytes, language: str = "en-US"):
            return {
                "transcript": "This is a test transcription of the audio content.",
                "confidence": 0.95,
                "language": language,
                "duration": 5.2,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        async def get_supported_languages(self):
            return {
                "languages": [
                    {"code": "en-US", "name": "English (US)"},
                    {"code": "en-GB", "name": "English (UK)"},
                    {"code": "es-ES", "name": "Spanish (Spain)"},
                    {"code": "fr-FR", "name": "French (France)"}
                ]
            }
    
    return MockSpeechService()

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "email": fake.email(),
        "name": fake.name(),
        "password_hash": "hashed_password_123",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

@pytest.fixture
def sample_user(test_db_session, sample_user_data):
    """Create a sample user in the test database."""
    user = User(**sample_user_data)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user

@pytest.fixture
def sample_session_data(sample_user):
    """Sample interview session data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "user_id": sample_user.id,
        "role": "Senior Python Developer",
        "job_description": "We are looking for a Senior Python Developer with 5+ years of experience in Django, Flask, and API development.",
        "status": "active",
        "total_questions": 5,
        "completed_questions": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

@pytest.fixture
def sample_interview_session(test_db_session, sample_session_data):
    """Create a sample interview session in the test database."""
    session = InterviewSession(**sample_session_data)
    test_db_session.add(session)
    test_db_session.commit()
    test_db_session.refresh(session)
    return session

@pytest.fixture
def sample_question_data():
    """Sample question data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "question_text": "Tell me about your experience with Python web frameworks.",
        "question_metadata": {"role": "python_developer", "context": "web_development"},
        "difficulty_level": "medium",
        "category": "technical",
        "subcategory": "web_frameworks",
        "compatible_roles": ["python_developer", "backend_developer"],
        "required_skills": ["python", "django", "flask"],
        "industry_tags": ["technology", "web_development"],
        "usage_count": 5,
        "average_score": 8.5,
        "success_rate": 0.85,
        "ai_service_used": "openai",
        "generation_prompt_hash": "hash_123",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

@pytest.fixture
def sample_question(test_db_session, sample_question_data):
    """Create a sample question in the test database."""
    question = Question(**sample_question_data)
    test_db_session.add(question)
    test_db_session.commit()
    test_db_session.refresh(question)
    return question

@pytest.fixture
def sample_session_question_data(sample_interview_session, sample_question):
    """Sample session question data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "session_id": sample_interview_session.id,
        "question_id": sample_question.id,
        "question_order": 1,
        "session_specific_context": {"role": "senior_developer", "focus": "technical_skills"},
        "created_at": datetime.utcnow()
    }

@pytest.fixture
def sample_session_question(test_db_session, sample_session_question_data):
    """Create a sample session question in the test database."""
    session_question = SessionQuestion(**sample_session_question_data)
    test_db_session.add(session_question)
    test_db_session.commit()
    test_db_session.refresh(session_question)
    return session_question

@pytest.fixture
def sample_answer_data(sample_question):
    """Sample answer data for testing."""
    return {
        "id": str(uuid.uuid4()),
        "question_id": sample_question.id,
        "answer_text": "I have 5 years of experience with Django and Flask frameworks. I've built several REST APIs and have experience with database optimization.",
        "analysis_result": {
            "score": {"clarity": 8.5, "confidence": 7.8, "relevance": 9.0, "overall": 8.4},
            "missingKeywords": ["Django", "Flask"],
            "improvements": ["Provide more specific examples"],
            "idealAnswer": "I have extensive experience with Python web frameworks..."
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

@pytest.fixture
def sample_answer(test_db_session, sample_answer_data):
    """Create a sample answer in the test database."""
    answer = Answer(**sample_answer_data)
    test_db_session.add(answer)
    test_db_session.commit()
    test_db_session.refresh(answer)
    return answer

@pytest.fixture
def sample_parse_request():
    """Sample parse request data."""
    return {
        "role": "Senior Python Developer",
        "jobDescription": "We are looking for a Senior Python Developer with 5+ years of experience in Django, Flask, and API development. The ideal candidate should have strong debugging skills and experience with database optimization."
    }

@pytest.fixture
def sample_analyze_request():
    """Sample analyze request data."""
    return {
        "jobDescription": "We are looking for a Senior Python Developer with 5+ years of experience in Django, Flask, and API development.",
        "question": "What is your experience with Python web frameworks?",
        "answer": "I have been working with Python for 5 years, primarily in web development using Django and Flask frameworks. I've built several REST APIs and have experience with database optimization."
    }

@pytest.fixture
def sample_auth_request():
    """Sample authentication request data."""
    return {
        "email": fake.email(),
        "password": "testpassword123"
    }

@pytest.fixture
def sample_file_upload():
    """Sample file upload data."""
    return {
        "file": ("test_audio.wav", b"fake audio data", "audio/wav"),
        "file_type": "audio",
        "language": "en-US"
    }

@pytest.fixture
def mock_jwt_token():
    """Mock JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaWF0IjoxNzA1MzI0NjAwfQ.test_signature"

@pytest.fixture
def auth_headers(mock_jwt_token):
    """Authentication headers for testing."""
    return {"Authorization": f"Bearer {mock_jwt_token}"}

@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    class MockRateLimiter:
        def __init__(self):
            self.requests = {}
        
        def check_rate_limit(self, client_id: str):
            return True
        
        def get_rate_limit_status(self, client_id: str, user_type: str = "free"):
            return {
                "endpoint_remaining": 100,
                "user_remaining": 1000,
                "window_reset": 3600
            }
    
    return MockRateLimiter()

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    class MockRedisClient:
        def __init__(self):
            self.data = {}
        
        def get(self, key: str):
            return self.data.get(key)
        
        def set(self, key: str, value: str, ex: int = None):
            self.data[key] = value
            return True
        
        def setex(self, key: str, time: int, value: str):
            self.data[key] = value
            return True
        
        def delete(self, key: str):
            if key in self.data:
                del self.data[key]
                return 1
            return 0
        
        def exists(self, key: str):
            return key in self.data
        
        def expire(self, key: str, time: int):
            return key in self.data
    
    return MockRedisClient()

@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector for testing."""
    class MockMetricsCollector:
        def __init__(self):
            self.request_count = 0
            self.error_count = 0
            self.ai_service_requests = 0
            self.metrics = {}
        
        def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
            self.request_count += 1
            self.metrics[f"{method}_{endpoint}"] = {
                "count": self.metrics.get(f"{method}_{endpoint}", {}).get("count", 0) + 1,
                "total_duration": self.metrics.get(f"{method}_{endpoint}", {}).get("total_duration", 0) + duration
            }
        
        def record_error(self, error_type: str, endpoint: str):
            self.error_count += 1
        
        def record_ai_service_request(self, service: str, operation: str, status: str, duration: float):
            self.ai_service_requests += 1
        
        def get_metrics(self):
            return {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "ai_service_requests": self.ai_service_requests,
                "detailed_metrics": self.metrics
            }
    
    return MockMetricsCollector()

@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    class MockLogger:
        def __init__(self):
            self.logs = []
        
        def info(self, message: str):
            self.logs.append(("INFO", message))
        
        def warning(self, message: str):
            self.logs.append(("WARNING", message))
        
        def error(self, message: str):
            self.logs.append(("ERROR", message))
        
        def debug(self, message: str):
            self.logs.append(("DEBUG", message))
        
        def get_logs(self):
            return self.logs
    
    return MockLogger()

@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_file_system(temp_directory):
    """Mock file system operations."""
    class MockFileSystem:
        def __init__(self, base_path: str):
            self.base_path = Path(base_path)
            self.files = {}
        
        def write_file(self, path: str, content: str):
            full_path = self.base_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            self.files[path] = content
        
        def read_file(self, path: str):
            return self.files.get(path, "")
        
        def file_exists(self, path: str):
            return path in self.files
        
        def delete_file(self, path: str):
            if path in self.files:
                del self.files[path]
    
    return MockFileSystem(temp_directory)

# Override dependencies for testing
@pytest.fixture(autouse=True)
def override_dependencies(mock_ai_service):
    """Override FastAPI dependencies for testing."""
    app.dependency_overrides[get_ai_service] = lambda: mock_ai_service
    yield
    app.dependency_overrides.clear()

# Test data generators
@pytest.fixture
def generate_test_users(test_db_session, count: int = 5):
    """Generate multiple test users."""
    users = []
    for _ in range(count):
        user_data = {
            "id": str(uuid.uuid4()),
            "email": fake.email(),
            "name": fake.name(),
            "password_hash": "hashed_password_123",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        user = User(**user_data)
        test_db_session.add(user)
        users.append(user)
    
    test_db_session.commit()
    for user in users:
        test_db_session.refresh(user)
    
    return users

@pytest.fixture
def generate_test_sessions(test_db_session, sample_user, count: int = 3):
    """Generate multiple test interview sessions."""
    sessions = []
    for i in range(count):
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": sample_user.id,
            "role": f"Developer {i+1}",
            "job_description": f"Job description for role {i+1}",
            "status": "active",
            "total_questions": 5,
            "completed_questions": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        session = InterviewSession(**session_data)
        test_db_session.add(session)
        sessions.append(session)
    
    test_db_session.commit()
    for session in sessions:
        test_db_session.refresh(session)
    
    return sessions

# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.get_duration()
        
        def get_duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return PerformanceTimer()

# Async test fixtures
@pytest.fixture
async def async_client():
    """Async test client for testing async endpoints."""
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# Database transaction fixtures
@pytest.fixture
def db_transaction(test_db_session):
    """Database transaction fixture for testing rollbacks."""
    transaction = test_db_session.begin()
    yield test_db_session
    transaction.rollback()

# Mock external services
@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service."""
    class MockOpenAIService:
        async def generate_questions(self, role: str, job_description: str):
            return ["Question 1", "Question 2", "Question 3"]
        
        async def analyze_answer(self, question: str, answer: str):
            return {"score": 8.5, "feedback": "Good answer"}
    
    return MockOpenAIService()

@pytest.fixture
def mock_anthropic_service():
    """Mock Anthropic service."""
    class MockAnthropicService:
        async def generate_questions(self, role: str, job_description: str):
            return ["Question 1", "Question 2", "Question 3"]
        
        async def analyze_answer(self, question: str, answer: str):
            return {"score": 8.5, "feedback": "Good answer"}
    
    return MockAnthropicService()

@pytest.fixture
def mock_ollama_service():
    """Mock Ollama service."""
    class MockOllamaService:
        async def generate_questions(self, role: str, job_description: str):
            return ["Question 1", "Question 2", "Question 3"]
        
        async def analyze_answer(self, question: str, answer: str):
            return {"score": 8.5, "feedback": "Good answer"}
    
    return MockOllamaService()

# Test utilities
@pytest.fixture
def assert_response_structure():
    """Utility for asserting response structure."""
    def _assert_response_structure(response_data: Dict[str, Any], expected_fields: List[str]):
        for field in expected_fields:
            assert field in response_data, f"Missing field: {field}"
    
    return _assert_response_structure

@pytest.fixture
def assert_error_response():
    """Utility for asserting error responses."""
    def _assert_error_response(response, expected_status: int, expected_message: str = None):
        assert response.status_code == expected_status
        if expected_message:
            response_data = response.json()
            assert expected_message in response_data.get("detail", "")
    
    return _assert_error_response