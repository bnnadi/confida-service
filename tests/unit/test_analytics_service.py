"""
Unit tests for AnalyticsService.

Tests the analytics service logic including performance metrics, trend analysis,
session analytics, dimension progress, session comparison, filtered search,
heatmap generation, and goal management.
"""
import pytest
import uuid as _uuid
uuid = _uuid  # alias for use in tests
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app.services.analytics_service import AnalyticsService
from app.database.models import (
    InterviewSession, User, Question, SessionQuestion, Answer, UserGoal
)
from app.models.analytics_models import (
    ReportRequest, ReportType, ReportFormat, AnalyticsFilter,
    UserGoalCreate, UserGoalUpdate, GoalType, GoalStatus
)


@pytest.fixture
def analytics_user(db_session):
    """Create a unique user for analytics tests (avoids UNIQUE constraint issues)."""
    user = User(
        email=f"analytics-{_uuid.uuid4().hex[:8]}@test.com",
        name="Analytics Test User",
        password_hash=generate_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_session(
    db_session,
    user_id,
    role="Python Developer",
    status="completed",
    total_questions=5,
    completed_questions=5,
    overall_score=None,
    created_at=None,
    updated_at=None,
):
    """Helper to create an InterviewSession with sensible defaults."""
    now = datetime.utcnow()
    session = InterviewSession(
        user_id=user_id,
        role=role,
        job_description="Test job description",
        status=status,
        total_questions=total_questions,
        completed_questions=completed_questions,
        overall_score=overall_score or {"overall": 7.5},
        created_at=created_at or now - timedelta(days=5),
        updated_at=updated_at or now - timedelta(days=5) + timedelta(minutes=30),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


def _create_sessions_over_time(db_session, user_id, count=5, base_score=6.0, step=0.5):
    """Create several sessions spread over time with incrementing scores."""
    sessions = []
    base_date = datetime.utcnow() - timedelta(days=count * 3)
    for i in range(count):
        score = base_score + i * step
        created = base_date + timedelta(days=i * 3)
        s = _create_session(
            db_session,
            user_id,
            overall_score={"overall": score, "python": score + 0.5, "communication": score - 0.5},
            created_at=created,
            updated_at=created + timedelta(minutes=25),
        )
        sessions.append(s)
    return sessions


# ---------------------------------------------------------------------------
# Score extraction helpers
# ---------------------------------------------------------------------------

class TestScoreExtraction:
    """Tests for the private JSONB score parsing helpers."""

    @pytest.mark.unit
    def test_extract_score_none(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_score_value(None) is None

    @pytest.mark.unit
    def test_extract_score_float(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_score_value(8.5) == 8.5

    @pytest.mark.unit
    def test_extract_score_int(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_score_value(7) == 7.0

    @pytest.mark.unit
    def test_extract_score_dict_overall(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_score_value({"overall": 9.0, "python": 8.0}) == 9.0

    @pytest.mark.unit
    def test_extract_score_dict_average(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_score_value({"average": 7.5}) == 7.5

    @pytest.mark.unit
    def test_extract_score_dict_unknown_keys(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_score_value({"python": 8.0}) is None

    @pytest.mark.unit
    def test_extract_dimension_scores(self, db_session):
        svc = AnalyticsService(db_session)
        dims = svc._extract_dimension_scores({"overall": 9.0, "python": 8.0, "communication": 7.0})
        assert "python" in dims
        assert "communication" in dims
        assert "overall" not in dims  # meta key excluded

    @pytest.mark.unit
    def test_extract_dimension_scores_non_dict(self, db_session):
        svc = AnalyticsService(db_session)
        assert svc._extract_dimension_scores(8.5) == {}


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------

class TestPerformanceMetrics:
    """Tests for get_performance_metrics."""

    @pytest.mark.unit
    def test_no_sessions_returns_empty(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        metrics = svc.get_performance_metrics(str(analytics_user.id), "30d")
        assert metrics.total_sessions == 0
        assert metrics.average_score == 0.0
        assert metrics.completion_rate == 0.0

    @pytest.mark.unit
    def test_with_sessions(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=4, base_score=7.0)
        svc = AnalyticsService(db_session)
        metrics = svc.get_performance_metrics(str(analytics_user.id), "30d")

        assert metrics.total_sessions == 4
        assert metrics.average_score > 0
        assert metrics.completion_rate == 100.0
        assert isinstance(metrics.strongest_areas, list)
        assert isinstance(metrics.improvement_areas, list)
        assert metrics.time_period == "30d"

    @pytest.mark.unit
    def test_improvement_trend_calculation(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=6, base_score=5.0, step=1.0)
        svc = AnalyticsService(db_session)
        metrics = svc.get_performance_metrics(str(analytics_user.id), "90d")

        # Scores go from 5 to 10 — trend should be positive
        assert metrics.improvement_trend > 0


# ---------------------------------------------------------------------------
# Trend Analysis
# ---------------------------------------------------------------------------

class TestTrendAnalysis:
    """Tests for get_trend_analysis."""

    @pytest.mark.unit
    def test_no_sessions(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        trend = svc.get_trend_analysis(str(analytics_user.id), "average_score", "30d")
        assert trend.data_points == []
        assert trend.trend_direction.value == "stable"
        assert trend.confidence_level == 0.0

    @pytest.mark.unit
    def test_with_sessions(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=5)
        svc = AnalyticsService(db_session)
        trend = svc.get_trend_analysis(str(analytics_user.id), "average_score", "30d")

        assert len(trend.data_points) > 0
        assert trend.metric == "average_score"
        assert trend.time_period == "30d"
        assert trend.confidence_level > 0

    @pytest.mark.unit
    def test_completion_rate_metric(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=3)
        svc = AnalyticsService(db_session)
        trend = svc.get_trend_analysis(str(analytics_user.id), "completion_rate", "30d")
        assert trend.metric == "completion_rate"

    @pytest.mark.unit
    def test_total_sessions_metric(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=3)
        svc = AnalyticsService(db_session)
        trend = svc.get_trend_analysis(str(analytics_user.id), "total_sessions", "30d")
        assert trend.metric == "total_sessions"


# ---------------------------------------------------------------------------
# Session Analytics
# ---------------------------------------------------------------------------

class TestSessionAnalytics:
    """Tests for get_session_analytics."""

    @pytest.mark.unit
    def test_returns_list(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=3)
        svc = AnalyticsService(db_session)
        sessions = svc.get_session_analytics(str(analytics_user.id), limit=10, offset=0)
        assert isinstance(sessions, list)
        assert len(sessions) == 3

    @pytest.mark.unit
    def test_pagination(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=5)
        svc = AnalyticsService(db_session)

        page1 = svc.get_session_analytics(str(analytics_user.id), limit=2, offset=0)
        page2 = svc.get_session_analytics(str(analytics_user.id), limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].session_id != page2[0].session_id

    @pytest.mark.unit
    def test_empty_for_unknown_user(self, db_session):
        svc = AnalyticsService(db_session)
        sessions = svc.get_session_analytics(str(uuid.uuid4()), limit=10, offset=0)
        assert sessions == []


# ---------------------------------------------------------------------------
# Analytics Summary
# ---------------------------------------------------------------------------

class TestAnalyticsSummary:
    """Tests for get_analytics_summary."""

    @pytest.mark.unit
    def test_summary_structure(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=3)
        svc = AnalyticsService(db_session)
        summary = svc.get_analytics_summary(str(analytics_user.id), "30d")

        assert summary.total_sessions == 3
        assert isinstance(summary.average_score, float)
        assert isinstance(summary.recent_activity, list)
        assert isinstance(summary.top_performing_areas, list)
        assert isinstance(summary.areas_for_improvement, list)

    @pytest.mark.unit
    def test_summary_empty_user(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        summary = svc.get_analytics_summary(str(analytics_user.id), "30d")
        assert summary.total_sessions == 0


# ---------------------------------------------------------------------------
# Performance Comparison
# ---------------------------------------------------------------------------

class TestPerformanceComparison:
    """Tests for get_performance_comparison."""

    @pytest.mark.unit
    def test_comparison_returns_model(self, db_session, analytics_user):
        # Create old sessions
        old_base = datetime.utcnow() - timedelta(days=50)
        for i in range(3):
            _create_session(
                db_session, analytics_user.id,
                overall_score={"overall": 5.0},
                created_at=old_base + timedelta(days=i),
            )
        # Create recent sessions
        recent_base = datetime.utcnow() - timedelta(days=10)
        for i in range(3):
            _create_session(
                db_session, analytics_user.id,
                overall_score={"overall": 8.0},
                created_at=recent_base + timedelta(days=i),
            )

        svc = AnalyticsService(db_session)
        comparison = svc.get_performance_comparison(str(analytics_user.id), "30d", "30d")

        assert comparison.current_period.total_sessions == 3
        assert comparison.previous_period.total_sessions == 3
        assert isinstance(comparison.improvement_percentage, float)

    @pytest.mark.unit
    def test_comparison_no_sessions(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        comparison = svc.get_performance_comparison(str(analytics_user.id), "30d", "30d")
        assert comparison.current_period.total_sessions == 0
        assert comparison.improvement_percentage == 0.0


# ---------------------------------------------------------------------------
# Dimension Progress
# ---------------------------------------------------------------------------

class TestDimensionProgress:
    """Tests for get_dimension_progress."""

    @pytest.mark.unit
    def test_dimension_progress(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=4)
        svc = AnalyticsService(db_session)
        progress = svc.get_dimension_progress(str(analytics_user.id), "30d")

        assert progress.user_id == str(analytics_user.id)
        assert isinstance(progress.dimensions, list)
        assert progress.overall_score >= 0
        assert isinstance(progress.data_points, list)

    @pytest.mark.unit
    def test_dimension_progress_no_sessions(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        progress = svc.get_dimension_progress(str(analytics_user.id), "30d")
        assert progress.dimensions == []
        assert progress.overall_score == 0.0


# ---------------------------------------------------------------------------
# Session Comparison
# ---------------------------------------------------------------------------

class TestSessionComparison:
    """Tests for compare_sessions."""

    @pytest.mark.unit
    def test_compare_two_sessions(self, db_session, analytics_user):
        s1 = _create_session(
            db_session, analytics_user.id,
            overall_score={"overall": 6.0, "python": 7.0},
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        s2 = _create_session(
            db_session, analytics_user.id,
            overall_score={"overall": 8.0, "python": 9.0},
            created_at=datetime.utcnow() - timedelta(days=2),
        )

        svc = AnalyticsService(db_session)
        result = svc.compare_sessions(str(analytics_user.id), str(s1.id), str(s2.id))

        assert result.score_delta == pytest.approx(2.0, abs=0.1)
        assert isinstance(result.category_deltas, dict)
        assert "improvement" in result.improvement_summary.lower() or "higher" in result.improvement_summary.lower()

    @pytest.mark.unit
    def test_compare_sessions_not_found(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        with pytest.raises(ValueError, match="not found"):
            svc.compare_sessions(str(analytics_user.id), str(uuid.uuid4()), str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Filtered Session Search
# ---------------------------------------------------------------------------

class TestFilteredSessions:
    """Tests for get_filtered_sessions."""

    @pytest.mark.unit
    def test_filter_by_role(self, db_session, analytics_user):
        _create_session(db_session, analytics_user.id, role="Python Developer")
        _create_session(db_session, analytics_user.id, role="Java Developer")

        svc = AnalyticsService(db_session)
        filters = AnalyticsFilter(role="Python")
        result = svc.get_filtered_sessions(str(analytics_user.id), filters)

        assert result.total_count >= 1
        assert all("Python" in s.role for s in result.sessions)

    @pytest.mark.unit
    def test_filter_by_status(self, db_session, analytics_user):
        _create_session(db_session, analytics_user.id, status="completed")
        _create_session(db_session, analytics_user.id, status="active")

        svc = AnalyticsService(db_session)
        filters = AnalyticsFilter(session_status="completed")
        result = svc.get_filtered_sessions(str(analytics_user.id), filters)

        assert all(s.status == "completed" for s in result.sessions)

    @pytest.mark.unit
    def test_filter_by_score_range(self, db_session, analytics_user):
        _create_session(db_session, analytics_user.id, overall_score={"overall": 4.0})
        _create_session(db_session, analytics_user.id, overall_score={"overall": 8.0})
        _create_session(db_session, analytics_user.id, overall_score={"overall": 9.5})

        svc = AnalyticsService(db_session)
        filters = AnalyticsFilter(min_score=7.0, max_score=9.0)
        result = svc.get_filtered_sessions(str(analytics_user.id), filters)

        assert result.total_count >= 1
        assert all(7.0 <= s.average_score <= 9.0 for s in result.sessions)

    @pytest.mark.unit
    def test_filter_pagination(self, db_session, analytics_user):
        for _ in range(5):
            _create_session(db_session, analytics_user.id)

        svc = AnalyticsService(db_session)
        filters = AnalyticsFilter(limit=2, offset=0)
        result = svc.get_filtered_sessions(str(analytics_user.id), filters)

        assert len(result.sessions) == 2
        assert result.total_count >= 5

    @pytest.mark.unit
    def test_filters_applied_tracking(self, db_session, analytics_user):
        _create_session(db_session, analytics_user.id)
        svc = AnalyticsService(db_session)
        filters = AnalyticsFilter(role="Developer", session_status="completed")
        result = svc.get_filtered_sessions(str(analytics_user.id), filters)

        assert "role" in result.filters_applied
        assert "session_status" in result.filters_applied


# ---------------------------------------------------------------------------
# Performance Heatmap
# ---------------------------------------------------------------------------

class TestPerformanceHeatmap:
    """Tests for get_performance_heatmap."""

    @pytest.mark.unit
    def test_heatmap_structure(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=3)
        svc = AnalyticsService(db_session)
        heatmap = svc.get_performance_heatmap(str(analytics_user.id), "30d")

        assert heatmap.user_id == str(analytics_user.id)
        assert heatmap.time_period == "30d"
        # 7 days * 24 hours = 168 cells
        assert len(heatmap.cells) == 168
        assert isinstance(heatmap.peak_day, str)
        assert 0 <= heatmap.peak_hour <= 23
        assert heatmap.total_sessions == 3

    @pytest.mark.unit
    def test_heatmap_no_sessions(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        heatmap = svc.get_performance_heatmap(str(analytics_user.id), "30d")

        assert heatmap.total_sessions == 0
        assert all(c.session_count == 0 for c in heatmap.cells)

    @pytest.mark.unit
    def test_heatmap_cell_fields(self, db_session, analytics_user):
        _create_session(db_session, analytics_user.id)
        svc = AnalyticsService(db_session)
        heatmap = svc.get_performance_heatmap(str(analytics_user.id), "30d")

        for cell in heatmap.cells:
            assert 0 <= cell.day_of_week <= 6
            assert 0 <= cell.hour <= 23
            assert cell.session_count >= 0
            assert cell.average_score >= 0


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Tests for generate_report and generate_csv_report."""

    @pytest.mark.unit
    def test_generate_report(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=3)
        svc = AnalyticsService(db_session)

        request = ReportRequest(
            user_id=str(analytics_user.id),
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            report_type=ReportType.DETAILED,
        )
        report = svc.generate_report(request)

        assert report.user_id == str(analytics_user.id)
        assert report.report_type == "detailed"
        assert report.performance_metrics.total_sessions >= 0
        assert isinstance(report.recommendations, list)
        assert isinstance(report.sessions, list)

    @pytest.mark.unit
    def test_generate_csv_report(self, db_session, analytics_user):
        _create_sessions_over_time(db_session, analytics_user.id, count=2)
        svc = AnalyticsService(db_session)

        request = ReportRequest(
            user_id=str(analytics_user.id),
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            report_type=ReportType.PERFORMANCE,
            format=ReportFormat.CSV,
        )
        csv_string = svc.generate_csv_report(request)

        assert isinstance(csv_string, str)
        assert "Confida Analytics Report" in csv_string
        assert "Performance Summary" in csv_string

    @pytest.mark.unit
    def test_report_with_no_sessions(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        request = ReportRequest(
            user_id=str(analytics_user.id),
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow(),
            report_type=ReportType.SUMMARY,
        )
        report = svc.generate_report(request)
        assert report.performance_metrics.total_sessions == 0


# ---------------------------------------------------------------------------
# Goal Management
# ---------------------------------------------------------------------------

class TestGoalManagement:
    """Tests for CRUD goal operations."""

    @pytest.mark.unit
    def test_create_goal(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        goal_data = UserGoalCreate(
            title="Score above 8",
            goal_type=GoalType.SCORE,
            target_value=8.0,
        )
        goal = svc.create_goal(str(analytics_user.id), goal_data)

        assert goal.title == "Score above 8"
        assert goal.goal_type == "score"
        assert goal.target_value == 8.0
        assert goal.current_value == 0.0
        assert goal.status == "active"
        assert goal.progress_percentage == 0.0

    @pytest.mark.unit
    def test_list_goals(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Goal A", goal_type=GoalType.SESSIONS, target_value=10
        ))
        svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Goal B", goal_type=GoalType.SCORE, target_value=9
        ))

        goals = svc.list_goals(str(analytics_user.id))
        assert len(goals) >= 2

    @pytest.mark.unit
    def test_list_goals_with_status_filter(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Active Goal", goal_type=GoalType.SCORE, target_value=8
        ))

        active_goals = svc.list_goals(str(analytics_user.id), status_filter="active")
        assert all(g.status == "active" for g in active_goals)

    @pytest.mark.unit
    def test_get_goal(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        created = svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Find Me", goal_type=GoalType.STREAK, target_value=5
        ))

        goal = svc.get_goal(str(analytics_user.id), created.id)
        assert goal is not None
        assert goal.title == "Find Me"

    @pytest.mark.unit
    def test_get_goal_not_found(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        goal = svc.get_goal(str(analytics_user.id), str(uuid.uuid4()))
        assert goal is None

    @pytest.mark.unit
    def test_update_goal(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        created = svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Original", goal_type=GoalType.SCORE, target_value=7
        ))

        updated = svc.update_goal(
            str(analytics_user.id),
            created.id,
            UserGoalUpdate(title="Updated Title", target_value=9.0)
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.target_value == 9.0

    @pytest.mark.unit
    def test_update_goal_status(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        created = svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Cancel Me", goal_type=GoalType.SCORE, target_value=7
        ))

        updated = svc.update_goal(
            str(analytics_user.id),
            created.id,
            UserGoalUpdate(status=GoalStatus.CANCELLED)
        )

        assert updated.status == "cancelled"

    @pytest.mark.unit
    def test_delete_goal(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        created = svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Delete Me", goal_type=GoalType.SCORE, target_value=5
        ))

        deleted = svc.delete_goal(str(analytics_user.id), created.id)
        assert deleted is True

        # Confirm it's gone
        assert svc.get_goal(str(analytics_user.id), created.id) is None

    @pytest.mark.unit
    def test_delete_goal_not_found(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        deleted = svc.delete_goal(str(analytics_user.id), str(uuid.uuid4()))
        assert deleted is False

    @pytest.mark.unit
    def test_goal_progress_percentage(self, db_session, analytics_user):
        """Test that progress percentage is correctly calculated.
        
        Since get_goal refreshes progress from live session data, we create
        sessions so the average score matches a known value against the target.
        """
        # Create sessions with average score ~5.0
        _create_session(db_session, analytics_user.id, overall_score={"overall": 5.0})

        svc = AnalyticsService(db_session)
        created = svc.create_goal(str(analytics_user.id), UserGoalCreate(
            title="Half Done", goal_type=GoalType.SCORE, target_value=10
        ))

        goal = svc.get_goal(str(analytics_user.id), created.id)
        # average_score ~5.0, target_value=10 → progress ~50%
        assert goal.progress_percentage == pytest.approx(50.0, abs=5.0)

    @pytest.mark.unit
    def test_create_dimension_goal(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        goal_data = UserGoalCreate(
            title="Improve Communication",
            goal_type=GoalType.DIMENSION_SCORE,
            target_value=9.0,
            dimension="communication",
        )
        goal = svc.create_goal(str(analytics_user.id), goal_data)
        assert goal.dimension == "communication"
        assert goal.goal_type == "dimension_score"


# ---------------------------------------------------------------------------
# Analytics Event Logging
# ---------------------------------------------------------------------------

class TestAnalyticsEventLogging:
    """Tests for _log_analytics_event."""

    @pytest.mark.unit
    def test_log_event_does_not_raise(self, db_session, analytics_user):
        svc = AnalyticsService(db_session)
        # Should not raise
        svc._log_analytics_event(
            user_id=str(analytics_user.id),
            event_type="test_event",
            event_data={"key": "value"}
        )


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class TestRecommendations:
    """Tests for _generate_recommendations."""

    @pytest.mark.unit
    def test_low_score_recommendation(self, db_session):
        svc = AnalyticsService(db_session)
        metrics = svc._create_empty_metrics("30d")
        metrics.average_score = 4.0
        metrics.total_sessions = 10
        recs = svc._generate_recommendations(metrics)
        assert any("score" in r.lower() for r in recs)

    @pytest.mark.unit
    def test_low_completion_recommendation(self, db_session):
        svc = AnalyticsService(db_session)
        metrics = svc._create_empty_metrics("30d")
        metrics.completion_rate = 50.0
        metrics.total_sessions = 10
        recs = svc._generate_recommendations(metrics)
        assert any("complete" in r.lower() for r in recs)

    @pytest.mark.unit
    def test_few_sessions_recommendation(self, db_session):
        svc = AnalyticsService(db_session)
        metrics = svc._create_empty_metrics("30d")
        metrics.total_sessions = 2
        recs = svc._generate_recommendations(metrics)
        assert any("more" in r.lower() for r in recs)

    @pytest.mark.unit
    def test_good_performance_recommendation(self, db_session):
        svc = AnalyticsService(db_session)
        metrics = svc._create_empty_metrics("30d")
        metrics.average_score = 9.0
        metrics.completion_rate = 95.0
        metrics.total_sessions = 20
        metrics.improvement_trend = 2.0
        recs = svc._generate_recommendations(metrics)
        assert any("great" in r.lower() or "keep" in r.lower() for r in recs)
