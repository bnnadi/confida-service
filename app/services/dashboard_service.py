"""
Dashboard Service for Confida.

This service provides dashboard-specific data aggregation and formatting
for the dashboard API endpoints.
"""
from typing import Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.services.data_aggregator import DataAggregator
from app.services.analytics_service import AnalyticsService
from app.database.models import InterviewSession
from app.models.dashboard_models import (
    DashboardOverview, UserProgress, AnalyticsData, PerformanceMetrics,
    PerformanceTrends, UserInsights, Activity
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DashboardService:
    """Service for dashboard data aggregation and formatting."""
    
    def __init__(self, db: Session):
        self.db = db
        self.aggregator = DataAggregator(db)
        self.analytics_service = AnalyticsService(db)
    
    def get_dashboard_overview(
        self,
        user_id: str,
        days: int = 30
    ) -> DashboardOverview:
        """Get dashboard overview data."""
        try:
            # Get session summary
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            summary = self.aggregator.get_user_sessions_summary(user_id, start_date, end_date)
            
            # Calculate improvement rate
            improvement_rate = 0.0
            if summary["total_sessions"] > 1:
                # Get first and last session scores
                sessions = self.db.query(InterviewSession).filter(
                    InterviewSession.user_id == user_id
                ).order_by(InterviewSession.created_at).all()
                
                if len(sessions) >= 2:
                    first_scores = []
                    last_scores = []
                    
                    # Get first half scores
                    for session in sessions[:len(sessions)//2]:
                        if session.overall_score and isinstance(session.overall_score, dict):
                            if "overall" in session.overall_score:
                                first_scores.append(float(session.overall_score["overall"]))
                    
                    # Get last half scores
                    for session in sessions[len(sessions)//2:]:
                        if session.overall_score and isinstance(session.overall_score, dict):
                            if "overall" in session.overall_score:
                                last_scores.append(float(session.overall_score["overall"]))
                    
                    if first_scores and last_scores:
                        first_avg = sum(first_scores) / len(first_scores)
                        last_avg = sum(last_scores) / len(last_scores)
                        improvement_rate = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0.0
            
            # Get current streak
            current_streak = self.aggregator.get_current_streak(user_id)
            
            # Get recent activity
            recent_activities = self.aggregator.get_recent_activity(user_id, limit=10)
            activities = [
                Activity(
                    activity_type=act["activity_type"],
                    activity_date=act["activity_date"],
                    activity_data=act["activity_data"]
                )
                for act in recent_activities
            ]
            
            return DashboardOverview(
                user_id=user_id,
                total_sessions=summary["total_sessions"],
                average_score=summary["average_score"],
                improvement_rate=improvement_rate,
                current_streak=current_streak,
                recent_activity=activities,
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting dashboard overview for user {user_id}: {e}")
            raise
    
    def get_user_progress(
        self,
        user_id: str,
        days: int = 30
    ) -> UserProgress:
        """Get user progress data."""
        try:
            progress_data = self.aggregator.get_user_progress_data(user_id, days)
            
            return UserProgress(
                user_id=user_id,
                skill_progression=progress_data["skill_progression"],
                difficulty_progression=progress_data["difficulty_progression"],
                time_progression=progress_data["time_progression"],
                overall_trend=progress_data["overall_trend"],
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting user progress for user {user_id}: {e}")
            raise
    
    def get_analytics_data(
        self,
        user_id: str,
        days: int = 30
    ) -> AnalyticsData:
        """Get analytics data."""
        try:
            # Get performance metrics
            metrics = self.aggregator.get_performance_metrics_detailed(user_id, days)
            
            # Get skill breakdown
            skill_breakdown = self.aggregator.get_skill_breakdown(user_id, days)
            
            # Get time analysis
            time_analysis = {
                "total_days": days,
                "sessions_per_day": metrics["total_sessions"] / days if days > 0 else 0,
                "average_duration_minutes": metrics["average_session_duration"]
            }
            
            # Get recommendations from insights
            insights = self.aggregator.get_user_insights(user_id, days)
            recommendations = insights["recommendations"]
            
            return AnalyticsData(
                user_id=user_id,
                performance_metrics={
                    "average_score": metrics["average_score"],
                    "completion_rate": metrics["completion_rate"],
                    "total_sessions": metrics["total_sessions"],
                    "total_questions": metrics["total_questions_answered"]
                },
                skill_breakdown=skill_breakdown,
                time_analysis=time_analysis,
                recommendations=recommendations,
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting analytics data for user {user_id}: {e}")
            raise
    
    def get_performance_metrics(
        self,
        user_id: str,
        days: int = 30
    ) -> PerformanceMetrics:
        """Get performance metrics."""
        try:
            metrics = self.aggregator.get_performance_metrics_detailed(user_id, days)
            
            return PerformanceMetrics(
                user_id=user_id,
                total_sessions=metrics["total_sessions"],
                completed_sessions=metrics["completed_sessions"],
                average_score=metrics["average_score"],
                best_score=metrics["best_score"],
                worst_score=metrics["worst_score"],
                completion_rate=metrics["completion_rate"],
                average_session_duration=metrics["average_session_duration"],
                total_questions_answered=metrics["total_questions_answered"],
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting performance metrics for user {user_id}: {e}")
            raise
    
    def get_performance_trends(
        self,
        user_id: str,
        days: int = 30
    ) -> PerformanceTrends:
        """Get performance trends."""
        try:
            trend_data = self.aggregator.get_trend_data(user_id, days)
            
            return PerformanceTrends(
                user_id=user_id,
                score_trend=trend_data["score_trend"],
                completion_trend=trend_data["completion_trend"],
                skill_trends=trend_data["skill_trends"],
                trend_direction=trend_data["trend_direction"],
                trend_percentage=trend_data["trend_percentage"],
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting performance trends for user {user_id}: {e}")
            raise
    
    def get_user_insights(
        self,
        user_id: str,
        days: int = 30
    ) -> UserInsights:
        """Get user insights."""
        try:
            insights_data = self.aggregator.get_user_insights(user_id, days)
            
            return UserInsights(
                user_id=user_id,
                strengths=insights_data["strengths"],
                weaknesses=insights_data["weaknesses"],
                recommendations=insights_data["recommendations"],
                milestones=insights_data["milestones"],
                next_goals=insights_data["next_goals"],
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting user insights for user {user_id}: {e}")
            raise

