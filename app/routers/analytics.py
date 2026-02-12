"""
Analytics API endpoints for Confida.

This module provides REST API endpoints for analytics and reporting functionality,
including performance metrics, trend analysis, report generation, dimension progress
tracking, session comparison, and goal management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.database_service import get_db
from app.services.analytics_service import AnalyticsService
from app.models.analytics_models import (
    PerformanceMetrics, SessionAnalytics, TrendAnalysis, ReportRequest, 
    ReportResponse, AnalyticsSummary, PerformanceComparison, AnalyticsFilter,
    TimePeriod, ReportType, ReportFormat, DimensionProgress,
    SessionComparisonResponse, UserGoalCreate, UserGoalUpdate, UserGoalResponse,
    GoalStatus, FilteredSessionsResponse, PerformanceHeatmap
)
from app.database.question_database_models import (
    QuestionGenerationLog, QuestionTemplate, QuestionMatch, QuestionFeedback
)
from sqlalchemy import func, desc, and_
from app.middleware.auth_middleware import get_current_user_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    """Dependency to get analytics service."""
    return AnalyticsService(db)


# =============================================================================
# Performance Metrics
# =============================================================================

@router.get("/performance/{user_id}", response_model=PerformanceMetrics)
async def get_performance_metrics(
    user_id: str,
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get performance metrics for a user.
    
    Returns comprehensive performance metrics including average scores,
    improvement trends, and area analysis for the specified time period.
    """
    try:
        if time_period not in [tp.value for tp in TimePeriod]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {[tp.value for tp in TimePeriod]}"
            )
        
        metrics = analytics_service.get_performance_metrics(user_id, time_period)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="performance_metrics_viewed",
            event_data={"time_period": time_period}
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance metrics for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        ) from e


# =============================================================================
# Trend Analysis
# =============================================================================

@router.get("/trends/{user_id}", response_model=TrendAnalysis)
async def get_trend_analysis(
    user_id: str,
    metric: str = Query("average_score", description="Metric to analyze"),
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get trend analysis for a user.
    
    Analyzes trends for a specific metric over the specified time period,
    including trend direction, percentage change, and confidence level.
    """
    try:
        if time_period not in [tp.value for tp in TimePeriod]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {[tp.value for tp in TimePeriod]}"
            )
        
        valid_metrics = ["average_score", "completion_rate", "total_sessions", "response_time"]
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {valid_metrics}"
            )
        
        trend_analysis = analytics_service.get_trend_analysis(user_id, metric, time_period)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="trend_analysis_viewed",
            event_data={"metric": metric, "time_period": time_period}
        )
        
        return trend_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trend analysis for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trend analysis: {str(e)}"
        ) from e


# =============================================================================
# Session Analytics
# =============================================================================

@router.get("/sessions/{user_id}", response_model=List[SessionAnalytics])
async def get_session_analytics(
    user_id: str,
    limit: int = Query(10, description="Number of sessions to return", ge=1, le=100),
    offset: int = Query(0, description="Number of sessions to skip", ge=0),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get session analytics for a user.
    
    Returns detailed analytics for recent interview sessions,
    including scores, completion times, and category breakdowns.
    """
    try:
        sessions = analytics_service.get_session_analytics(user_id, limit, offset)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="session_analytics_viewed",
            event_data={"limit": limit, "offset": offset}
        )
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error getting session analytics for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session analytics: {str(e)}"
        ) from e


# =============================================================================
# Report Generation & Export
# =============================================================================

