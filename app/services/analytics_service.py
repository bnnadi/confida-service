"""
Analytics Service for InterviewIQ.

This service provides comprehensive analytics and reporting functionality,
including performance metrics, trend analysis, and report generation.
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
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {operation_name}: {e}")
                raise
        return wrapper
    return decorator


class AnalyticsService:
    """Service for analytics and reporting functionality."""
    
    def __init__(self, db: Session):
        self.db = db
    
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
    
    def _calculate_performance_metrics(self, sessions: List[InterviewSession], time_period: str) -> PerformanceMetrics:
        """Calculate performance metrics from a list of sessions."""
        if not sessions:
            return self._create_empty_metrics(time_period)
        
        # Calculate basic metrics
        basic_metrics = self._calculate_basic_metrics(sessions)
        score_metrics = self._calculate_score_metrics(sessions)
        trend_metrics = self._calculate_trend_metrics(sessions)
        area_analysis = self._analyze_areas(sessions)
        
        return PerformanceMetrics(
            total_sessions=basic_metrics['total_sessions'],
            average_score=score_metrics['average_score'],
            improvement_trend=trend_metrics['improvement_trend'],
            strongest_areas=area_analysis[0],
            improvement_areas=area_analysis[1],
            time_period=time_period,
            completion_rate=basic_metrics['completion_rate'],
            total_questions_answered=score_metrics['total_questions_answered'],
            average_response_time=score_metrics['average_response_time']
        )
    
    def _calculate_basic_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate basic session metrics."""
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == "completed"])
        completion_rate = (completed_sessions / total_sessions) * 100 if total_sessions > 0 else 0.0
        
        return {
            'total_sessions': total_sessions,
            'completion_rate': completion_rate
        }
    
    def _calculate_score_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate score-related metrics."""
        scores = []
        total_questions_answered = 0
        total_response_time = 0
        
        for session in sessions:
            answers = self._get_session_answers(session.id)
            if answers:
                session_avg = self._calculate_average_score_from_answers(answers)
                if session_avg > 0:
                    scores.append(session_avg)
                
                total_questions_answered += len(answers)
                
                # Calculate response time
                for answer in answers:
                    if answer.created_at and session.created_at:
                        response_time = (answer.created_at - session.created_at).total_seconds()
                        total_response_time += response_time
        
        average_score = sum(scores) / len(scores) if scores else 0.0
        average_response_time = total_response_time / total_questions_answered if total_questions_answered > 0 else 0.0
        
        return {
            'average_score': average_score,
            'total_questions_answered': total_questions_answered,
            'average_response_time': average_response_time
        }
    
    def _calculate_trend_metrics(self, sessions: List[InterviewSession]) -> Dict[str, Any]:
        """Calculate trend-related metrics."""
        improvement_trend = self._calculate_improvement_trend(sessions)
        
        return {
            'improvement_trend': improvement_trend
        }
    
    @handle_analytics_errors("getting trend analysis")
    def get_trend_analysis(self, user_id: str, metric: str, time_period: str = "30d") -> TrendAnalysis:
        """Get trend analysis for a specific metric."""
        # Calculate time range
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(end_date, time_period)
        
        # Get data points over time
        data_points = self._get_metric_data_points(user_id, metric, start_date, end_date)
        
        # Calculate trend
        trend_direction, trend_percentage, confidence_level = self._calculate_trend(data_points)
        
        return TrendAnalysis(
            metric=metric,
            time_period=time_period,
            data_points=data_points,
            trend_direction=trend_direction,
            trend_percentage=trend_percentage,
            confidence_level=confidence_level
        )
    
    def get_session_analytics(self, user_id: str, limit: int = 10, offset: int = 0) -> List[SessionAnalytics]:
        """Get session analytics for a user."""
        try:
            sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id
            ).order_by(desc(InterviewSession.created_at)).offset(offset).limit(limit).all()
            
            session_analytics = []
            for session in sessions:
                # Get session questions and answers
                questions = self.db.query(Question).filter(Question.session_id == session.id).all()
                answers = self.db.query(Answer).filter(Answer.session_id == session.id).all()
                
                # Calculate session metrics
                total_questions = len(questions)
                answered_questions = len(answers)
                
                # Calculate average score
                scores = [answer.score for answer in answers if answer.score is not None]
                average_score = sum(scores) / len(scores) if scores else 0.0
                
                # Calculate completion time
                completion_time = 0
                if session.updated_at and session.created_at:
                    completion_time = int((session.updated_at - session.created_at).total_seconds())
                
                # Analyze difficulty distribution
                difficulty_distribution = {}
                for question in questions:
                    difficulty = question.difficulty_level or "medium"
                    difficulty_distribution[difficulty] = difficulty_distribution.get(difficulty, 0) + 1
                
                # Analyze category scores
                category_scores = {}
                for answer in answers:
                    if answer.question and answer.score is not None:
                        category = answer.question.category or "general"
                        if category not in category_scores:
                            category_scores[category] = []
                        category_scores[category].append(answer.score)
                
                # Calculate average scores per category
                for category in category_scores:
                    category_scores[category] = sum(category_scores[category]) / len(category_scores[category])
                
                session_analytics.append(SessionAnalytics(
                    session_id=str(session.id),
                    user_id=str(session.user_id),
                    role=session.role or "Unknown",
                    total_questions=total_questions,
                    answered_questions=answered_questions,
                    average_score=average_score,
                    completion_time=completion_time,
                    created_at=session.created_at,
                    status=session.status or "unknown",
                    difficulty_distribution=difficulty_distribution,
                    category_scores=category_scores
                ))
            
            return session_analytics
            
        except Exception as e:
            logger.error(f"Error getting session analytics for user {user_id}: {e}")
            raise
    
    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate a comprehensive report."""
        try:
            # Get performance metrics
            time_period = self._calculate_time_period(request.start_date, request.end_date)
            metrics = self.get_performance_metrics(request.user_id, time_period)
            
            # Get trend analysis if requested
            trend_analysis = None
            if request.include_trends:
                trend_analysis = self.get_trend_analysis(request.user_id, "average_score", time_period)
            
            # Get session details
            sessions = self.get_session_analytics(request.user_id, limit=1000)
            
            # Filter sessions by date range
            filtered_sessions = [
                session for session in sessions
                if request.start_date <= session.created_at <= request.end_date
            ]
            
            # Generate recommendations
            recommendations = []
            if request.include_recommendations:
                recommendations = self._generate_recommendations(metrics, trend_analysis)
            
            # Create report response
            report_id = str(uuid.uuid4())
            report_response = ReportResponse(
                report_id=report_id,
                user_id=request.user_id,
                report_type=request.report_type.value,
                generated_at=datetime.utcnow(),
                time_period=f"{request.start_date.date()} to {request.end_date.date()}",
                performance_metrics=metrics,
                trend_analysis=trend_analysis,
                sessions=filtered_sessions,
                recommendations=recommendations
            )
            
            # Log analytics event
            self._log_analytics_event(
                user_id=request.user_id,
                event_type="report_generated",
                event_data={
                    "report_id": report_id,
                    "report_type": request.report_type.value,
                    "time_period": time_period
                }
            )
            
            return report_response
            
        except Exception as e:
            logger.error(f"Error generating report for user {request.user_id}: {e}")
            raise
    
    def get_analytics_summary(self, user_id: str) -> AnalyticsSummary:
        """Get analytics summary for dashboard display."""
        try:
            # Get recent performance metrics
            metrics = self.get_performance_metrics(user_id, "30d")
            
            # Get recent activity
            recent_sessions = self.get_session_analytics(user_id, limit=5)
            recent_activity = []
            
            for session in recent_sessions:
                recent_activity.append({
                    "session_id": session.session_id,
                    "role": session.role,
                    "score": session.average_score,
                    "date": session.created_at.isoformat(),
                    "status": session.status
                })
            
            return AnalyticsSummary(
                total_sessions=metrics.total_sessions,
                average_score=metrics.average_score,
                improvement_trend=metrics.improvement_trend,
                completion_rate=metrics.completion_rate,
                top_performing_areas=metrics.strongest_areas,
                areas_for_improvement=metrics.improvement_areas,
                recent_activity=recent_activity
            )
            
        except Exception as e:
            logger.error(f"Error getting analytics summary for user {user_id}: {e}")
            raise
    
    def get_performance_comparison(self, user_id: str, current_period: str = "30d", previous_period: str = "30d") -> PerformanceComparison:
        """Get performance comparison between two periods."""
        try:
            # Get current period metrics
            current_metrics = self.get_performance_metrics(user_id, current_period)
            
            # Get previous period metrics
            end_date = datetime.utcnow()
            current_start = self._calculate_start_date(end_date, current_period)
            previous_start = self._calculate_start_date(current_start, previous_period)
            
            # Query previous period sessions
            previous_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= previous_start,
                InterviewSession.created_at < current_start
            ).all()
            
            previous_metrics = self._calculate_metrics_from_sessions(previous_sessions, previous_period)
            
            # Calculate improvement percentage
            improvement_percentage = 0.0
            if previous_metrics.average_score > 0:
                improvement_percentage = ((current_metrics.average_score - previous_metrics.average_score) / previous_metrics.average_score) * 100
            
            # Calculate area comparisons
            area_comparisons = self._compare_areas(current_metrics, previous_metrics)
            
            return PerformanceComparison(
                current_period=current_metrics,
                previous_period=previous_metrics,
                improvement_percentage=improvement_percentage,
                area_comparisons=area_comparisons
            )
            
        except Exception as e:
            logger.error(f"Error getting performance comparison for user {user_id}: {e}")
            raise
    
    def _calculate_start_date(self, end_date: datetime, time_period: str) -> datetime:
        """Calculate start date based on time period."""
        days = AnalyticsConstants.TIME_PERIOD_DAYS.get(time_period, 30)  # Default to 30 days
        return end_date - timedelta(days=days)
    
    def _calculate_time_period(self, start_date: datetime, end_date: datetime) -> str:
        """Calculate time period string from date range."""
        days = (end_date - start_date).days
        
        # Find the appropriate time period
        for period, period_days in sorted(AnalyticsConstants.TIME_PERIOD_DAYS.items(), key=lambda x: x[1]):
            if days <= period_days:
                return period
        return "1y"  # Default for longer periods
    
    def _calculate_improvement_trend(self, sessions: List[InterviewSession]) -> float:
        """Calculate improvement trend over time."""
        if len(sessions) < 2:
            return 0.0
        
        # Sort sessions by date
        sorted_sessions = sorted(sessions, key=lambda x: x.created_at)
        
        # Calculate average scores for first and second half
        mid_point = len(sorted_sessions) // 2
        first_half = sorted_sessions[:mid_point]
        second_half = sorted_sessions[mid_point:]
        
        first_half_avg = self._calculate_average_score(first_half)
        second_half_avg = self._calculate_average_score(second_half)
        
        if first_half_avg == 0:
            return 0.0
        
        return ((second_half_avg - first_half_avg) / first_half_avg) * 100
    
    def _calculate_average_score(self, sessions: List[InterviewSession]) -> float:
        """Calculate average score for a list of sessions."""
        total_score = 0.0
        total_sessions = 0
        
        for session in sessions:
            answers = self.db.query(Answer).filter(Answer.session_id == session.id).all()
            if answers:
                scores = [answer.score for answer in answers if answer.score is not None]
                if scores:
                    total_score += sum(scores) / len(scores)
                    total_sessions += 1
        
        return total_score / total_sessions if total_sessions > 0 else 0.0
    
    def _analyze_areas(self, sessions: List[InterviewSession]) -> Tuple[List[str], List[str]]:
        """Analyze strongest and weakest areas."""
        # This is a simplified implementation
        # In a real system, this would analyze the content of answers
        strongest_areas = ["Technical Knowledge", "Communication"]
        improvement_areas = ["Problem Solving", "Leadership"]
        
        return strongest_areas, improvement_areas
    
    def _get_metric_data_points(self, user_id: str, metric: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get data points for trend analysis."""
        # Simplified implementation - in practice, this would aggregate data by time periods
        sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id,
            InterviewSession.created_at >= start_date,
            InterviewSession.created_at <= end_date
        ).order_by(asc(InterviewSession.created_at)).all()
        
        data_points = []
        for session in sessions:
            if metric == "average_score":
                answers = self.db.query(Answer).filter(Answer.session_id == session.id).all()
                scores = [answer.score for answer in answers if answer.score is not None]
                value = sum(scores) / len(scores) if scores else 0.0
            else:
                value = 0.0
            
            data_points.append({
                "date": session.created_at.isoformat(),
                "value": value,
                "session_id": str(session.id)
            })
        
        return data_points
    
    def _calculate_trend(self, data_points: List[Dict[str, Any]]) -> Tuple[TrendDirection, float, float]:
        """Calculate trend from data points."""
        if len(data_points) < 2:
            return TrendDirection.STABLE, 0.0, 0.0
        
        # Simple linear trend calculation
        values = [point["value"] for point in data_points]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0.0
        second_avg = sum(second_half) / len(second_half) if second_half else 0.0
        
        if first_avg == 0:
            return TrendDirection.STABLE, 0.0, 0.0
        
        trend_percentage = ((second_avg - first_avg) / first_avg) * 100
        
        # Use constants for threshold
        if trend_percentage > AnalyticsConstants.TREND_THRESHOLD:
            direction = TrendDirection.UP
        elif trend_percentage < -AnalyticsConstants.TREND_THRESHOLD:
            direction = TrendDirection.DOWN
        else:
            direction = TrendDirection.STABLE
        
        # Simple confidence calculation
        confidence = min(abs(trend_percentage) / AnalyticsConstants.CONFIDENCE_DIVISOR, 1.0)
        
        return direction, trend_percentage, confidence
    
    def _generate_recommendations(self, metrics: PerformanceMetrics, trend_analysis: Optional[TrendAnalysis]) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        # Use constants for thresholds
        if metrics.average_score < AnalyticsConstants.LOW_SCORE_THRESHOLD:
            recommendations.append("Focus on improving overall interview performance")
        
        if metrics.improvement_trend < 0:
            recommendations.append("Consider reviewing recent interview techniques")
        
        if "Problem Solving" in metrics.improvement_areas:
            recommendations.append("Practice problem-solving scenarios and coding challenges")
        
        if "Communication" in metrics.improvement_areas:
            recommendations.append("Work on clear and concise communication skills")
        
        if metrics.completion_rate < AnalyticsConstants.LOW_COMPLETION_RATE_THRESHOLD:
            recommendations.append("Try to complete more interview sessions to get better insights")
        
        if trend_analysis and trend_analysis.trend_direction == TrendDirection.DOWN:
            recommendations.append("Review your recent performance and consider adjusting your preparation strategy")
        
        return recommendations
    
    
    def _compare_areas(self, current: PerformanceMetrics, previous: PerformanceMetrics) -> Dict[str, Dict[str, float]]:
        """Compare performance areas between two periods."""
        comparisons = {}
        
        # Compare strongest areas
        for area in current.strongest_areas:
            if area in previous.strongest_areas:
                comparisons[area] = {
                    "current": 1.0,
                    "previous": 1.0,
                    "change": 0.0
                }
            else:
                comparisons[area] = {
                    "current": 1.0,
                    "previous": 0.0,
                    "change": 1.0
                }
        
        return comparisons
    
    def _log_analytics_event(self, user_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log an analytics event."""
        try:
            event = AnalyticsEvent(
                user_id=user_id,
                event_type=event_type,
                event_data=event_data
            )
            self.db.add(event)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging analytics event: {e}")
            self.db.rollback()
