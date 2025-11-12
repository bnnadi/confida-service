"""
Unit tests for Data Aggregator service.

Tests the data aggregation logic for dashboard endpoints.
"""
import pytest
from datetime import datetime, timedelta
from app.services.data_aggregator import DataAggregator
from app.database.models import (
    InterviewSession, Question, SessionQuestion, AnalyticsEvent, User
)
import uuid


class TestDataAggregator:
    """Test cases for DataAggregator service."""
    
    @pytest.mark.unit
    def test_get_user_sessions_summary_no_sessions(self, db_session, sample_user):
        """Test getting session summary when user has no sessions."""
        aggregator = DataAggregator(db_session)
        
        result = aggregator.get_user_sessions_summary(str(sample_user.id))
        
        assert result["total_sessions"] == 0
        assert result["completed_sessions"] == 0
        assert result["active_sessions"] == 0
        assert result["average_score"] == 0.0
        assert result["completion_rate"] == 0.0
    
    @pytest.mark.unit
    def test_get_user_sessions_summary_with_sessions(self, db_session, sample_user):
        """Test getting session summary with multiple sessions."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions with different statuses and scores
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 8.5}
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 7.5}
        )
        session3 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="active",
            total_questions=5,
            completed_questions=2,
            overall_score=None
        )
        
        db_session.add_all([session1, session2, session3])
        db_session.commit()
        
        result = aggregator.get_user_sessions_summary(str(sample_user.id))
        
        assert result["total_sessions"] == 3
        assert result["completed_sessions"] == 2
        assert result["active_sessions"] == 1
        assert result["average_score"] == 8.0  # (8.5 + 7.5) / 2
        assert result["completion_rate"] == pytest.approx(66.67, abs=0.1)
    
    @pytest.mark.unit
    def test_get_user_sessions_summary_with_date_range(self, db_session, sample_user):
        """Test getting session summary with date filtering."""
        aggregator = DataAggregator(db_session)
        
        # Create old session
        old_session = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 6.0},
            created_at=datetime.utcnow() - timedelta(days=60)
        )
        
        # Create recent session
        recent_session = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"overall": 9.0},
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        
        db_session.add_all([old_session, recent_session])
        db_session.commit()
        
        # Get only recent sessions (last 30 days)
        start_date = datetime.utcnow() - timedelta(days=30)
        result = aggregator.get_user_sessions_summary(
            str(sample_user.id),
            start_date=start_date
        )
        
        assert result["total_sessions"] == 1
        assert result["average_score"] == 9.0
    
    @pytest.mark.unit
    def test_get_user_progress_data(self, db_session, sample_user):
        """Test getting user progress data."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions with scores
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 7.0, "django": 8.0, "overall": 7.5},
            created_at=datetime.utcnow() - timedelta(days=20)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 8.0, "django": 9.0, "overall": 8.5},
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        
        # Create questions with difficulty
        question1 = Question(
            question_text="Test question 1",
            question_metadata={},
            difficulty_level="easy",
            category="python"
        )
        question2 = Question(
            question_text="Test question 2",
            question_metadata={},
            difficulty_level="hard",
            category="django"
        )
        
        db_session.add_all([session1, session2, question1, question2])
        db_session.commit()
        
        # Create session questions
        sq1 = SessionQuestion(
            session_id=session1.id,
            question_id=question1.id,
            question_order=1
        )
        sq2 = SessionQuestion(
            session_id=session2.id,
            question_id=question2.id,
            question_order=1
        )
        
        db_session.add_all([sq1, sq2])
        db_session.commit()
        
        result = aggregator.get_user_progress_data(str(sample_user.id), days=30)
        
        assert "skill_progression" in result
        assert "difficulty_progression" in result
        assert "time_progression" in result
        assert "overall_trend" in result
        assert len(result["time_progression"]) == 2
        assert result["overall_trend"] in ["improving", "stable", "declining"]
    
    @pytest.mark.unit
    def test_get_recent_activity(self, db_session, sample_user):
        """Test getting recent activity."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="active",
            total_questions=5,
            completed_questions=2,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Create analytics event
        event = AnalyticsEvent(
            user_id=sample_user.id,
            event_type="session_started",
            event_data={"session_id": str(session2.id)}
        )
        
        db_session.add_all([session1, session2, event])
        db_session.commit()
        
        result = aggregator.get_recent_activity(str(sample_user.id), limit=5)
        
        assert len(result) <= 5
        assert all("activity_type" in item for item in result)
        assert all("activity_date" in item for item in result)
        assert all("activity_data" in item for item in result)
    
    @pytest.mark.unit
    def test_get_current_streak(self, db_session, sample_user):
        """Test calculating current streak."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions for consecutive days
        today = datetime.utcnow().date()
        for i in range(3):
            session_date = datetime.combine(today - timedelta(days=i), datetime.min.time())
            session = InterviewSession(
                user_id=sample_user.id,
                role="Python Developer",
                status="completed",
                total_questions=5,
                completed_questions=5,
                created_at=session_date
            )
            db_session.add(session)
        
        db_session.commit()
        
        streak = aggregator.get_current_streak(str(sample_user.id))
        
        assert streak >= 3
    
    @pytest.mark.unit
    def test_get_current_streak_no_activity(self, db_session, sample_user):
        """Test streak calculation with no recent activity."""
        aggregator = DataAggregator(db_session)
        
        streak = aggregator.get_current_streak(str(sample_user.id))
        
        assert streak == 0
    
    @pytest.mark.unit
    def test_get_skill_breakdown(self, db_session, sample_user):
        """Test getting skill breakdown."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions with skill scores
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 7.0, "django": 8.0},
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 8.0, "django": 9.0},
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        
        db_session.add_all([session1, session2])
        db_session.commit()
        
        result = aggregator.get_skill_breakdown(str(sample_user.id), days=30)
        
        assert "python" in result
        assert "django" in result
        assert result["python"] == 7.5  # (7.0 + 8.0) / 2
        assert result["django"] == 8.5  # (8.0 + 9.0) / 2
    
    @pytest.mark.unit
    def test_get_performance_metrics_detailed(self, db_session, sample_user):
        """Test getting detailed performance metrics."""
        aggregator = DataAggregator(db_session)
        
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
        session3 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="active",
            total_questions=5,
            completed_questions=2,
            overall_score=None,
            created_at=datetime.utcnow() - timedelta(days=1),
            updated_at=datetime.utcnow() - timedelta(days=1) + timedelta(minutes=15)
        )
        
        db_session.add_all([session1, session2, session3])
        db_session.commit()
        
        result = aggregator.get_performance_metrics_detailed(str(sample_user.id), days=30)
        
        assert result["total_sessions"] == 3
        assert result["completed_sessions"] == 2
        assert result["average_score"] == 8.0  # (7.0 + 9.0) / 2
        assert result["best_score"] == 9.0
        assert result["worst_score"] == 7.0
        assert result["completion_rate"] == pytest.approx(66.67, abs=0.1)
        assert result["total_questions_answered"] == 12  # 5 + 5 + 2
        assert result["average_session_duration"] > 0
    
    @pytest.mark.unit
    def test_get_trend_data(self, db_session, sample_user):
        """Test getting trend data."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions over time
        base_date = datetime.utcnow() - timedelta(days=20)
        for i in range(5):
            session = InterviewSession(
                user_id=sample_user.id,
                role="Python Developer",
                status="completed",
                total_questions=5,
                completed_questions=5,
                overall_score={"overall": 7.0 + i * 0.5, "python": 6.0 + i * 0.5},
                created_at=base_date + timedelta(days=i*4)
            )
            db_session.add(session)
        
        db_session.commit()
        
        result = aggregator.get_trend_data(str(sample_user.id), days=30)
        
        assert "score_trend" in result
        assert "completion_trend" in result
        assert "skill_trends" in result
        assert "trend_direction" in result
        assert "trend_percentage" in result
        assert len(result["score_trend"]) == 5
        assert result["trend_direction"] in ["improving", "stable", "declining"]
    
    @pytest.mark.unit
    def test_get_user_insights(self, db_session, sample_user):
        """Test getting user insights."""
        aggregator = DataAggregator(db_session)
        
        # Create sessions with varying scores
        session1 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 9.0, "django": 8.0, "testing": 5.0},
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        session2 = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            status="completed",
            total_questions=5,
            completed_questions=5,
            overall_score={"python": 8.5, "django": 7.5, "testing": 5.5},
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        
        db_session.add_all([session1, session2])
        db_session.commit()
        
        result = aggregator.get_user_insights(str(sample_user.id), days=30)
        
        assert "strengths" in result
        assert "weaknesses" in result
        assert "recommendations" in result
        assert "milestones" in result
        assert "next_goals" in result
        assert isinstance(result["strengths"], list)
        assert isinstance(result["weaknesses"], list)
        assert isinstance(result["recommendations"], list)