@router.post("/reports", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Generate a comprehensive analytics report.
    
    Creates a detailed report with performance metrics, trend analysis,
    session details, and improvement recommendations.
    """
    try:
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        date_diff = request.end_date - request.start_date
        if date_diff.days > 365:
            raise HTTPException(
                status_code=400,
                detail="Date range cannot exceed 365 days"
            )
        
        report = analytics_service.generate_report(request)
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        ) from e


@router.get("/reports/{user_id}/export")
async def export_report(
    user_id: str,
    format: str = Query("json", description="Export format: json, pdf, csv"),
    start_date: Optional[datetime] = Query(None, description="Report start date"),
    end_date: Optional[datetime] = Query(None, description="Report end date"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Export analytics report in specified format.
    
    Generates and exports a report in the requested format (JSON, PDF, or CSV).
    If no date range is specified, defaults to the last 30 days.
    """
    try:
        if format not in [fmt.value for fmt in ReportFormat]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {[fmt.value for fmt in ReportFormat]}"
            )
        
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        if start_date >= end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        report_request = ReportRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            report_type=ReportType.DETAILED,
            format=ReportFormat(format)
        )
        
        if format == "csv":
            csv_content = analytics_service.generate_csv_report(report_request)
            return PlainTextResponse(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=confida-report-{user_id}.csv"}
            )
        elif format == "pdf":
            # PDF generation requires additional dependencies — return JSON with note
            report = analytics_service.generate_report(report_request)
            return {
                "message": "PDF export requires additional setup. Returning JSON data.",
                "report": report.dict()
            }
        else:
            report = analytics_service.generate_report(report_request)
            return report.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export report: {str(e)}"
        ) from e


# =============================================================================
# Analytics Summary
# =============================================================================

@router.get("/summary/{user_id}", response_model=AnalyticsSummary)
async def get_analytics_summary(
    user_id: str,
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics summary for dashboard display.
    
    Returns a concise summary of key metrics and recent activity
    suitable for dashboard display.
    """
    try:
        summary = analytics_service.get_analytics_summary(user_id, time_period)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="analytics_summary_viewed",
            event_data={"time_period": time_period}
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting analytics summary for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics summary: {str(e)}"
        ) from e


# =============================================================================
# Performance Comparison
# =============================================================================

@router.get("/comparison/{user_id}", response_model=PerformanceComparison)
async def get_performance_comparison(
    user_id: str,
    current_period: str = Query("30d", description="Current period: 7d, 30d, 90d, 1y"),
    previous_period: str = Query("30d", description="Previous period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get performance comparison between two periods.
    
    Compares performance metrics between current and previous periods,
    showing improvement percentages and area-specific comparisons.
    """
    try:
        valid_periods = [tp.value for tp in TimePeriod]
        if current_period not in valid_periods or previous_period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {valid_periods}"
            )
        
        comparison = analytics_service.get_performance_comparison(
            user_id, current_period, previous_period
        )
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="performance_comparison_viewed",
            event_data={
                "current_period": current_period,
                "previous_period": previous_period
            }
        )
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance comparison for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance comparison: {str(e)}"
        ) from e


# =============================================================================
# Dashboard Metrics (aggregated)
# =============================================================================

@router.get("/metrics/{user_id}/dashboard")
async def get_dashboard_metrics(
    user_id: str,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get metrics optimized for dashboard display.
    
    Returns a curated set of metrics formatted for dashboard widgets,
    including key performance indicators and recent trends.
    """
    try:
        summary = analytics_service.get_analytics_summary(user_id)
        trend = analytics_service.get_trend_analysis(user_id, "average_score", "30d")
        
        dashboard_data = {
            "summary": summary.dict(),
            "trend": trend.dict(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="dashboard_metrics_viewed",
            event_data={}
        )
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard metrics for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard metrics: {str(e)}"
        ) from e


# =============================================================================
# Dimension Progress Tracking
# =============================================================================

@router.get("/dimensions/{user_id}", response_model=DimensionProgress)
async def get_dimension_progress(
    user_id: str,
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get progress tracking across all scoring dimensions.
    
    Returns per-dimension scores, trends, and time-series data points
    for the enhanced scoring rubric categories.
    """
    try:
        if time_period not in [tp.value for tp in TimePeriod]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {[tp.value for tp in TimePeriod]}"
            )
        
        progress = analytics_service.get_dimension_progress(user_id, time_period)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="dimension_progress_viewed",
            event_data={"time_period": time_period}
        )
        
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dimension progress for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dimension progress: {str(e)}"
        ) from e


# =============================================================================
# Session Comparison
# =============================================================================

