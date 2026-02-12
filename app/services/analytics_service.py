"""
Unified Analytics Service for Confida

This service combines comprehensive analytics functionality with simplified aggregation
capabilities, eliminating the need for separate AnalyticsService and SimplifiedAnalyticsService classes.
"""
import uuid
import io
import csv
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from app.database.models import (
    InterviewSession, Question, Answer, User, AnalyticsEvent,
    UserPerformance, SessionQuestion, UserGoal
)
from app.models.analytics_models import (
    PerformanceMetrics, SessionAnalytics, TrendAnalysis, ReportRequest, 
    ReportResponse, AnalyticsSummary, PerformanceComparison, AnalyticsFilter,
    TimePeriod, TrendDirection, ReportType, DimensionScore, DimensionProgress,
    SessionComparisonResponse, UserGoalCreate, UserGoalUpdate, UserGoalResponse,
    GoalStatus, GoalType, FilteredSessionsResponse, HeatmapCell, PerformanceHeatmap
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AnalyticsConstants:
    """Constants for analytics calculations."""
    TREND_THRESHOLD = 5.0
    LOW_SCORE_THRESHOLD = 6.0
    LOW_COMPLETION_RATE_THRESHOLD = 80.0
    CONFIDENCE_DIVISOR = 10.0
    
    # Time period mappings
    TIME_PERIOD_DAYS = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "1y": 365
    }


