"""
Analytics data models for Confida.

This module defines Pydantic models for analytics and reporting functionality,
including performance metrics, trend analysis, report generation, dimension
progress tracking, session comparison, and goal management.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class TimePeriod(str, Enum):
    """Time period options for analytics."""
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"
    ONE_YEAR = "1y"


class ReportType(str, Enum):
    """Report type options."""
    PERFORMANCE = "performance"
    TRENDS = "trends"
    DETAILED = "detailed"
    SUMMARY = "summary"


class ReportFormat(str, Enum):
    """Report export format options."""
    JSON = "json"
    PDF = "pdf"
    CSV = "csv"


class TrendDirection(str, Enum):
    """Trend direction options."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class GoalStatus(str, Enum):
    """Goal status options."""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class GoalType(str, Enum):
    """Goal type options."""
    SCORE = "score"
    SESSIONS = "sessions"
    STREAK = "streak"
    COMPLETION_RATE = "completion_rate"
    DIMENSION_SCORE = "dimension_score"


class PerformanceMetrics(BaseModel):
    """Performance metrics for a user."""
    total_sessions: int = Field(..., description="Total number of interview sessions")
    average_score: float = Field(..., description="Average score across all sessions")
    improvement_trend: float = Field(..., description="Improvement trend percentage")
    strongest_areas: List[str] = Field(..., description="Areas where user performs best")
    improvement_areas: List[str] = Field(..., description="Areas needing improvement")
    time_period: str = Field(..., description="Time period for metrics")
    completion_rate: float = Field(..., description="Session completion rate")
    total_questions_answered: int = Field(..., description="Total questions answered")
    average_response_time: float = Field(..., description="Average response time in seconds")


