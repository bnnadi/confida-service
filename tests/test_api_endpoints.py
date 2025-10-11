"""
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_detailed(client):
    """Test the health check endpoint with detailed response."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    
    # Check service status
    services = data["services"]
    assert "database" in services
    assert "redis" in services
    assert "ollama" in services
    assert "openai" in services
    assert "anthropic" in services


def test_ready_endpoint_detailed(client):
    """Test the readiness check endpoint with detailed response."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "ready" in data
    assert "database" in data
    assert "timestamp" in data
    
    # Check types
    assert isinstance(data["ready"], bool)
    assert isinstance(data["database"], str)


def test_sessions_endpoints_require_auth(client):
    """Test that session endpoints require authentication (return 422 for missing user_id)."""
    # Test create session endpoint
    response = client.post("/api/v1/sessions/", json={
        "role": "Software Engineer",
        "job_description": "Test job"
    })
    # Should return 422 for missing user_id query parameter
    assert response.status_code == 422


def test_interview_endpoints_require_auth(client):
    """Test that interview endpoints require authentication (return 422 for missing user_id)."""
    # Test parse JD endpoint
    response = client.post("/api/v1/parse-jd", json={
        "role": "Software Engineer",
        "jobDescription": "Test job description"
    })
    # Should return 422 for missing user_id query parameter
    assert response.status_code == 422


def test_admin_endpoints_exist(client):
    """Test that admin endpoints are accessible."""
    # Test admin health endpoint
    response = client.get("/admin/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data


def test_api_documentation_accessible(client):
    """Test that API documentation is accessible."""
    # Test OpenAPI JSON
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data
    
    # Test ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200
