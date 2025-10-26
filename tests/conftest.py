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
