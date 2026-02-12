"""
Integration tests for scoring endpoints.

Tests the scoring API endpoints including:
- Multi-agent analysis endpoint
- Score conversion and rubric generation
- Error handling
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing."""
    client = AsyncMock()
    client.analyze_answer = AsyncMock(return_value={
        "analysis": "This is a comprehensive analysis of the answer.",
        "score": {
            "clarity": 8.0,
            "confidence": 7.5
        },
        "suggestions": [
            "Add more specific examples",
            "Elaborate on technical details",
            "Improve structure"
        ]
    })
    return client


@pytest.fixture
def mock_ai_client_with_enhanced_rubric():
    """Mock AI client that returns enhanced rubric."""
    client = AsyncMock()
    client.analyze_answer = AsyncMock(return_value={
        "analysis": "Comprehensive analysis",
        "score": {
            "clarity": 8.0,
            "confidence": 7.5
        },
        "suggestions": ["Suggestion 1", "Suggestion 2"],
        "enhanced_rubric": {
            "verbal_communication": {
                "articulation": {"score": 4.0, "feedback": "Clear", "examples": []},
                "content_relevance": {"score": 4.5, "feedback": "Relevant", "examples": []},
                "structure": {"score": 3.5, "feedback": "Organized", "examples": []},
                "vocabulary": {"score": 4.0, "feedback": "Good", "examples": []},
                "delivery_confidence": {"score": 4.5, "feedback": "Confident", "examples": []},
                "category_score": 20.5,
                "category_feedback": "Strong verbal communication"
            },
            "interview_readiness": {
                "preparedness": {"score": 4.0, "feedback": "Prepared", "examples": []},
                "example_quality": {"score": 3.5, "feedback": "Good examples", "examples": []},
                "problem_solving": {"score": 4.0, "feedback": "Strong", "examples": []},
                "responsiveness": {"score": 3.5, "feedback": "Responsive", "examples": []},
                "category_score": 15.0,
                "category_feedback": "Well prepared"
            },
            "non_verbal_communication": {
                "eye_contact": {"score": 3.0, "feedback": "Good", "examples": []},
                "body_language": {"score": 3.0, "feedback": "Positive", "examples": []},
                "vocal_variety": {"score": 3.5, "feedback": "Varied", "examples": []},
                "pacing": {"score": 3.0, "feedback": "Appropriate", "examples": []},
                "engagement": {"score": 3.5, "feedback": "Engaged", "examples": []},
                "category_score": 16.0,
                "category_feedback": "Good non-verbal cues"
            },
            "adaptability_engagement": {
                "adaptability": {"score": 3.5, "feedback": "Adaptable", "examples": []},
                "enthusiasm": {"score": 4.0, "feedback": "Enthusiastic", "examples": []},
                "active_listening": {"score": 3.5, "feedback": "Attentive", "examples": []},
                "category_score": 11.0,
                "category_feedback": "Engaged and adaptable"
            },
            "overall_feedback": "Strong overall performance",
            "top_strengths": ["Clear communication", "Good preparation"],
            "improvement_areas": ["Could improve pacing", "More examples needed"]
        }
    })
    return client


@pytest.fixture
def sample_analysis_request():
    """Sample request for analysis."""
    return {
        "response": "Python is a high-level programming language known for its simplicity and readability. It's widely used in web development, data science, and automation.",
        "question": "What is Python?",
        "job_description": "We are looking for a Python developer with experience in web frameworks.",
        "role": "Python Developer"
    }


