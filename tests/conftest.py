"""
Test configuration and fixtures for InterviewIQ API tests.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from app.main import app
from app.dependencies import get_ai_service
from app.services.hybrid_ai_service import HybridAIService
from faker import Faker

fake = Faker()

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    class MockAIService:
        def __init__(self):
            self.service_type = "openai"
        
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
                "timestamp": "2024-01-15T10:30:00Z"
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
                "timestamp": "2024-01-15T10:30:00Z"
            }
        
        async def get_available_services(self):
            return {
                "available_services": ["openai", "anthropic", "ollama"],
                "service_priority": ["openai", "anthropic", "ollama"],
                "service_status": {
                    "openai": "available",
                    "anthropic": "available", 
                    "ollama": "unavailable"
                }
            }
    
    return MockAIService()

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
                "timestamp": "2024-01-15T10:30:00Z"
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
        "email": "test@example.com",
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
def mock_database_session():
    """Mock database session for testing."""
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.add.return_value = None
    mock_session.commit.return_value = None
    mock_session.rollback.return_value = None
    return mock_session

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "name": "Test User",
        "is_active": True,
        "created_at": "2024-01-15T10:30:00Z"
    }

@pytest.fixture
def sample_session_data():
    """Sample interview session data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "role": "Senior Python Developer",
        "job_description": "We are looking for a Senior Python Developer...",
        "status": "active",
        "total_questions": 5,
        "completed_questions": 0,
        "created_at": "2024-01-15T10:30:00Z"
    }

@pytest.fixture
def sample_question_data():
    """Sample question data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "session_id": "550e8400-e29b-41d4-a716-446655440001",
        "question_text": "Tell me about your experience with Python web frameworks.",
        "question_order": 1,
        "difficulty_level": "medium",
        "category": "technical"
    }

@pytest.fixture
def sample_answer_data():
    """Sample answer data for testing."""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "question_id": "550e8400-e29b-41d4-a716-446655440002",
        "answer_text": "I have 5 years of experience with Django and Flask frameworks.",
        "analysis_result": {
            "score": {"clarity": 8.5, "confidence": 7.8, "relevance": 9.0, "overall": 8.4},
            "missingKeywords": ["Django", "Flask"],
            "improvements": ["Provide more specific examples"]
        },
        "created_at": "2024-01-15T10:30:00Z"
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
            # Allow all requests for testing
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
    
    return MockRedisClient()

@pytest.fixture
def mock_metrics_collector():
    """Mock metrics collector for testing."""
    class MockMetricsCollector:
        def __init__(self):
            self.request_count = 0
            self.error_count = 0
            self.ai_service_requests = 0
        
        def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
            self.request_count += 1
        
        def record_error(self, error_type: str, endpoint: str):
            self.error_count += 1
        
        def record_ai_service_request(self, service: str, operation: str, status: str, duration: float):
            self.ai_service_requests += 1
    
    return MockMetricsCollector()

# Override dependencies for testing
@pytest.fixture(autouse=True)
def override_dependencies(mock_ai_service):
    """Override FastAPI dependencies for testing."""
    app.dependency_overrides[get_ai_service] = lambda: mock_ai_service
    yield
    app.dependency_overrides.clear()