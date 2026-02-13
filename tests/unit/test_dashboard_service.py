"""
Unit tests for Dashboard Service.

Tests the dashboard service logic and data formatting.
"""
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from app.services.dashboard_service import DashboardService
from app.database.models import InterviewSession, User
import uuid


class TestDashboardService:
    """Test cases for DashboardService."""
    
    @pytest.mark.unit
    def test_get_dashboard_overview(self, db_session, sample_user):
        """Test getting dashboard overview."""
        service = DashboardService(db_session)
        
        # Create sessions
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 7.0},
            created_at=datetime.utcnow() - timedelta(days=20)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 9.0},
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        
        db_session.add_all([session1, session2])
        db_session.commit()
        
        overview = service.get_dashboard_overview(str(sample_user.id), days=30)
        
        assert overview.user_id == str(sample_user.id)
        assert overview.total_sessions == 2
        assert overview.average_score == 8.0
        assert isinstance(overview.improvement_rate, float)
        assert isinstance(overview.current_streak, int)
        assert isinstance(overview.recent_activity, list)
        assert isinstance(overview.last_updated, datetime)
    
    @pytest.mark.unit
    def test_get_dashboard_overview_no_sessions(self, db_session, sample_user):
        """Test getting dashboard overview with no sessions."""
        service = DashboardService(db_session)
        
        overview = service.get_dashboard_overview(str(sample_user.id), days=30)
        
        assert overview.user_id == str(sample_user.id)
        assert overview.total_sessions == 0
        assert overview.average_score == 0.0
        assert overview.current_streak == 0
    
    @pytest.mark.unit
    def test_get_user_progress(self, db_session, sample_user):
        """Test getting user progress."""
        service = DashboardService(db_session)
        
        # Create sessions with progress data
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 7.0, "overall": 7.0},
            created_at=datetime.utcnow() - timedelta(days=20)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 8.0, "overall": 8.0},
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        
        db_session.add_all([session1, session2])
        db_session.commit()
        
        progress = service.get_user_progress(str(sample_user.id), days=30)
        
        assert progress.user_id == str(sample_user.id)
        assert isinstance(progress.skill_progression, dict)
        assert isinstance(progress.difficulty_progression, list)
        assert isinstance(progress.time_progression, list)
        assert progress.overall_trend in ["improving", "stable", "declining"]
        assert isinstance(progress.last_updated, datetime)
    
    @pytest.mark.unit
    def test_get_analytics_data(self, db_session, sample_user):
        """Test getting analytics data."""
        service = DashboardService(db_session)
        
        # Create sessions
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 7.0, "django": 8.0, "overall": 7.5},
            created_at=datetime.utcnow() - timedelta(days=10),
            updated_at=datetime.utcnow() - timedelta(days=10) + timedelta(minutes=30)
        )
        
        db_session.add(session1)
        db_session.commit()
        
        analytics = service.get_analytics_data(str(sample_user.id), days=30)
        
        assert analytics.user_id == str(sample_user.id)
        assert isinstance(analytics.performance_metrics, dict)
        assert isinstance(analytics.skill_breakdown, dict)
        assert isinstance(analytics.time_analysis, dict)
        assert isinstance(analytics.recommendations, list)
        assert isinstance(analytics.last_updated, datetime)
    
    @pytest.mark.unit
    def test_get_performance_metrics(self, db_session, sample_user):
        """Test getting performance metrics."""
        service = DashboardService(db_session)
        
        # Create sessions
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 7.0},
            created_at=datetime.utcnow() - timedelta(days=10),
            updated_at=datetime.utcnow() - timedelta(days=10) + timedelta(minutes=30)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 9.0},
            created_at=datetime.utcnow() - timedelta(days=5),
            updated_at=datetime.utcnow() - timedelta(days=5) + timedelta(minutes=45)
        )
        
        db_session.add_all([session1, session2])
        db_session.commit()
        
        metrics = service.get_performance_metrics(str(sample_user.id), days=30)
        
        assert metrics.user_id == str(sample_user.id)
        assert metrics.total_sessions == 2
        assert metrics.completed_sessions == 2
        assert metrics.average_score == 8.0
        assert metrics.best_score == 9.0
        assert metrics.worst_score == 7.0
        assert metrics.completion_rate == 100.0
        assert metrics.total_questions_answered == 10
        assert isinstance(metrics.last_updated, datetime)
    
    @pytest.mark.unit
    def test_get_performance_trends(self, db_session, sample_user):
        """Test getting performance trends."""
        service = DashboardService(db_session)
        
        # Create sessions over time
        base_date = datetime.utcnow() - timedelta(days=20)
        for i in range(3):
            session = InterviewSession(
                user_id=sample_user.id,
                role="Python Developer",
                status="completed",
                total_questions=5,
                completed_questions=5,
                overall_score={"overall": 7.0 + i * 0.5, "python": 6.0 + i * 0.5},
                created_at=base_date + timedelta(days=i*7)
            )
            db_session.add(session)
        
        db_session.commit()
        
        trends = service.get_performance_trends(str(sample_user.id), days=30)
        
        assert trends.user_id == str(sample_user.id)
        assert isinstance(trends.score_trend, list)
        assert isinstance(trends.completion_trend, list)
        assert isinstance(trends.skill_trends, dict)
        assert trends.trend_direction in ["improving", "stable", "declining"]
        assert isinstance(trends.trend_percentage, float)
        assert isinstance(trends.last_updated, datetime)
    
    @pytest.mark.unit
    def test_get_user_insights(self, db_session, sample_user):
        """Test getting user insights."""
        service = DashboardService(db_session)
        
        # Create sessions with varying scores
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 9.0, "django": 8.0, "testing": 5.0, "overall": 7.3},
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 8.5, "django": 7.5, "testing": 5.5, "overall": 7.2},
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        
        db_session.add_all([session1, session2])
        db_session.commit()
        
        insights = service.get_user_insights(str(sample_user.id), days=30)
        
        assert insights.user_id == str(sample_user.id)
        assert isinstance(insights.strengths, list)
        assert isinstance(insights.weaknesses, list)
        assert isinstance(insights.recommendations, list)
        assert isinstance(insights.milestones, list)
        assert isinstance(insights.next_goals, list)
        assert isinstance(insights.last_updated, datetime)

    @pytest.mark.unit
    def test_get_dashboard_overview_aggregator_raises(self, db_session, sample_user):
        """Test get_dashboard_overview propagates exception from aggregator."""
        service = DashboardService(db_session)
        with patch.object(service.aggregator, "get_user_sessions_summary", side_effect=RuntimeError("DB error")):
            with pytest.raises(RuntimeError, match="DB error"):
                service.get_dashboard_overview(str(sample_user.id), days=30)

    @pytest.mark.unit
    def test_get_user_progress_aggregator_raises(self, db_session, sample_user):
        """Test get_user_progress propagates exception from aggregator."""
        service = DashboardService(db_session)
        with patch.object(service.aggregator, "get_user_progress_data", side_effect=ValueError("Bad data")):
            with pytest.raises(ValueError, match="Bad data"):
                service.get_user_progress(str(sample_user.id), days=30)

    @pytest.mark.unit
    def test_get_analytics_data_aggregator_raises(self, db_session, sample_user):
        """Test get_analytics_data propagates exception from aggregator."""
        service = DashboardService(db_session)
        with patch.object(service.aggregator, "get_performance_metrics_detailed", side_effect=RuntimeError("Metrics error")):
            with pytest.raises(RuntimeError, match="Metrics error"):
                service.get_analytics_data(str(sample_user.id), days=30)