@router.get("/compare-sessions/{user_id}", response_model=SessionComparisonResponse)
async def compare_sessions(
    user_id: str,
    session_a: str = Query(..., description="First session ID"),
    session_b: str = Query(..., description="Second session ID"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Compare two interview sessions side-by-side.
    
    Returns score deltas per category and an improvement summary.
    """
    try:
        comparison = analytics_service.compare_sessions(user_id, session_a, session_b)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="session_comparison_viewed",
            event_data={"session_a": session_a, "session_b": session_b}
        )
        
        return comparison
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error comparing sessions for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare sessions: {str(e)}"
        ) from e


# =============================================================================
# Advanced Filtered Search
# =============================================================================

@router.post("/sessions/{user_id}/filter", response_model=FilteredSessionsResponse)
async def get_filtered_sessions(
    user_id: str,
    filters: AnalyticsFilter,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get session analytics with advanced filtering.
    
    Supports filtering by role, date range, score range, session status,
    with pagination via limit/offset. The user_id in the filter body is
    ignored in favour of the path parameter.
    """
    try:
        # Override the filter's user_id with the path param for security
        filters.user_id = user_id

        result = analytics_service.get_filtered_sessions(user_id, filters)

        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="filtered_sessions_viewed",
            event_data={"filters": result.filters_applied}
        )

        return result

    except Exception as e:
        logger.error(f"Error filtering sessions for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to filter sessions: {str(e)}"
        ) from e


# =============================================================================
# Performance Heatmap
# =============================================================================

@router.get("/heatmap/{user_id}", response_model=PerformanceHeatmap)
async def get_performance_heatmap(
    user_id: str,
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get performance heatmap by day-of-week and hour-of-day.
    
    Returns a 7x24 grid of cells showing session counts and average scores
    for each day/hour combination, plus peak activity indicators.
    """
    try:
        if time_period not in [tp.value for tp in TimePeriod]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {[tp.value for tp in TimePeriod]}"
            )

        heatmap = analytics_service.get_performance_heatmap(user_id, time_period)

        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="heatmap_viewed",
            event_data={"time_period": time_period}
        )

        return heatmap

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting heatmap for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance heatmap: {str(e)}"
        ) from e


# =============================================================================
# Goal Management
# =============================================================================

@router.post("/goals/{user_id}", response_model=UserGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    user_id: str,
    goal_data: UserGoalCreate,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Create a new personal goal for interview preparation."""
    try:
        goal = analytics_service.create_goal(user_id, goal_data)
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="goal_created",
            event_data={"goal_type": goal_data.goal_type.value, "title": goal_data.title}
        )
        
        return goal
        
    except Exception as e:
        logger.error(f"Error creating goal for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create goal: {str(e)}"
        ) from e


@router.get("/goals/{user_id}", response_model=List[UserGoalResponse])
async def list_goals(
    user_id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: active, completed, expired, cancelled"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """List all goals for a user with optional status filter."""
    try:
        if status_filter and status_filter not in [s.value for s in GoalStatus]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in GoalStatus]}"
            )
        
        goals = analytics_service.list_goals(user_id, status_filter)
        return goals
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing goals for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list goals: {str(e)}"
        ) from e


@router.get("/goals/{user_id}/{goal_id}", response_model=UserGoalResponse)
async def get_goal(
    user_id: str,
    goal_id: str,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Get a specific goal by ID."""
    try:
        goal = analytics_service.get_goal(user_id, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting goal {goal_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get goal: {str(e)}"
        ) from e


@router.put("/goals/{user_id}/{goal_id}", response_model=UserGoalResponse)
async def update_goal(
    user_id: str,
    goal_id: str,
    updates: UserGoalUpdate,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Update an existing goal."""
    try:
        goal = analytics_service.update_goal(user_id, goal_id, updates)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="goal_updated",
            event_data={"goal_id": goal_id}
        )
        
        return goal
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating goal {goal_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update goal: {str(e)}"
        ) from e


@router.delete("/goals/{user_id}/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    user_id: str,
    goal_id: str,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """Delete a goal."""
    try:
        deleted = analytics_service.delete_goal(user_id, goal_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Goal not found")
        
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="goal_deleted",
            event_data={"goal_id": goal_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting goal {goal_id} for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete goal: {str(e)}"
        ) from e


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def analytics_health_check(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Health check for analytics service.
    
    Verifies that the analytics service is functioning correctly
    and can access required data sources.
    """
    try:
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "features": [
                "performance_metrics", "trend_analysis", "session_analytics",
                "report_generation", "csv_export", "analytics_summary",
                "performance_comparison", "dimension_progress",
                "session_comparison", "goal_management",
                "filtered_session_search", "performance_heatmap"
            ]
        }
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Analytics service unhealthy: {str(e)}"
        ) from e


# =============================================================================
# Question Analytics Endpoints
# =============================================================================

@router.get("/questions/generation-stats")
async def get_question_generation_statistics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get comprehensive statistics about question generation methods."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logs = db.query(QuestionGenerationLog).filter(
            and_(
                QuestionGenerationLog.created_at >= start_date,
                QuestionGenerationLog.created_at <= end_date
            )
        ).all()
        
        if not logs:
            return {
                "message": f"No generation data found for the last {days} days",
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "total_generations": 0
            }
        
        total_generations = len(logs)
        total_questions = sum(log.questions_generated for log in logs)
        
        method_stats = {}
        for log in logs:
            method = log.generation_method
            if method not in method_stats:
                method_stats[method] = {"count": 0, "questions": 0}
            method_stats[method]["count"] += 1
            method_stats[method]["questions"] += log.questions_generated
        
        avg_questions = total_questions / total_generations if total_generations > 0 else 0
        
        return {
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "total_generations": total_generations,
            "total_questions": total_questions,
            "average_questions_per_generation": round(avg_questions, 2),
            "method_breakdown": method_stats,
            "database_hit_rate": method_stats.get("database", {}).get("count", 0) / total_generations if total_generations > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting question generation statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get generation statistics: {str(e)}") from e


@router.get("/questions/database-performance")
async def get_database_performance_metrics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get database performance metrics for question retrieval."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        matches = db.query(QuestionMatch).filter(
            and_(
                QuestionMatch.created_at >= start_date,
                QuestionMatch.created_at <= end_date
            )
        ).all()
        
        if not matches:
            return {
                "message": f"No database performance data found for the last {days} days",
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "total_matches": 0
            }
        
        total_matches = len(matches)
        avg_response_time = sum(match.response_time for match in matches if match.response_time) / total_matches if total_matches > 0 else 0
        
        role_stats = {}
        for match in matches:
            role = match.role
            if role not in role_stats:
                role_stats[role] = {"count": 0, "avg_time": 0}
            role_stats[role]["count"] += 1
            if match.response_time:
                role_stats[role]["avg_time"] += match.response_time
        
        for role in role_stats:
            if role_stats[role]["count"] > 0:
                role_stats[role]["avg_time"] = role_stats[role]["avg_time"] / role_stats[role]["count"]
        
        return {
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "total_matches": total_matches,
            "average_response_time": round(avg_response_time, 3),
            "role_breakdown": role_stats,
            "performance_grade": "excellent" if avg_response_time < 0.1 else "good" if avg_response_time < 0.5 else "needs_improvement"
        }
        
    except Exception as e:
        logger.error(f"Error getting database performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database performance metrics: {str(e)}") from e


# =============================================================================
# Cost Analytics (Deprecated — services removed in microservice migration)
# =============================================================================

@router.get("/costs/summary", deprecated=True)
async def get_cost_summary(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
):
    """
    Get cost summary and optimization insights.
    
    **Deprecated**: Cost tracking has been moved to a separate microservice.
    This endpoint returns a placeholder response.
    """
    return {
        "status": "deprecated",
        "message": "Cost analytics have been migrated to the cost-tracking microservice. "
                   "Please use the dedicated cost-tracking API.",
        "period_days": days
    }


@router.get("/costs/optimization-effectiveness", deprecated=True)
async def get_optimization_effectiveness(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
):
    """
    Get optimization effectiveness metrics.
    
    **Deprecated**: Optimization tracking has been moved to a separate microservice.
    This endpoint returns a placeholder response.
    """
    return {
        "status": "deprecated",
        "message": "Optimization analytics have been migrated to the cost-tracking microservice. "
                   "Please use the dedicated cost-tracking API.",
        "period_days": days
    }