class SessionAnalytics(BaseModel):
    """Analytics for a single interview session."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    role: str = Field(..., description="Interview role")
    total_questions: int = Field(..., description="Total questions in session")
    answered_questions: int = Field(..., description="Questions answered")
    average_score: float = Field(..., description="Average score for session")
    completion_time: int = Field(..., description="Session completion time in seconds")
    created_at: datetime = Field(..., description="Session creation timestamp")
    status: str = Field(..., description="Session status")
    difficulty_distribution: Dict[str, int] = Field(..., description="Distribution of question difficulties")
    category_scores: Dict[str, float] = Field(..., description="Scores by question category")


class TrendAnalysis(BaseModel):
    """Trend analysis for a specific metric."""
    metric: str = Field(..., description="Metric being analyzed")
    time_period: str = Field(..., description="Time period for analysis")
    data_points: List[Dict[str, Any]] = Field(..., description="Data points over time")
    trend_direction: TrendDirection = Field(..., description="Overall trend direction")
    trend_percentage: float = Field(..., description="Trend percentage change")
    confidence_level: float = Field(..., description="Confidence level of trend analysis")
    seasonal_patterns: Optional[Dict[str, Any]] = Field(None, description="Seasonal patterns detected")


class ReportRequest(BaseModel):
    """Request model for generating reports."""
    user_id: str = Field(..., description="User identifier")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    report_type: ReportType = Field(..., description="Type of report to generate")
    format: ReportFormat = Field(default=ReportFormat.JSON, description="Export format")
    include_recommendations: bool = Field(default=True, description="Include improvement recommendations")
    include_trends: bool = Field(default=True, description="Include trend analysis")


class ReportResponse(BaseModel):
    """Response model for generated reports."""
    report_id: str = Field(..., description="Unique report identifier")
    user_id: str = Field(..., description="User identifier")
    report_type: str = Field(..., description="Type of report generated")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    time_period: str = Field(..., description="Time period covered")
    performance_metrics: PerformanceMetrics = Field(..., description="Performance metrics")
    trend_analysis: Optional[TrendAnalysis] = Field(None, description="Trend analysis")
    sessions: List[SessionAnalytics] = Field(..., description="Session details")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    export_url: Optional[str] = Field(None, description="URL for exported report file")


class AnalyticsSummary(BaseModel):
    """Summary analytics for dashboard display."""
    total_sessions: int = Field(..., description="Total sessions")
    average_score: float = Field(..., description="Overall average score")
    improvement_trend: float = Field(..., description="Improvement trend")
    completion_rate: float = Field(..., description="Session completion rate")
    top_performing_areas: List[str] = Field(..., description="Top performing areas")
    areas_for_improvement: List[str] = Field(..., description="Areas needing improvement")
    recent_activity: List[Dict[str, Any]] = Field(..., description="Recent activity summary")


class PerformanceComparison(BaseModel):
    """Performance comparison across different metrics."""
    current_period: PerformanceMetrics = Field(..., description="Current period metrics")
    previous_period: PerformanceMetrics = Field(..., description="Previous period metrics")
    improvement_percentage: float = Field(..., description="Overall improvement percentage")
    area_comparisons: Dict[str, Dict[str, float]] = Field(..., description="Area-specific comparisons")


class AnalyticsFilter(BaseModel):
    """Filter options for analytics queries."""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    role: Optional[str] = Field(None, description="Filter by role")
    start_date: Optional[datetime] = Field(None, description="Filter start date")
    end_date: Optional[datetime] = Field(None, description="Filter end date")
    min_score: Optional[float] = Field(None, description="Minimum score filter")
    max_score: Optional[float] = Field(None, description="Maximum score filter")
    session_status: Optional[str] = Field(None, description="Filter by session status")
    limit: int = Field(default=100, description="Maximum number of results")
    offset: int = Field(default=0, description="Number of results to skip")


class FilteredSessionsResponse(BaseModel):
    """Response for filtered session analytics query."""
    sessions: List[SessionAnalytics] = Field(..., description="Filtered sessions")
    total_count: int = Field(..., description="Total matching sessions (before pagination)")
    filters_applied: Dict[str, Any] = Field(..., description="Filters that were applied")


class HeatmapCell(BaseModel):
    """A single cell in the performance heatmap."""
    day_of_week: int = Field(..., description="Day of week (0=Monday, 6=Sunday)")
    hour: int = Field(..., description="Hour of day (0-23)")
    session_count: int = Field(default=0, description="Number of sessions in this slot")
    average_score: float = Field(default=0.0, description="Average score in this slot")


class PerformanceHeatmap(BaseModel):
    """Performance heatmap showing activity and scores by day/hour."""
    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(..., description="Time period analyzed")
    cells: List[HeatmapCell] = Field(..., description="Heatmap cells")
    peak_day: str = Field(..., description="Day with most activity")
    peak_hour: int = Field(..., description="Hour with most activity")
    total_sessions: int = Field(..., description="Total sessions in period")
    last_updated: datetime = Field(..., description="Last update timestamp")


# --- Dimension Progress Tracking Models ---

class DimensionScore(BaseModel):
    """Score for a specific scoring dimension."""
    dimension: str = Field(..., description="Dimension name (e.g., 'technical', 'communication')")
    score: float = Field(..., description="Score for this dimension")
    max_score: float = Field(default=100.0, description="Maximum possible score")
    trend: TrendDirection = Field(default=TrendDirection.STABLE, description="Trend direction")
    trend_percentage: float = Field(default=0.0, description="Trend change percentage")


class DimensionProgress(BaseModel):
    """Progress tracking across scoring dimensions."""
    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(..., description="Time period for analysis")
    dimensions: List[DimensionScore] = Field(..., description="Scores per dimension")
    overall_score: float = Field(..., description="Overall composite score")
    data_points: List[Dict[str, Any]] = Field(default_factory=list, description="Time-series data per dimension")
    last_updated: datetime = Field(..., description="Last update timestamp")


# --- Session Comparison Models ---

class SessionComparisonResponse(BaseModel):
    """Response for comparing two interview sessions."""
    session_a: SessionAnalytics = Field(..., description="First session analytics")
    session_b: SessionAnalytics = Field(..., description="Second session analytics")
    score_delta: float = Field(..., description="Score difference (B - A)")
    category_deltas: Dict[str, float] = Field(..., description="Per-category score deltas")
    improvement_summary: str = Field(..., description="Human-readable improvement summary")


# --- Goal Management Models ---

class UserGoalCreate(BaseModel):
    """Request model for creating a user goal."""
    title: str = Field(..., description="Goal title", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Goal description")
    goal_type: GoalType = Field(..., description="Type of goal")
    target_value: float = Field(..., description="Target value to achieve")
    target_date: Optional[datetime] = Field(None, description="Target completion date")
    dimension: Optional[str] = Field(None, description="Specific dimension for dimension_score goals")


class UserGoalUpdate(BaseModel):
    """Request model for updating a user goal."""
    title: Optional[str] = Field(None, description="Goal title", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="Goal description")
    target_value: Optional[float] = Field(None, description="Target value to achieve")
    target_date: Optional[datetime] = Field(None, description="Target completion date")
    status: Optional[GoalStatus] = Field(None, description="Goal status")


class UserGoalResponse(BaseModel):
    """Response model for a user goal."""
    id: str = Field(..., description="Goal identifier")
    user_id: str = Field(..., description="User identifier")
    title: str = Field(..., description="Goal title")
    description: Optional[str] = Field(None, description="Goal description")
    goal_type: str = Field(..., description="Type of goal")
    target_value: float = Field(..., description="Target value to achieve")
    current_value: float = Field(..., description="Current progress value")
    progress_percentage: float = Field(..., description="Progress as percentage")
    dimension: Optional[str] = Field(None, description="Specific dimension for dimension_score goals")
    target_date: Optional[datetime] = Field(None, description="Target completion date")
    status: str = Field(..., description="Goal status")
    created_at: datetime = Field(..., description="Goal creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
