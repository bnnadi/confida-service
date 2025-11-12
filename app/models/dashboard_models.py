"""
Dashboard data models for Confida.

This module defines Pydantic models for dashboard data aggregation,
including overview, progress, analytics, metrics, trends, and insights.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class Activity(BaseModel):
    """Activity model for recent user activity."""
    activity_type: str = Field(..., description="Type of activity")
    activity_date: datetime = Field(..., description="Activity timestamp")
    activity_data: Dict[str, Any] = Field(..., description="Activity-specific data")


class DashboardOverview(BaseModel):
    """Dashboard overview data model."""
    user_id: str = Field(..., description="User identifier")
    total_sessions: int = Field(..., description="Total number of interview sessions")
    average_score: float = Field(..., description="Average score across all sessions")
    improvement_rate: float = Field(..., description="Improvement rate percentage")
    current_streak: int = Field(..., description="Current consecutive days with activity")
    recent_activity: List[Activity] = Field(..., description="Recent activity list")
    last_updated: datetime = Field(..., description="Last update timestamp")


class UserProgress(BaseModel):
    """User progress data model."""
    user_id: str = Field(..., description="User identifier")
    skill_progression: Dict[str, List[float]] = Field(..., description="Skill progression over time")
    difficulty_progression: List[float] = Field(..., description="Difficulty progression over time")
    time_progression: List[datetime] = Field(..., description="Time progression timestamps")
    overall_trend: str = Field(..., description="Overall trend: 'improving', 'stable', or 'declining'")
    last_updated: datetime = Field(..., description="Last update timestamp")


class AnalyticsData(BaseModel):
    """Analytics data model."""
    user_id: str = Field(..., description="User identifier")
    performance_metrics: Dict[str, float] = Field(..., description="Performance metrics")
    skill_breakdown: Dict[str, float] = Field(..., description="Skill breakdown by category")
    time_analysis: Dict[str, Any] = Field(..., description="Time-based analysis")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    last_updated: datetime = Field(..., description="Last update timestamp")


class PerformanceMetrics(BaseModel):
    """Performance metrics model for dashboard."""
    user_id: str = Field(..., description="User identifier")
    total_sessions: int = Field(..., description="Total sessions")
    completed_sessions: int = Field(..., description="Completed sessions")
    average_score: float = Field(..., description="Average score")
    best_score: float = Field(..., description="Best score achieved")
    worst_score: float = Field(..., description="Worst score achieved")
    completion_rate: float = Field(..., description="Session completion rate")
    average_session_duration: float = Field(..., description="Average session duration in minutes")
    total_questions_answered: int = Field(..., description="Total questions answered")
    last_updated: datetime = Field(..., description="Last update timestamp")


class PerformanceTrends(BaseModel):
    """Performance trends model."""
    user_id: str = Field(..., description="User identifier")
    score_trend: List[Dict[str, Any]] = Field(..., description="Score trend over time")
    completion_trend: List[Dict[str, Any]] = Field(..., description="Completion trend over time")
    skill_trends: Dict[str, List[Dict[str, Any]]] = Field(..., description="Skill-specific trends")
    trend_direction: str = Field(..., description="Overall trend direction")
    trend_percentage: float = Field(..., description="Trend percentage change")
    last_updated: datetime = Field(..., description="Last update timestamp")


class UserInsights(BaseModel):
    """User insights model."""
    user_id: str = Field(..., description="User identifier")
    strengths: List[str] = Field(..., description="User strengths")
    weaknesses: List[str] = Field(..., description="Areas for improvement")
    recommendations: List[str] = Field(..., description="Personalized recommendations")
    milestones: List[Dict[str, Any]] = Field(..., description="Achieved milestones")
    next_goals: List[Dict[str, Any]] = Field(..., description="Next goals to achieve")
    last_updated: datetime = Field(..., description="Last update timestamp")

