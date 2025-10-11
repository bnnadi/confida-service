"""
Unit tests for interview endpoints.
"""
import pytest
from fastapi.testclient import TestClient

class TestInterviewEndpoints:
    """Test cases for interview-related endpoints."""
    
    def test_parse_jd_success(self, client: TestClient, sample_parse_request):
        """Test successful job description parsing."""
        response = client.post("/api/v1/parse-jd", json=sample_parse_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert isinstance(data["questions"], list)
        assert len(data["questions"]) > 0
        assert all(isinstance(q, str) for q in data["questions"])
    
    def test_parse_jd_with_service_parameter(self, client: TestClient, sample_parse_request):
        """Test job description parsing with service parameter."""
        response = client.post(
            "/api/v1/parse-jd?service=openai",
            json=sample_parse_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0
    
    def test_parse_jd_invalid_request_empty_role(self, client: TestClient):
        """Test job description parsing with empty role."""
        invalid_request = {
            "role": "",
            "jobDescription": "We are looking for a developer with 5+ years of experience."
        }
        
        response = client.post("/api/v1/parse-jd", json=invalid_request)
        assert response.status_code == 422
    
    def test_parse_jd_invalid_request_short_description(self, client: TestClient):
        """Test job description parsing with too short description."""
        invalid_request = {
            "role": "Senior Developer",
            "jobDescription": "Short"
        }
        
        response = client.post("/api/v1/parse-jd", json=invalid_request)
        assert response.status_code == 422
    
    def test_parse_jd_missing_fields(self, client: TestClient):
        """Test job description parsing with missing fields."""
        incomplete_request = {
            "role": "Senior Python Developer"
        }
        
        response = client.post("/api/v1/parse-jd", json=incomplete_request)
        assert response.status_code == 422
    
    def test_analyze_answer_success(self, client: TestClient, sample_analyze_request):
        """Test successful answer analysis."""
        response = client.post("/api/v1/analyze-answer", json=sample_analyze_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "missingKeywords" in data
        assert "improvements" in data
        assert "idealAnswer" in data
        
        # Validate score structure
        assert isinstance(data["score"], dict)
        assert "overall" in data["score"]
    
    def test_analyze_answer_with_service_parameter(self, client: TestClient, sample_analyze_request):
        """Test answer analysis with service parameter."""
        response = client.post(
            "/api/v1/analyze-answer?service=openai",
            json=sample_analyze_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
    
    def test_analyze_answer_invalid_request(self, client: TestClient):
        """Test answer analysis with invalid request."""
        invalid_request = {
            "jobDescription": "Short",
            "question": "",
            "answer": "Short"
        }
        
        response = client.post("/api/v1/analyze-answer", json=invalid_request)
        assert response.status_code == 422
    
    def test_analyze_answer_missing_fields(self, client: TestClient):
        """Test answer analysis with missing fields."""
        incomplete_request = {
            "jobDescription": "We are looking for a developer...",
            "question": "Tell me about yourself"
        }
        
        response = client.post("/api/v1/analyze-answer", json=incomplete_request)
        assert response.status_code == 422


class TestAdminEndpoints:
    """Test cases for admin endpoints."""
    
    def test_get_services_status(self, client: TestClient):
        """Test getting services status."""
        response = client.get("/api/v1/admin/services")
        
        assert response.status_code == 200
        data = response.json()
        assert "available_services" in data
        assert "service_priority" in data
    
    def test_get_models(self, client: TestClient):
        """Test getting available models."""
        response = client.get("/api/v1/admin/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/api/v1/admin/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_rate_limits_config(self, client: TestClient):
        """Test rate limits configuration endpoint."""
        response = client.get("/api/v1/admin/rate-limits")
        
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "backend" in data


class TestHealthEndpoints:
    """Test cases for health check endpoints."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_readiness_endpoint(self, client: TestClient):
        """Test readiness endpoint."""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)

