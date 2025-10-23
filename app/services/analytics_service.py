"""
Unified Analytics Service for Confida

This service combines comprehensive analytics functionality with simplified aggregation
capabilities, eliminating the need for separate AnalyticsService and SimplifiedAnalyticsService classes.
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from app.database.models import InterviewSession, Question, Answer, User, AnalyticsEvent, UserPerformance
from app.models.analytics_models import (
    PerformanceMetrics, SessionAnalytics, TrendAnalysis, ReportRequest, 
    ReportResponse, AnalyticsSummary, PerformanceComparison, AnalyticsFilter,
    TimePeriod, TrendDirection, ReportType
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


class UnifiedAnalyticsService:
    """Unified service for analytics and reporting functionality with both comprehensive and simplified modes."""
    
    def __init__(self, db: Session):
        self.db = db
        # Note: Aggregation framework removed - using simplified methods instead
        self.aggregator = None
    
    # Helper methods for database queries
    def _get_session_answers(self, session_id: int) -> List[Answer]:
        """Get all answers for a session."""
        return self.db.query(Answer).filter(Answer.session_id == session_id).all()
    
    def _get_session_questions(self, session_id: int) -> List[Question]:
        """Get all questions for a session."""
        return self.db.query(Question).filter(Question.session_id == session_id).all()
    
    def _get_user_sessions(self, user_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[InterviewSession]:
        """Get user sessions within date range."""
        query = self.db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
        
        if start_date:
            query = query.filter(InterviewSession.created_at >= start_date)
        if end_date:
            query = query.filter(InterviewSession.created_at <= end_date)
            
        return query.all()
    
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
        """Calculate average score from a list of answers."""
        scores = [answer.score for answer in answers if answer.score is not None]
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
            if answer.question and answer.score is not None:
                category = answer.question.category or "general"
                category_scores[category].append(answer.score)
        
        # Calculate averages
        return {
            category: sum(scores) / len(scores)
            for category, scores in category_scores.items()
        }
    
    # Comprehensive Analytics Methods
    @handle_analytics_errors("getting performance metrics")
    def get_performance_metrics(self, user_id: str, time_period: str = "30d") -> PerformanceMetrics:
        """Get performance metrics for a user."""
        # Calculate time range
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(end_date, time_period)
        
        # Get session data
        sessions = self._get_user_sessions(user_id, start_date, end_date)
        
        if not sessions:
            return self._create_empty_metrics(time_period)
        
        return self._calculate_performance_metrics(sessions, time_period)
    
    def _calculate_start_date(self, end_date: datetime, time_period: str) -> datetime:
        """Calculate start date based on time period."""
        days = AnalyticsConstants.TIME_PERIOD_DAYS.get(time_period, 30)
        return end_date - timedelta(days=days)
    
    def _calculate_performance_metrics(self, sessions: List[InterviewSession], time_period: str) -> PerformanceMetrics:
        """Calculate performance metrics from a list of sessions."""
        if not sessions:
            return self._create_empty_metrics(time_period)
        
        # Calculate basic metrics
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
    
    def _calculate_basic_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate basic session metrics."""
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == "completed"])
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        total_questions = sum(len(self._get_session_questions(s.id)) for s in sessions)
        total_time = sum(self._calculate_completion_time(s) for s in sessions)
        average_response_time = total_time / total_questions if total_questions > 0 else 0
        
        return {
            "total_sessions": total_sessions,
            "completion_rate": completion_rate,
            "total_questions_answered": total_questions,
            "average_response_time": average_response_time
        }
    
    def _calculate_score_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate score-related metrics."""
        all_answers = []
        for session in sessions:
            answers = self._get_session_answers(session.id)
            all_answers.extend(answers)
        
        if not all_answers:
            return {
                "average_score": 0.0,
                "strongest_areas": [],
                "improvement_areas": []
            }
        
        average_score = self._calculate_average_score_from_answers(all_answers)
        category_scores = self._calculate_category_scores(all_answers)
        
        # Sort categories by score
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        strongest_areas = [cat for cat, score in sorted_categories[:3]]
        improvement_areas = [cat for cat, score in sorted_categories[-3:]]
        
        return {
            "average_score": average_score,
            "strongest_areas": strongest_areas,
            "improvement_areas": improvement_areas
        }
    
    def _calculate_trend_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate trend metrics."""
        if len(sessions) < 2:
            return {"improvement_trend": 0.0}
        
        # Sort sessions by date
        sorted_sessions = sorted(sessions, key=lambda s: s.created_at)
        
        # Calculate scores for first and second half
        mid_point = len(sorted_sessions) // 2
        first_half = sorted_sessions[:mid_point]
        second_half = sorted_sessions[mid_point:]
        
        first_half_scores = []
        second_half_scores = []
        
        for session in first_half:
            answers = self._get_session_answers(session.id)
            if answers:
                first_half_scores.append(self._calculate_average_score_from_answers(answers))
        
        for session in second_half:
            answers = self._get_session_answers(session.id)
            if answers:
                second_half_scores.append(self._calculate_average_score_from_answers(answers))
        
        if not first_half_scores or not second_half_scores:
            return {"improvement_trend": 0.0}
        
        first_avg = sum(first_half_scores) / len(first_half_scores)
        second_avg = sum(second_half_scores) / len(second_half_scores)
        
        improvement_trend = second_avg - first_avg
        return {"improvement_trend": improvement_trend}
    
    # Simplified Analytics Methods (using aggregation framework)
    def get_user_performance_metrics_simple(self, user_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get user performance metrics using simplified aggregation."""
        # Simplified implementation without external aggregation framework
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
        
        # Calculate basic metrics
        all_answers = []
        for session in sessions:
            answers = self._get_session_answers(session.id)
            all_answers.extend(answers)
        
        scores = [answer.score for answer in all_answers if answer.score is not None]
        
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
    
    def get_session_analytics_simple(self, session_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get session analytics using simplified aggregation."""
        # Simplified implementation without external aggregation framework
        session = self.db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        if not session:
            return {
                "session_id": session_id,
                "metrics": {"count": 0, "duration": 0, "questions_answered": 0, "avg_score": 0.0},
                "time_range": f"{date_range_days} days",
                "execution_time_ms": 0
            }
        
        # Get session data
        answers = self._get_session_answers(session.id)
        questions = self._get_session_questions(session.id)
        duration = self._calculate_completion_time(session)
        scores = [answer.score for answer in answers if answer.score is not None]
        
        return {
            "session_id": session_id,
            "metrics": {
                "count": 1,
                "duration": duration,
                "questions_answered": len(answers),
                "avg_score": sum(scores) / len(scores) if scores else 0.0
            },
            "time_range": f"{date_range_days} days",
            "execution_time_ms": 0
        }
    
    def get_question_analytics_simple(self, question_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Get question analytics using simplified aggregation."""
        # Simplified implementation without external aggregation framework
        question = self.db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            return {
                "question_id": question_id,
                "metrics": {"count": 0, "avg_difficulty": 0.0, "avg_response_time": 0.0, "avg_accuracy": 0.0},
                "time_range": f"{date_range_days} days",
                "execution_time_ms": 0
            }
        
        # Get answers for this question
        answers = self.db.query(Answer).filter(Answer.question_id == question_id).all()
        
        if not answers:
            return {
                "question_id": question_id,
                "metrics": {"count": 0, "avg_difficulty": 0.0, "avg_response_time": 0.0, "avg_accuracy": 0.0},
                "time_range": f"{date_range_days} days",
                "execution_time_ms": 0
            }
        
        # Calculate metrics
        scores = [answer.score for answer in answers if answer.score is not None]
        response_times = [answer.response_time for answer in answers if answer.response_time is not None]
        
        return {
            "question_id": question_id,
            "metrics": {
                "count": len(answers),
                "avg_difficulty": question.difficulty_level or 0.0,
                "avg_response_time": sum(response_times) / len(response_times) if response_times else 0.0,
                "avg_accuracy": sum(scores) / len(scores) if scores else 0.0
            },
            "time_range": f"{date_range_days} days",
            "execution_time_ms": 0
        }
    
    # Report Generation Methods
    @handle_analytics_errors("generating report")
    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate a comprehensive analytics report."""
        # Get performance metrics
        metrics = self.get_performance_metrics(request.user_id, request.time_period)
        
        # Get session analytics
        sessions = self._get_user_sessions(
            request.user_id,
            self._calculate_start_date(datetime.utcnow(), request.time_period),
            datetime.utcnow()
        )
        
        # Generate report content
        report_content = self._generate_report_content(metrics, sessions, request)
        
        return ReportResponse(
            report_id=str(uuid.uuid4()),
            user_id=request.user_id,
            report_type=request.report_type,
            time_period=request.time_period,
            generated_at=datetime.utcnow(),
            content=report_content,
            metrics=metrics
        )
    
    def _generate_report_content(self, metrics: PerformanceMetrics, sessions: List[InterviewSession], request: ReportRequest) -> str:
        """Generate report content based on metrics and sessions."""
        content = f"# Performance Report for {request.time_period}\n\n"
        content += f"## Summary\n"
        content += f"- Total Sessions: {metrics.total_sessions}\n"
        content += f"- Average Score: {metrics.average_score:.2f}\n"
        content += f"- Completion Rate: {metrics.completion_rate:.1f}%\n"
        content += f"- Improvement Trend: {metrics.improvement_trend:+.2f}\n\n"
        
        if metrics.strongest_areas:
            content += f"## Strongest Areas\n"
            for area in metrics.strongest_areas:
                content += f"- {area}\n"
            content += "\n"
        
        if metrics.improvement_areas:
            content += f"## Areas for Improvement\n"
            for area in metrics.improvement_areas:
                content += f"- {area}\n"
            content += "\n"
        
        return content
    
    # Analytics Summary Methods
    @handle_analytics_errors("getting analytics summary")
    def get_analytics_summary(self, user_id: str, time_period: str = "30d") -> AnalyticsSummary:
        """Get a comprehensive analytics summary."""
        metrics = self.get_performance_metrics(user_id, time_period)
        
        # Get recent sessions for additional context
        recent_sessions = self._get_user_sessions(
            user_id,
            self._calculate_start_date(datetime.utcnow(), time_period),
            datetime.utcnow()
        )
        
        return AnalyticsSummary(
            user_id=user_id,
            time_period=time_period,
            performance_metrics=metrics,
            total_sessions=len(recent_sessions),
            last_activity=recent_sessions[-1].created_at if recent_sessions else None,
            generated_at=datetime.utcnow()
        )
    
    # Performance Comparison Methods
    @handle_analytics_errors("comparing performance")
    def compare_performance(self, user_id: str, comparison_periods: List[str]) -> PerformanceComparison:
        """Compare performance across different time periods."""
        metrics_by_period = {}
        
        for period in comparison_periods:
            metrics_by_period[period] = self.get_performance_metrics(user_id, period)
        
        return PerformanceComparison(
            user_id=user_id,
            comparison_periods=comparison_periods,
            metrics_by_period=metrics_by_period,
            generated_at=datetime.utcnow()
        )
    
    # Legacy Compatibility Methods
    def get_user_performance_metrics(self, user_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Legacy method for backward compatibility - uses simplified aggregation."""
        return self.get_user_performance_metrics_simple(user_id, date_range_days)
    
    def get_session_analytics(self, session_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Legacy method for backward compatibility - uses simplified aggregation."""
        return self.get_session_analytics_simple(session_id, date_range_days)
    
    def get_question_analytics(self, question_id: str, date_range_days: int = 30) -> Dict[str, Any]:
        """Legacy method for backward compatibility - uses simplified aggregation."""
        return self.get_question_analytics_simple(question_id, date_range_days)
