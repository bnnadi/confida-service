"""
Integration tests for Dashboard API endpoints.

Tests the complete flow of dashboard-related endpoints including
authentication, data retrieval, and error handling.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timedelta
from app.database.models import InterviewSession, User
import uuid


class TestDashboardEndpoints:
    """Test cases for dashboard API endpoints."""
    
    @pytest.fixture
    def mock_current_user(self, sample_user):
        """Mock current user for authentication."""
        return {
            "user_id": str(sample_user.id),
            "email": sample_user.email,
            "is_admin": False
        }
    
    @pytest.fixture
    def mock_admin_user(self, sample_user):
        """Mock admin user for authentication."""
        return {
            "user_id": str(sample_user.id),
            "email": sample_user.email,
            "is_admin": True
        }
    
    @pytest.fixture
    def sample_sessions(self, db_session, sample_user):
        """Create sample sessions for testing."""
        sessions = []
        base_date = datetime.utcnow() - timedelta(days=20)
        
        for i in range(5):
            session = InterviewSession(
                user_id=sample_user.id,
                role="Python Developer",
                status="completed" if i < 4 else "active",
                total_questions=5,
                completed_questions=5 if i < 4 else 2,
                overall_score={"overall": 7.0 + i * 0.5, "python": 6.0 + i * 0.5},
                created_at=base_date + timedelta(days=i*4),
                updated_at=base_date + timedelta(days=i*4) + timedelta(minutes=30)
            )
            db_session.add(session)
            sessions.append(session)
        
        db_session.commit()
        return sessions
    
    @pytest.mark.integration
    def test_get_dashboard_overview_success(
        self, client, sample_user, sample_sessions, mock_current_user
    ):
        """Test successful dashboard overview retrieval."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/overview/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert "total_sessions" in data
        assert "average_score" in data
        assert "improvement_rate" in data
        assert "current_streak" in data
        assert "recent_activity" in data
        assert "last_updated" in data
    
    @pytest.mark.integration
    def test_get_dashboard_overview_unauthorized(
        self, client, sample_user, sample_sessions
    ):
        """Test dashboard overview with unauthorized access."""
        other_user_id = str(uuid.uuid4())
        mock_user = {
            "user_id": other_user_id,
            "email": "other@example.com",
            "is_admin": False
        }
        
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_user):
            response = client.get(
                f"/api/v1/dashboard/overview/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 403
    
    @pytest.mark.integration
    def test_get_dashboard_overview_admin_access(
        self, client, sample_user, sample_sessions, mock_admin_user
    ):
        """Test dashboard overview with admin access."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_admin_user):
            response = client.get(
                f"/api/v1/dashboard/overview/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
    
    @pytest.mark.integration
    def test_get_user_progress_success(
        self, client, sample_user, sample_sessions, mock_current_user
    ):
        """Test successful user progress retrieval."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/progress/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert "skill_progression" in data
        assert "difficulty_progression" in data
        assert "time_progression" in data
        assert "overall_trend" in data
        assert data["overall_trend"] in ["improving", "stable", "declining"]
    
    @pytest.mark.integration
    def test_get_analytics_data_success(
        self, client, sample_user, sample_sessions, mock_current_user
    ):
        """Test successful analytics data retrieval."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/analytics/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert "performance_metrics" in data
        assert "skill_breakdown" in data
        assert "time_analysis" in data
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
    
    @pytest.mark.integration
    def test_get_performance_metrics_success(
        self, client, sample_user, sample_sessions, mock_current_user
    ):
        """Test successful performance metrics retrieval."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/metrics/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert "total_sessions" in data
        assert "completed_sessions" in data
        assert "average_score" in data
        assert "best_score" in data
        assert "worst_score" in data
        assert "completion_rate" in data
        assert "average_session_duration" in data
        assert "total_questions_answered" in data
    
    @pytest.mark.integration
    def test_get_performance_trends_success(
        self, client, sample_user, sample_sessions, mock_current_user
    ):
        """Test successful performance trends retrieval."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/trends/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert "score_trend" in data
        assert "completion_trend" in data
        assert "skill_trends" in data
        assert "trend_direction" in data
        assert "trend_percentage" in data
        assert data["trend_direction"] in ["improving", "stable", "declining"]
    
    @pytest.mark.integration
    def test_get_user_insights_success(
        self, client, sample_user, sample_sessions, mock_current_user
    ):
        """Test successful user insights retrieval."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/insights/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert "strengths" in data
        assert "weaknesses" in data
        assert "recommendations" in data
        assert "milestones" in data
        assert "next_goals" in data
        assert isinstance(data["strengths"], list)
        assert isinstance(data["weaknesses"], list)
        assert isinstance(data["recommendations"], list)
    
    @pytest.mark.integration
    def test_dashboard_endpoints_require_auth(self, client, sample_user):
        """Test that dashboard endpoints require authentication."""
        endpoints = [
            f"/api/v1/dashboard/overview/{sample_user.id}",
            f"/api/v1/dashboard/progress/{sample_user.id}",
            f"/api/v1/dashboard/analytics/{sample_user.id}",
            f"/api/v1/dashboard/metrics/{sample_user.id}",
            f"/api/v1/dashboard/trends/{sample_user.id}",
            f"/api/v1/dashboard/insights/{sample_user.id}",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should return 401 or 403 without auth
            assert response.status_code in [401, 403, 422]
    
    @pytest.mark.integration
    def test_dashboard_endpoints_with_invalid_days(self, client, sample_user, mock_current_user):
        """Test dashboard endpoints with invalid days parameter."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/overview/{sample_user.id}",
                params={"days": 500}  # Exceeds max of 365
            )
        
        # Should validate and return 422 or handle gracefully
        assert response.status_code in [200, 422]
    
    @pytest.mark.integration
    def test_dashboard_endpoints_with_no_data(
        self, client, sample_user, mock_current_user
    ):
        """Test dashboard endpoints when user has no data."""
        with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
            response = client.get(
                f"/api/v1/dashboard/overview/{sample_user.id}",
                params={"days": 30}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(sample_user.id)
        assert data["total_sessions"] == 0
        assert data["average_score"] == 0.0