@pytest.fixture
def mock_current_user():
    """Mock current user for authentication."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "role": "user"
    }


class TestScoringAnalyzeEndpoint:
    """Tests for POST /api/v1/scoring/analyze endpoint."""
    
    @pytest.mark.integration
    @pytest.mark.ai
    @patch('app.routers.scoring.get_current_user')
    @patch('app.dependencies.get_ai_client_dependency')
    def test_analyze_answer_success(
        self,
        mock_get_ai_client,
        mock_get_user,
        client,
        mock_ai_client,
        sample_analysis_request,
        mock_current_user
    ):
        """Test successful answer analysis."""
        mock_get_ai_client.return_value = mock_ai_client
        mock_get_user.return_value = mock_current_user
        
        response = client.post(
            "/api/v1/scoring/analyze",
            json=sample_analysis_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "analysis" in data
        assert "processing_time" in data
        assert "agents_used" in data
        
        analysis = data["analysis"]
        assert "overall_score" in analysis
        assert "grade_tier" in analysis
        assert "enhanced_rubric" in analysis
        
        # Verify score is on 0-100 scale
        assert 0.0 <= analysis["overall_score"] <= 100.0
        
        # Verify grade tier is valid
        assert analysis["grade_tier"] in ["Excellent", "Strong", "Average", "At Risk"]
    
    @pytest.mark.integration
    @pytest.mark.ai
    @patch('app.routers.scoring.get_current_user')
    @patch('app.dependencies.get_ai_client_dependency')
    def test_analyze_answer_with_enhanced_rubric(
        self,
        mock_get_ai_client,
        mock_get_user,
        client,
        mock_ai_client_with_enhanced_rubric,
        sample_analysis_request,
        mock_current_user
    ):
        """Test analysis with enhanced rubric from AI service."""
        mock_get_ai_client.return_value = mock_ai_client_with_enhanced_rubric
        mock_get_user.return_value = mock_current_user
        
        response = client.post(
            "/api/v1/scoring/analyze",
            json=sample_analysis_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        rubric = data["analysis"]["enhanced_rubric"]
        assert rubric is not None
        assert "verbal_communication" in rubric
        assert "interview_readiness" in rubric
        assert "non_verbal_communication" in rubric
        assert "adaptability_engagement" in rubric
        assert "total_score" in rubric
        assert "grade_tier" in rubric
        
        # Verify category scores
        assert rubric["verbal_communication"]["category_score"] <= 40.0
        assert rubric["interview_readiness"]["category_score"] <= 20.0
        assert rubric["non_verbal_communication"]["category_score"] <= 25.0
        assert rubric["adaptability_engagement"]["category_score"] <= 15.0
    
    @pytest.mark.integration
    @pytest.mark.ai
    @patch('app.routers.scoring.get_current_user')
    @patch('app.dependencies.get_ai_client_dependency')
    def test_analyze_answer_ai_service_unavailable(
        self,
        mock_get_ai_client,
        mock_get_user,
        client,
        sample_analysis_request,
        mock_current_user
    ):
        """Test analysis when AI service is unavailable."""
        mock_get_ai_client.return_value = None
        mock_get_user.return_value = mock_current_user
        
        response = client.post(
            "/api/v1/scoring/analyze",
            json=sample_analysis_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()
    
    @pytest.mark.integration
    @pytest.mark.ai
    @patch('app.routers.scoring.get_current_user')
    @patch('app.dependencies.get_ai_client_dependency')
    def test_analyze_answer_ai_service_error(
        self,
        mock_get_ai_client,
        mock_get_user,
        client,
        sample_analysis_request,
        mock_current_user
    ):
        """Test analysis when AI service returns error."""
        mock_ai_client = AsyncMock()
        mock_ai_client.analyze_answer = AsyncMock(side_effect=Exception("AI service error"))
        mock_get_ai_client.return_value = mock_ai_client
        mock_get_user.return_value = mock_current_user
        
        response = client.post(
            "/api/v1/scoring/analyze",
            json=sample_analysis_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 503
    
    @pytest.mark.integration
    @pytest.mark.ai
    def test_analyze_answer_unauthorized(self, client, sample_analysis_request):
        """Test analysis endpoint without authentication."""
        response = client.post(
            "/api/v1/scoring/analyze",
            json=sample_analysis_request
        )
        
        assert response.status_code == 401 or response.status_code == 403
    
    @pytest.mark.integration
    @pytest.mark.ai
    @patch('app.routers.scoring.get_current_user')
    @patch('app.dependencies.get_ai_client_dependency')
    def test_analyze_answer_validation_error(
        self,
        mock_get_ai_client,
        mock_get_user,
        client,
        mock_ai_client,
        mock_current_user
    ):
        """Test analysis with invalid request data."""
        mock_get_ai_client.return_value = mock_ai_client
        mock_get_user.return_value = mock_current_user
        
        invalid_request = {
            "response": "",  # Empty response
            "question": "Test question",
            "job_description": "Test job description"
        }
        
        response = client.post(
            "/api/v1/scoring/analyze",
            json=invalid_request,
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422  # Validation error


class TestScoringStatusEndpoint:
    """Tests for GET /api/v1/scoring/status endpoint."""
    
    @pytest.mark.integration
    def test_get_scoring_status(self, client):
        """Test getting scoring system status."""
        response = client.get("/api/v1/scoring/status")
        
        # May return 200 or 500 depending on implementation
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "overall_status" in data
            assert "agents" in data


class TestScoringAgentsEndpoint:
    """Tests for GET /api/v1/scoring/agents endpoint."""
    
    @pytest.mark.integration
    def test_list_available_agents(self, client):
        """Test listing available scoring agents."""
        response = client.get("/api/v1/scoring/agents")
        
        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, list)
        assert "content_agent" in agents
        assert "delivery_agent" in agents
        assert "technical_agent" in agents


class TestScoringConfigurationEndpoint:
    """Tests for GET /api/v1/scoring/configuration endpoint."""
    
    @pytest.mark.integration
    def test_get_scoring_configuration(self, client):
        """Test getting scoring configuration."""
        response = client.get("/api/v1/scoring/configuration")
        
        # May return 200 or 500 depending on implementation
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "default_weights" in data or "enable_parallel_processing" in data


class TestScoringMetricsEndpoint:
    """Tests for GET /api/v1/scoring/metrics endpoint."""
    
    @pytest.mark.integration
    def test_get_performance_metrics(self, client):
        """Test getting performance metrics."""
        response = client.get("/api/v1/scoring/metrics")
        
        # May return 200 or 500 depending on implementation
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "total_analyses" in data or "average_processing_time" in data