def handle_analytics_errors(operation_name: str):
    """Decorator for consistent error handling in analytics operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}")
                raise
        return wrapper
    return decorator


class AnalyticsService:
    """Unified service for analytics and reporting functionality with both comprehensive and simplified modes."""
    
    def __init__(self, db: Session):
        self.db = db
        self.aggregator = None
    
    # -------------------------------------------------------------------------
    # Score extraction helpers (handles JSONB score fields)
    # -------------------------------------------------------------------------
    
    def _extract_score_value(self, score) -> Optional[float]:
        """Extract a single numeric score from a JSONB score field.
        
        Handles multiple formats: plain number, dict with 'overall'/'average'/'score'/'total' key.
        """
        if score is None:
            return None
        if isinstance(score, (int, float)):
            return float(score)
        if isinstance(score, dict):
            for key in ("overall", "average", "score", "total"):
                if key in score and isinstance(score[key], (int, float)):
                    return float(score[key])
        return None
    
    def _extract_dimension_scores(self, score) -> Dict[str, float]:
        """Extract per-dimension scores from a JSONB score field.
        
        Returns a dict of dimension_name -> numeric score, excluding meta keys.
        """
        if not isinstance(score, dict):
            return {}
        
        meta_keys = {"overall", "average", "score", "total", "grade", "tier"}
        result = {}
        for key, value in score.items():
            if key.lower() in meta_keys:
                continue
            if isinstance(value, (int, float)):
                result[key] = float(value)
            elif isinstance(value, dict):
                # Nested dimension: try to extract its score
                inner = self._extract_score_value(value)
                if inner is not None:
                    result[key] = inner
        return result
    
    # -------------------------------------------------------------------------
    # Database query helpers
    # -------------------------------------------------------------------------
    
    def _get_session_answers(self, session_id) -> List[Answer]:
        """Get all answers for a session via SessionQuestion join."""
        session_question_ids = self.db.query(SessionQuestion.question_id).filter(
            SessionQuestion.session_id == session_id
        ).all()
        question_ids = [sq[0] for sq in session_question_ids]
        if not question_ids:
            return []
        return self.db.query(Answer).filter(Answer.question_id.in_(question_ids)).all()
    
    def _get_session_questions(self, session_id) -> List[Question]:
        """Get all questions for a session via SessionQuestion join."""
        session_question_ids = self.db.query(SessionQuestion.question_id).filter(
            SessionQuestion.session_id == session_id
        ).all()
        question_ids = [sq[0] for sq in session_question_ids]
        if not question_ids:
            return []
        return self.db.query(Question).filter(Question.id.in_(question_ids)).all()
    
    def _get_user_sessions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[InterviewSession]:
        """Get user sessions within date range."""
        query = self.db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
        
        if start_date:
            query = query.filter(InterviewSession.created_at >= start_date)
        if end_date:
            query = query.filter(InterviewSession.created_at <= end_date)
            
        return query.order_by(InterviewSession.created_at).all()
    
    def _create_empty_metrics(self, time_period: str) -> PerformanceMetrics:
        """Create empty metrics for when no sessions exist."""
        return PerformanceMetrics(
            total_sessions=0,
            average_score=0.0,
            improvement_trend=0.0,
            strongest_areas=[],
            improvement_areas=[],
            time_period=time_period,
            completion_rate=0.0,
            total_questions_answered=0,
            average_response_time=0.0
        )
    
    def _calculate_average_score_from_answers(self, answers: List[Answer]) -> float:
        """Calculate average score from a list of answers, handling JSONB score fields."""
        scores = []
        for answer in answers:
            val = self._extract_score_value(answer.score)
            if val is not None:
                scores.append(val)
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_completion_time(self, session: InterviewSession) -> int:
        """Calculate session completion time in seconds."""
        if session.updated_at and session.created_at:
            return int((session.updated_at - session.created_at).total_seconds())
        return 0
    
    def _calculate_difficulty_distribution(self, questions: List[Question]) -> Dict[str, int]:
        """Calculate difficulty distribution using Counter."""
        difficulties = [q.difficulty_level or "medium" for q in questions]
        return dict(Counter(difficulties))
    
    def _calculate_category_scores(self, answers: List[Answer]) -> Dict[str, float]:
        """Calculate category scores using defaultdict."""
        category_scores = defaultdict(list)
        
        for answer in answers:
            val = self._extract_score_value(answer.score)
            if val is None:
                continue
            # Get question category
            if answer.question_id:
                question = self.db.query(Question).filter(Question.id == answer.question_id).first()
                category = question.category if question else "general"
            else:
                category = "general"
            category_scores[category].append(val)
        
        return {
            category: sum(scores) / len(scores)
            for category, scores in category_scores.items()
        }
    
    def _calculate_start_date(self, end_date: datetime, time_period: str) -> datetime:
        """Calculate start date based on time period."""
        days = AnalyticsConstants.TIME_PERIOD_DAYS.get(time_period, 30)
        return end_date - timedelta(days=days)
    
    def _time_period_from_dates(self, start_date: datetime, end_date: datetime) -> str:
        """Derive a human-readable time period string from date range."""
        days = (end_date - start_date).days
        if days <= 7:
            return "7d"
        elif days <= 30:
            return "30d"
        elif days <= 90:
            return "90d"
        return "1y"
    
    # -------------------------------------------------------------------------
    # Analytics event logging
    # -------------------------------------------------------------------------
    
    def _log_analytics_event(self, user_id: str, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> None:
        """Log an analytics event to the AnalyticsEvent table."""
        try:
            event = AnalyticsEvent(
                user_id=user_id,
                event_type=event_type,
                event_data=event_data or {}
            )
            self.db.add(event)
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to log analytics event '{event_type}' for user {user_id}: {e}")
            self.db.rollback()
    
    # -------------------------------------------------------------------------
    # Core metric calculations
    # -------------------------------------------------------------------------
    
    def _calculate_basic_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate basic session metrics."""
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == "completed"])
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        total_questions = sum(s.total_questions or 0 for s in sessions)
        total_time = sum(self._calculate_completion_time(s) for s in sessions)
        average_response_time = total_time / total_questions if total_questions > 0 else 0
        
        return {
            "total_sessions": total_sessions,
            "completion_rate": completion_rate,
            "total_questions_answered": total_questions,
            "average_response_time": average_response_time
        }
    
    def _calculate_score_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate score-related metrics from session overall_score (JSONB)."""
        all_scores = []
        category_totals = defaultdict(list)
        
        for session in sessions:
            val = self._extract_score_value(session.overall_score)
            if val is not None:
                all_scores.append(val)
            
            dims = self._extract_dimension_scores(session.overall_score)
            for dim, score in dims.items():
                category_totals[dim].append(score)
        
        if not all_scores:
            return {
                "average_score": 0.0,
                "strongest_areas": [],
                "improvement_areas": []
            }
        
        average_score = sum(all_scores) / len(all_scores)
        
        category_averages = {
            cat: sum(scores) / len(scores)
            for cat, scores in category_totals.items()
        }
        
        sorted_categories = sorted(category_averages.items(), key=lambda x: x[1], reverse=True)
        strongest_areas = [cat for cat, _score in sorted_categories[:3]]
        improvement_areas = [cat for cat, _score in sorted_categories[-3:]]
        
        return {
            "average_score": average_score,
            "strongest_areas": strongest_areas,
            "improvement_areas": improvement_areas
        }
    
    def _calculate_trend_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate trend metrics by comparing first and second half of sessions."""
        if len(sessions) < 2:
            return {"improvement_trend": 0.0}
        
        sorted_sessions = sorted(sessions, key=lambda s: s.created_at)
        mid_point = len(sorted_sessions) // 2
        first_half = sorted_sessions[:mid_point]
        second_half = sorted_sessions[mid_point:]
        
        first_half_scores = []
        second_half_scores = []
        
        for session in first_half:
            val = self._extract_score_value(session.overall_score)
            if val is not None:
                first_half_scores.append(val)
        
        for session in second_half:
            val = self._extract_score_value(session.overall_score)
            if val is not None:
                second_half_scores.append(val)
        
        if not first_half_scores or not second_half_scores:
            return {"improvement_trend": 0.0}
        
        first_avg = sum(first_half_scores) / len(first_half_scores)
        second_avg = sum(second_half_scores) / len(second_half_scores)
        
        return {"improvement_trend": second_avg - first_avg}
    
    def _calculate_performance_metrics(self, sessions: List[InterviewSession], time_period: str) -> PerformanceMetrics:
        """Calculate performance metrics from a list of sessions."""
        if not sessions:
            return self._create_empty_metrics(time_period)
        
        basic_metrics = self._calculate_basic_metrics(sessions)
        score_metrics = self._calculate_score_metrics(sessions)
        trend_metrics = self._calculate_trend_metrics(sessions)
        
        return PerformanceMetrics(
            total_sessions=basic_metrics["total_sessions"],
            average_score=score_metrics["average_score"],
            improvement_trend=trend_metrics["improvement_trend"],
            strongest_areas=score_metrics["strongest_areas"],
            improvement_areas=score_metrics["improvement_areas"],
            time_period=time_period,
            completion_rate=basic_metrics["completion_rate"],
            total_questions_answered=basic_metrics["total_questions_answered"],
            average_response_time=basic_metrics["average_response_time"]
        )
    
    # -------------------------------------------------------------------------
    # Public API: Performance Metrics
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("getting performance metrics")
    def get_performance_metrics(self, user_id: str, time_period: str = "30d") -> PerformanceMetrics:
        """Get performance metrics for a user."""
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(end_date, time_period)
        sessions = self._get_user_sessions(user_id, start_date, end_date)
        
        if not sessions:
            return self._create_empty_metrics(time_period)
        
        return self._calculate_performance_metrics(sessions, time_period)
    
    # -------------------------------------------------------------------------
    # Public API: Trend Analysis
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("getting trend analysis")
    def get_trend_analysis(self, user_id: str, metric: str = "average_score", time_period: str = "30d") -> TrendAnalysis:
        """Get trend analysis for a specific metric over a time period.
        
        Supported metrics: average_score, completion_rate, total_sessions, response_time.
        """
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(end_date, time_period)
        sessions = self._get_user_sessions(user_id, start_date, end_date)
        
        if not sessions:
            return TrendAnalysis(
                metric=metric,
                time_period=time_period,
                data_points=[],
                trend_direction=TrendDirection.STABLE,
                trend_percentage=0.0,
                confidence_level=0.0
            )
        
        # Build data points grouped by date
        daily_data = defaultdict(list)
        for session in sessions:
            date_key = session.created_at.date().isoformat()
            
            if metric == "average_score":
                val = self._extract_score_value(session.overall_score)
                if val is not None:
                    daily_data[date_key].append(val)
            elif metric == "completion_rate":
                daily_data[date_key].append(1.0 if session.status == "completed" else 0.0)
            elif metric == "total_sessions":
                daily_data[date_key].append(1.0)
            elif metric == "response_time":
                ct = self._calculate_completion_time(session)
                questions = session.total_questions or 1
                daily_data[date_key].append(ct / questions if questions > 0 else 0.0)
        
        # Aggregate daily data
        data_points = []
        for date_key in sorted(daily_data.keys()):
            values = daily_data[date_key]
            if metric == "total_sessions":
                agg_value = sum(values)
            else:
                agg_value = sum(values) / len(values) if values else 0.0
            data_points.append({"date": date_key, "value": round(agg_value, 2)})
        
        # Calculate trend direction and percentage
        trend_direction, trend_percentage = self._compute_trend(data_points)
        
        # Confidence based on number of data points
        confidence_level = min(len(data_points) / AnalyticsConstants.CONFIDENCE_DIVISOR, 1.0)
        
        return TrendAnalysis(
            metric=metric,
            time_period=time_period,
            data_points=data_points,
            trend_direction=trend_direction,
            trend_percentage=round(trend_percentage, 2),
            confidence_level=round(confidence_level, 2)
        )
    
    def _compute_trend(self, data_points: List[Dict[str, Any]]) -> Tuple[TrendDirection, float]:
        """Compute trend direction and percentage from time-series data points."""
        if len(data_points) < 2:
            return TrendDirection.STABLE, 0.0
        
        mid = len(data_points) // 2
        first_half = data_points[:mid]
        second_half = data_points[mid:]
        
        first_avg = sum(p["value"] for p in first_half) / len(first_half)
        second_avg = sum(p["value"] for p in second_half) / len(second_half)
        
        if first_avg == 0:
            if second_avg > 0:
                return TrendDirection.UP, 100.0
            return TrendDirection.STABLE, 0.0
        
        pct_change = ((second_avg - first_avg) / abs(first_avg)) * 100
        
        if pct_change > AnalyticsConstants.TREND_THRESHOLD:
            return TrendDirection.UP, pct_change
        elif pct_change < -AnalyticsConstants.TREND_THRESHOLD:
            return TrendDirection.DOWN, abs(pct_change)
        return TrendDirection.STABLE, abs(pct_change)
    
    # -------------------------------------------------------------------------
    # Public API: Session Analytics (list for a user with pagination)
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("getting session analytics")
    def get_session_analytics(self, user_id: str, limit: int = 10, offset: int = 0) -> List[SessionAnalytics]:
        """Get paginated session analytics for a user."""
        sessions = (
            self.db.query(InterviewSession)
            .filter(InterviewSession.user_id == user_id)
            .order_by(desc(InterviewSession.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        result = []
        for session in sessions:
            questions = self._get_session_questions(session.id)
            answers = self._get_session_answers(session.id)
            
            avg_score = self._extract_score_value(session.overall_score) or 0.0
            completion_time = self._calculate_completion_time(session)
            difficulty_dist = self._calculate_difficulty_distribution(questions)
            cat_scores = self._calculate_category_scores(answers)
            
            result.append(SessionAnalytics(
                session_id=str(session.id),
                user_id=str(session.user_id),
                role=session.role or "unknown",
                total_questions=session.total_questions or 0,
                answered_questions=session.completed_questions or 0,
                average_score=avg_score,
                completion_time=completion_time,
                created_at=session.created_at,
                status=session.status or "unknown",
                difficulty_distribution=difficulty_dist,
                category_scores=cat_scores
            ))
        
        return result
    
    # -------------------------------------------------------------------------
    # Public API: Analytics Summary
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("getting analytics summary")
    def get_analytics_summary(self, user_id: str, time_period: str = "30d") -> AnalyticsSummary:
        """Get a concise analytics summary matching the AnalyticsSummary schema."""
        metrics = self.get_performance_metrics(user_id, time_period)
        
        # Recent activity
        recent_sessions = (
            self.db.query(InterviewSession)
            .filter(InterviewSession.user_id == user_id)
            .order_by(desc(InterviewSession.created_at))
            .limit(5)
            .all()
        )
        
        recent_activity = [
            {
                "session_id": str(s.id),
                "role": s.role,
                "status": s.status,
                "score": self._extract_score_value(s.overall_score),
                "date": s.created_at.isoformat() if s.created_at else None
            }
            for s in recent_sessions
        ]
        
        return AnalyticsSummary(
            total_sessions=metrics.total_sessions,
            average_score=metrics.average_score,
            improvement_trend=metrics.improvement_trend,
            completion_rate=metrics.completion_rate,
            top_performing_areas=metrics.strongest_areas,
            areas_for_improvement=metrics.improvement_areas,
            recent_activity=recent_activity
        )
    
    # -------------------------------------------------------------------------
    # Public API: Performance Comparison
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("comparing performance")
    def get_performance_comparison(
        self,
        user_id: str,
        current_period: str = "30d",
        previous_period: str = "30d"
    ) -> PerformanceComparison:
        """Compare performance between a current period and the equivalent previous period.
        
        For example, current_period='30d' compares the last 30 days against the 30 days before that.
        """
        end_date = datetime.utcnow()
        current_start = self._calculate_start_date(end_date, current_period)
        
        # Previous period ends where current starts
        previous_end = current_start
        previous_days = AnalyticsConstants.TIME_PERIOD_DAYS.get(previous_period, 30)
        previous_start = previous_end - timedelta(days=previous_days)
        
        current_sessions = self._get_user_sessions(user_id, current_start, end_date)
        previous_sessions = self._get_user_sessions(user_id, previous_start, previous_end)
        
        current_metrics = self._calculate_performance_metrics(current_sessions, current_period)
        previous_metrics = self._calculate_performance_metrics(previous_sessions, previous_period)
        
        # Overall improvement
        if previous_metrics.average_score > 0:
            improvement_pct = (
                (current_metrics.average_score - previous_metrics.average_score)
                / previous_metrics.average_score * 100
            )
        else:
            improvement_pct = 0.0 if current_metrics.average_score == 0 else 100.0
        
        # Per-area comparisons
        all_areas = set(current_metrics.strongest_areas + current_metrics.improvement_areas +
                        previous_metrics.strongest_areas + previous_metrics.improvement_areas)
        
        area_comparisons: Dict[str, Dict[str, float]] = {}
        current_dims = self._aggregate_dimension_scores(current_sessions)
        previous_dims = self._aggregate_dimension_scores(previous_sessions)
        
        for area in all_areas:
            curr_val = current_dims.get(area, 0.0)
            prev_val = previous_dims.get(area, 0.0)
            area_comparisons[area] = {
                "current": round(curr_val, 2),
                "previous": round(prev_val, 2),
                "delta": round(curr_val - prev_val, 2)
            }
        
        return PerformanceComparison(
            current_period=current_metrics,
            previous_period=previous_metrics,
            improvement_percentage=round(improvement_pct, 2),
            area_comparisons=area_comparisons
        )
    
    def _aggregate_dimension_scores(self, sessions: List[InterviewSession]) -> Dict[str, float]:
        """Average dimension scores across a set of sessions."""
        dim_totals = defaultdict(list)
        for session in sessions:
            dims = self._extract_dimension_scores(session.overall_score)
            for dim, score in dims.items():
                dim_totals[dim].append(score)
        return {
            dim: sum(scores) / len(scores)
            for dim, scores in dim_totals.items()
        }
    
    # -------------------------------------------------------------------------
    # Public API: Report Generation
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("generating report")
    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate a comprehensive analytics report."""
        time_period = self._time_period_from_dates(request.start_date, request.end_date)
        
        # Get performance metrics for the date range
        sessions = self._get_user_sessions(request.user_id, request.start_date, request.end_date)
        metrics = self._calculate_performance_metrics(sessions, time_period)
        
        # Trend analysis (if requested)
        trend = None
        if request.include_trends:
            trend = self.get_trend_analysis(request.user_id, "average_score", time_period)
        
        # Session analytics
        session_analytics = []
        for session in sessions[:50]:  # Cap at 50 sessions per report
            questions = self._get_session_questions(session.id)
            answers = self._get_session_answers(session.id)
            
            avg_score = self._extract_score_value(session.overall_score) or 0.0
            completion_time = self._calculate_completion_time(session)
            
            session_analytics.append(SessionAnalytics(
                session_id=str(session.id),
                user_id=str(session.user_id),
                role=session.role or "unknown",
                total_questions=session.total_questions or 0,
                answered_questions=session.completed_questions or 0,
                average_score=avg_score,
                completion_time=completion_time,
                created_at=session.created_at,
                status=session.status or "unknown",
                difficulty_distribution=self._calculate_difficulty_distribution(questions),
                category_scores=self._calculate_category_scores(answers)
            ))
        
        # Recommendations
        recommendations = []
        if request.include_recommendations:
            recommendations = self._generate_recommendations(metrics)
        
        return ReportResponse(
            report_id=str(uuid.uuid4()),
            user_id=request.user_id,
            report_type=request.report_type.value,
            generated_at=datetime.utcnow(),
            time_period=time_period,
            performance_metrics=metrics,
            trend_analysis=trend,
            sessions=session_analytics,
            recommendations=recommendations,
            export_url=None
        )
    
    def _generate_recommendations(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate improvement recommendations based on performance metrics."""
        recommendations = []
        
        if metrics.average_score < AnalyticsConstants.LOW_SCORE_THRESHOLD:
            recommendations.append(
                "Your average score is below target. Focus on structured responses using the STAR method."
            )
        
        if metrics.completion_rate < AnalyticsConstants.LOW_COMPLETION_RATE_THRESHOLD:
            recommendations.append(
                "Try to complete more sessions fully to get the most out of your practice."
            )
        
        if metrics.improvement_trend < 0:
            recommendations.append(
                "Your scores have been declining recently. Consider reviewing feedback from past sessions."
            )
        
        if metrics.improvement_areas:
            areas = ", ".join(metrics.improvement_areas[:3])
            recommendations.append(f"Focus on improving these areas: {areas}.")
        
        if metrics.total_sessions < 5:
            recommendations.append(
                "Complete more practice sessions to build confidence and track meaningful progress."
            )
        
        if not recommendations:
            recommendations.append("Great work! Keep up the consistent practice to maintain your performance.")
        
        return recommendations
    
    def generate_csv_report(self, request: ReportRequest) -> str:
        """Generate a CSV-formatted report string."""
        report = self.generate_report(request)
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Confida Analytics Report"])
        writer.writerow(["Generated", report.generated_at.isoformat()])
        writer.writerow(["Time Period", report.time_period])
        writer.writerow([])
        
        # Performance summary
        writer.writerow(["Performance Summary"])
        writer.writerow(["Total Sessions", report.performance_metrics.total_sessions])
        writer.writerow(["Average Score", f"{report.performance_metrics.average_score:.2f}"])
        writer.writerow(["Completion Rate", f"{report.performance_metrics.completion_rate:.1f}%"])
        writer.writerow(["Improvement Trend", f"{report.performance_metrics.improvement_trend:+.2f}"])
        writer.writerow([])
        
        # Session details
        writer.writerow(["Session Details"])
        writer.writerow(["Session ID", "Role", "Score", "Status", "Questions", "Answered", "Duration (s)", "Date"])
        for s in report.sessions:
            writer.writerow([
                s.session_id, s.role, f"{s.average_score:.2f}", s.status,
                s.total_questions, s.answered_questions, s.completion_time,
                s.created_at.isoformat()
            ])
        writer.writerow([])
        
        # Recommendations
        writer.writerow(["Recommendations"])
        for rec in report.recommendations:
            writer.writerow([rec])
        
        return output.getvalue()
    
    # -------------------------------------------------------------------------
    # Public API: Dimension Progress Tracking
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("getting dimension progress")
    def get_dimension_progress(self, user_id: str, time_period: str = "30d") -> DimensionProgress:
        """Get progress tracking across all scoring dimensions."""
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(end_date, time_period)
        sessions = self._get_user_sessions(user_id, start_date, end_date)
        
        # Aggregate dimension scores
        dim_all = defaultdict(list)
        time_series = []
        
        for session in sessions:
            dims = self._extract_dimension_scores(session.overall_score)
            if dims:
                point = {"date": session.created_at.isoformat()}
                for dim, score in dims.items():
                    dim_all[dim].append(score)
                    point[dim] = score
                time_series.append(point)
        
        # Build DimensionScore list with per-dimension trends
        dimension_scores = []
        for dim, scores in dim_all.items():
            avg = sum(scores) / len(scores)
            # Compute trend for this dimension
            if len(scores) >= 2:
                mid = len(scores) // 2
                first_avg = sum(scores[:mid]) / mid
                second_avg = sum(scores[mid:]) / (len(scores) - mid)
                delta = second_avg - first_avg
                pct = (delta / abs(first_avg) * 100) if first_avg != 0 else 0.0
                if pct > AnalyticsConstants.TREND_THRESHOLD:
                    direction = TrendDirection.UP
                elif pct < -AnalyticsConstants.TREND_THRESHOLD:
                    direction = TrendDirection.DOWN
                else:
                    direction = TrendDirection.STABLE
            else:
                direction = TrendDirection.STABLE
                pct = 0.0
            
            dimension_scores.append(DimensionScore(
                dimension=dim,
                score=round(avg, 2),
                trend=direction,
                trend_percentage=round(abs(pct), 2)
            ))
        
        # Overall composite score
        overall = (
            sum(d.score for d in dimension_scores) / len(dimension_scores)
            if dimension_scores else 0.0
        )
        
        return DimensionProgress(
            user_id=user_id,
            time_period=time_period,
            dimensions=dimension_scores,
            overall_score=round(overall, 2),
            data_points=time_series,
            last_updated=datetime.utcnow()
        )
    
    # -------------------------------------------------------------------------
    # Public API: Session Comparison
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("comparing sessions")
    def compare_sessions(self, user_id: str, session_id_a: str, session_id_b: str) -> SessionComparisonResponse:
        """Compare two interview sessions side-by-side."""
        session_a = self.db.query(InterviewSession).filter(
            InterviewSession.id == session_id_a,
            InterviewSession.user_id == user_id
        ).first()
        session_b = self.db.query(InterviewSession).filter(
            InterviewSession.id == session_id_b,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session_a or not session_b:
            raise ValueError("One or both sessions not found for this user")
        
        def build_session_analytics(session: InterviewSession) -> SessionAnalytics:
            questions = self._get_session_questions(session.id)
            answers = self._get_session_answers(session.id)
            return SessionAnalytics(
                session_id=str(session.id),
                user_id=str(session.user_id),
                role=session.role or "unknown",
                total_questions=session.total_questions or 0,
                answered_questions=session.completed_questions or 0,
                average_score=self._extract_score_value(session.overall_score) or 0.0,
                completion_time=self._calculate_completion_time(session),
                created_at=session.created_at,
                status=session.status or "unknown",
                difficulty_distribution=self._calculate_difficulty_distribution(questions),
                category_scores=self._calculate_category_scores(answers)
            )
        
        analytics_a = build_session_analytics(session_a)
        analytics_b = build_session_analytics(session_b)
        
        score_delta = analytics_b.average_score - analytics_a.average_score
        
        # Category deltas
        all_cats = set(list(analytics_a.category_scores.keys()) + list(analytics_b.category_scores.keys()))
        category_deltas = {}
        for cat in all_cats:
            a_val = analytics_a.category_scores.get(cat, 0.0)
            b_val = analytics_b.category_scores.get(cat, 0.0)
            category_deltas[cat] = round(b_val - a_val, 2)
        
        # Summary
        if score_delta > 0:
            summary = f"Session B scored {score_delta:.1f} points higher than Session A, showing improvement."
        elif score_delta < 0:
            summary = f"Session A scored {abs(score_delta):.1f} points higher than Session B."
        else:
            summary = "Both sessions achieved the same overall score."
        
        improved = [c for c, d in category_deltas.items() if d > 0]
        declined = [c for c, d in category_deltas.items() if d < 0]
        if improved:
            summary += f" Improved in: {', '.join(improved)}."
        if declined:
            summary += f" Declined in: {', '.join(declined)}."
        
        return SessionComparisonResponse(
            session_a=analytics_a,
            session_b=analytics_b,
            score_delta=round(score_delta, 2),
            category_deltas=category_deltas,
            improvement_summary=summary
        )
    
    # -------------------------------------------------------------------------
    # Public API: Goal Management
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("creating goal")
    def create_goal(self, user_id: str, goal_data: UserGoalCreate) -> UserGoalResponse:
        """Create a new user goal."""
        goal = UserGoal(
            user_id=user_id,
            title=goal_data.title,
            description=goal_data.description,
            goal_type=goal_data.goal_type.value,
            target_value=goal_data.target_value,
            current_value=0.0,
            dimension=goal_data.dimension,
            target_date=goal_data.target_date,
            status="active"
        )
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        
        return self._goal_to_response(goal)
    
    @handle_analytics_errors("listing goals")
    def list_goals(self, user_id: str, status_filter: Optional[str] = None) -> List[UserGoalResponse]:
        """List user goals with optional status filter."""
        query = self.db.query(UserGoal).filter(UserGoal.user_id == user_id)
        if status_filter:
            query = query.filter(UserGoal.status == status_filter)
        goals = query.order_by(desc(UserGoal.created_at)).all()
        
        # Refresh current_value for each active goal
        result = []
        for goal in goals:
            if goal.status == "active":
                self._refresh_goal_progress(goal)
            result.append(self._goal_to_response(goal))
        
        return result
    
    @handle_analytics_errors("getting goal")
    def get_goal(self, user_id: str, goal_id: str) -> Optional[UserGoalResponse]:
        """Get a single goal by ID."""
        goal = self.db.query(UserGoal).filter(
            UserGoal.id == goal_id,
            UserGoal.user_id == user_id
        ).first()
        if not goal:
            return None
        
        if goal.status == "active":
            self._refresh_goal_progress(goal)
        
        return self._goal_to_response(goal)
    
    @handle_analytics_errors("updating goal")
    def update_goal(self, user_id: str, goal_id: str, updates: UserGoalUpdate) -> Optional[UserGoalResponse]:
        """Update an existing user goal."""
        goal = self.db.query(UserGoal).filter(
            UserGoal.id == goal_id,
            UserGoal.user_id == user_id
        ).first()
        if not goal:
            return None
        
        if updates.title is not None:
            goal.title = updates.title
        if updates.description is not None:
            goal.description = updates.description
        if updates.target_value is not None:
            goal.target_value = updates.target_value
        if updates.target_date is not None:
            goal.target_date = updates.target_date
        if updates.status is not None:
            goal.status = updates.status.value
        
        self.db.commit()
        self.db.refresh(goal)
        
        return self._goal_to_response(goal)
    
    @handle_analytics_errors("deleting goal")
    def delete_goal(self, user_id: str, goal_id: str) -> bool:
        """Delete a user goal. Returns True if deleted."""
        goal = self.db.query(UserGoal).filter(
            UserGoal.id == goal_id,
            UserGoal.user_id == user_id
        ).first()
        if not goal:
            return False
        self.db.delete(goal)
        self.db.commit()
        return True
    
    def _refresh_goal_progress(self, goal: UserGoal) -> None:
        """Refresh the current_value for an active goal based on actual data."""
        user_id = str(goal.user_id)
        
        try:
            if goal.goal_type == "score":
                metrics = self.get_performance_metrics(user_id, "30d")
                goal.current_value = metrics.average_score
            elif goal.goal_type == "sessions":
                metrics = self.get_performance_metrics(user_id, "30d")
                goal.current_value = float(metrics.total_sessions)
            elif goal.goal_type == "streak":
                # Count consecutive days with sessions
                from app.services.data_aggregator import DataAggregator
                aggregator = DataAggregator(self.db)
                goal.current_value = float(aggregator.get_current_streak(user_id))
            elif goal.goal_type == "completion_rate":
                metrics = self.get_performance_metrics(user_id, "30d")
                goal.current_value = metrics.completion_rate
            elif goal.goal_type == "dimension_score" and goal.dimension:
                progress = self.get_dimension_progress(user_id, "30d")
                for dim in progress.dimensions:
                    if dim.dimension == goal.dimension:
                        goal.current_value = dim.score
                        break
            
            # Auto-complete if target reached
            if goal.current_value >= goal.target_value:
                goal.status = "completed"
            
            # Auto-expire if past target date
            if goal.target_date and datetime.utcnow() > goal.target_date and goal.status == "active":
                goal.status = "expired"
            
            self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to refresh goal progress for goal {goal.id}: {e}")
            self.db.rollback()
    
    def _goal_to_response(self, goal: UserGoal) -> UserGoalResponse:
        """Convert a UserGoal ORM object to a UserGoalResponse."""
        progress_pct = (
            (goal.current_value / goal.target_value * 100)
            if goal.target_value > 0 else 0.0
        )
        
        return UserGoalResponse(
            id=str(goal.id),
            user_id=str(goal.user_id),
            title=goal.title,
            description=goal.description,
            goal_type=goal.goal_type,
            target_value=goal.target_value,
            current_value=goal.current_value,
            progress_percentage=round(min(progress_pct, 100.0), 1),
            dimension=goal.dimension,
            target_date=goal.target_date,
            status=goal.status,
            created_at=goal.created_at,
            updated_at=goal.updated_at
        )
    
    # -------------------------------------------------------------------------
    # Public API: Filtered Session Search
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("filtering sessions")
    def get_filtered_sessions(self, user_id: str, filters: AnalyticsFilter) -> FilteredSessionsResponse:
        """Get session analytics with advanced filtering."""
        query = self.db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
        
        # Apply filters
        if filters.role:
            query = query.filter(InterviewSession.role.ilike(f"%{filters.role}%"))
        if filters.start_date:
            query = query.filter(InterviewSession.created_at >= filters.start_date)
        if filters.end_date:
            query = query.filter(InterviewSession.created_at <= filters.end_date)
        if filters.session_status:
            query = query.filter(InterviewSession.status == filters.session_status)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply score filters in-memory (overall_score is JSONB)
        sessions = query.order_by(desc(InterviewSession.created_at)).all()
        
        if filters.min_score is not None or filters.max_score is not None:
            filtered = []
            for s in sessions:
                score = self._extract_score_value(s.overall_score)
                if score is None:
                    continue
                if filters.min_score is not None and score < filters.min_score:
                    continue
                if filters.max_score is not None and score > filters.max_score:
                    continue
                filtered.append(s)
            sessions = filtered
            total_count = len(sessions)
        
        # Paginate
        paginated = sessions[filters.offset:filters.offset + filters.limit]
        
        # Build session analytics
        result = []
        for session in paginated:
            questions = self._get_session_questions(session.id)
            answers = self._get_session_answers(session.id)
            
            result.append(SessionAnalytics(
                session_id=str(session.id),
                user_id=str(session.user_id),
                role=session.role or "unknown",
                total_questions=session.total_questions or 0,
                answered_questions=session.completed_questions or 0,
                average_score=self._extract_score_value(session.overall_score) or 0.0,
                completion_time=self._calculate_completion_time(session),
                created_at=session.created_at,
                status=session.status or "unknown",
                difficulty_distribution=self._calculate_difficulty_distribution(questions),
                category_scores=self._calculate_category_scores(answers)
            ))
        
        filters_applied = {
            k: v for k, v in {
                "role": filters.role,
                "start_date": filters.start_date.isoformat() if filters.start_date else None,
                "end_date": filters.end_date.isoformat() if filters.end_date else None,
                "min_score": filters.min_score,
                "max_score": filters.max_score,
                "session_status": filters.session_status,
            }.items() if v is not None
        }
        
        return FilteredSessionsResponse(
            sessions=result,
            total_count=total_count,
            filters_applied=filters_applied
        )
    
    # -------------------------------------------------------------------------
    # Public API: Performance Heatmap
    # -------------------------------------------------------------------------
    
    @handle_analytics_errors("generating heatmap")
    def get_performance_heatmap(self, user_id: str, time_period: str = "30d") -> PerformanceHeatmap:
        """Generate a performance heatmap showing activity and scores by day-of-week and hour.
        
        Returns a grid of cells: 7 days x 24 hours, each with session count and average score.
        """
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(end_date, time_period)
        sessions = self._get_user_sessions(user_id, start_date, end_date)
        
        DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Build grid: (day_of_week, hour) -> list of scores
        grid: Dict[tuple, list] = {}
        for dow in range(7):
            for hour in range(24):
                grid[(dow, hour)] = []
        
        for session in sessions:
            if session.created_at:
                dow = session.created_at.weekday()  # 0=Monday
                hour = session.created_at.hour
                score = self._extract_score_value(session.overall_score)
                grid[(dow, hour)].append(score)
        
        # Build cells
        cells = []
        day_counts: Dict[int, int] = defaultdict(int)
        hour_counts: Dict[int, int] = defaultdict(int)
        
        for (dow, hour), scores in grid.items():
            count = len(scores)
            valid_scores = [s for s in scores if s is not None]
            avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
            
            cells.append(HeatmapCell(
                day_of_week=dow,
                hour=hour,
                session_count=count,
                average_score=round(avg, 2)
            ))
            
            day_counts[dow] += count
            hour_counts[hour] += count
        
        # Peak day/hour
        peak_day_idx = max(day_counts, key=day_counts.get) if day_counts else 0
        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0
        
        return PerformanceHeatmap(
            user_id=user_id,
            time_period=time_period,
            cells=cells,
            peak_day=DAY_NAMES[peak_day_idx],
            peak_hour=peak_hour,
            total_sessions=len(sessions),
            last_updated=datetime.utcnow()
        )
    
    # -------------------------------------------------------------------------
    # Simplified / Legacy Compatibility Methods
    # -------------------------------------------------------------------------
    
    def get_user_performance_metrics_simple(self, user_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get user performance metrics using simplified aggregation."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=date_range_days)
        sessions = self._get_user_sessions(user_id, start_date, end_date)
        
        if not sessions:
            return {
                "user_id": user_id,
                "metrics": {"count": 0, "avg_score": 0.0, "max_score": 0.0},
                "time_range": f"{date_range_days} days",
                "execution_time_ms": 0
            }
        
        scores = []
        for session in sessions:
            val = self._extract_score_value(session.overall_score)
            if val is not None:
                scores.append(val)
        
        return {
            "user_id": user_id,
            "metrics": {
                "count": len(sessions),
                "avg_score": sum(scores) / len(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0
            },
            "time_range": f"{date_range_days} days",
            "execution_time_ms": 0
        }
    
    def get_user_performance_metrics(self, user_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        return self.get_user_performance_metrics_simple(user_id, date_range_days)
    
    def get_question_analytics(self, question_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Legacy method for question analytics."""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            return {
                "question_id": question_id,
                "metrics": {"count": 0, "avg_difficulty": 0.0, "avg_response_time": 0.0, "avg_accuracy": 0.0},
                "time_range": f"{date_range_days} days",
                "execution_time_ms": 0
            }
        
        answers = self.db.query(Answer).filter(Answer.question_id == question_id).all()
        
        if not answers:
            return {
                "question_id": question_id,
                "metrics": {"count": 0, "avg_difficulty": 0.0, "avg_response_time": 0.0, "avg_accuracy": 0.0},
                "time_range": f"{date_range_days} days",
                "execution_time_ms": 0
            }
        
        scores = [self._extract_score_value(a.score) for a in answers]
        scores = [s for s in scores if s is not None]
        
        return {
            "question_id": question_id,
            "metrics": {
                "count": len(answers),
                "avg_difficulty": question.difficulty_level or 0.0,
                "avg_response_time": 0.0,
                "avg_accuracy": sum(scores) / len(scores) if scores else 0.0
            },
            "time_range": f"{date_range_days} days",
            "execution_time_ms": 0
        }
