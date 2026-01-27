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
    
    # Check service status - database and redis should always be present
    services = data["services"]
    assert "database" in services
    assert "redis" in services
    # AI services are only present if configured, so we don't assert they exist


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
    """Test that session endpoints require authentication."""
    # Test create session endpoint - should return 401 or 403 for missing auth
    response = client.post("/api/v1/sessions/", json={
        "role": "Software Engineer",
        "job_description": "Test job"
    })
    # Should return 401 (unauthorized) or 422 (validation error) for missing auth
    assert response.status_code in [401, 403, 422]


def test_interview_endpoints_require_auth(client):
    """Test that interview endpoints require authentication."""
    # Test parse JD endpoint - should return 401 or 403 for missing auth
    response = client.post("/api/v1/parse-jd", json={
        "role": "Software Engineer",
        "jobDescription": "Test job description"
    })
    # Should return 401 (unauthorized) or 422 (validation error) for missing auth
    assert response.status_code in [401, 403, 422]


def test_admin_endpoints_exist(client):
    """Test that admin endpoints are accessible."""
    # Test admin health endpoint (correct path is /api/v1/admin/health)
    response = client.get("/api/v1/admin/health")
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
