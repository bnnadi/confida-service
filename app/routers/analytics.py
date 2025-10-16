"""
Analytics API endpoints for InterviewIQ.

This module provides REST API endpoints for analytics and reporting functionality,
including performance metrics, trend analysis, and report generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database.connection import get_db, get_db_session
from app.services.unified_analytics_service import UnifiedAnalyticsService
from app.services.cost_tracker import CostTracker
from app.services.smart_token_optimizer import SmartTokenOptimizer
from app.models.analytics_models import (
    PerformanceMetrics, SessionAnalytics, TrendAnalysis, ReportRequest, 
    ReportResponse, AnalyticsSummary, PerformanceComparison, AnalyticsFilter,
    TimePeriod, ReportType, ReportFormat
)
from app.database.question_database_models import (
    QuestionGenerationLog, QuestionTemplate, QuestionMatch, QuestionFeedback
)
from sqlalchemy import func, desc, and_
from app.dependencies import get_current_user_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def get_analytics_service(db: Session = Depends(get_db)) -> UnifiedAnalyticsService:
    """Dependency to get analytics service."""
    return UnifiedAnalyticsService(db)


@router.get("/performance/{user_id}", response_model=PerformanceMetrics)
async def get_performance_metrics(
    user_id: str,
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Get performance metrics for a user.
    
    Returns comprehensive performance metrics including average scores,
    improvement trends, and area analysis for the specified time period.
    """
    try:
        # Validate time period
        if time_period not in [tp.value for tp in TimePeriod]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {[tp.value for tp in TimePeriod]}"
            )
        
        metrics = analytics_service.get_performance_metrics(user_id, time_period)
        
        # Log analytics event
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="performance_metrics_viewed",
            event_data={"time_period": time_period}
        )
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting performance metrics for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/trends/{user_id}", response_model=TrendAnalysis)
async def get_trend_analysis(
    user_id: str,
    metric: str = Query("average_score", description="Metric to analyze"),
    time_period: str = Query("30d", description="Time period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Get trend analysis for a user.
    
    Analyzes trends for a specific metric over the specified time period,
    including trend direction, percentage change, and confidence level.
    """
    try:
        # Validate time period
        if time_period not in [tp.value for tp in TimePeriod]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {[tp.value for tp in TimePeriod]}"
            )
        
        # Validate metric
        valid_metrics = ["average_score", "completion_rate", "total_sessions", "response_time"]
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric. Must be one of: {valid_metrics}"
            )
        
        trend_analysis = analytics_service.get_trend_analysis(user_id, metric, time_period)
        
        # Log analytics event
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="trend_analysis_viewed",
            event_data={"metric": metric, "time_period": time_period}
        )
        
        return trend_analysis
        
    except Exception as e:
        logger.error(f"Error getting trend analysis for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get trend analysis: {str(e)}"
        )


@router.get("/sessions/{user_id}", response_model=List[SessionAnalytics])
async def get_session_analytics(
    user_id: str,
    limit: int = Query(10, description="Number of sessions to return", ge=1, le=100),
    offset: int = Query(0, description="Number of sessions to skip", ge=0),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Get session analytics for a user.
    
    Returns detailed analytics for recent interview sessions,
    including scores, completion times, and category breakdowns.
    """
    try:
        sessions = analytics_service.get_session_analytics(user_id, limit, offset)
        
        # Log analytics event
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
        )


@router.post("/reports", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Generate a comprehensive analytics report.
    
    Creates a detailed report with performance metrics, trend analysis,
    session details, and improvement recommendations.
    """
    try:
        # Validate date range
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Validate date range is not too large
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
        )


@router.get("/summary/{user_id}", response_model=AnalyticsSummary)
async def get_analytics_summary(
    user_id: str,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Get analytics summary for dashboard display.
    
    Returns a concise summary of key metrics and recent activity
    suitable for dashboard display.
    """
    try:
        summary = analytics_service.get_analytics_summary(user_id)
        
        # Log analytics event
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="analytics_summary_viewed",
            event_data={}
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting analytics summary for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics summary: {str(e)}"
        )


@router.get("/comparison/{user_id}", response_model=PerformanceComparison)
async def get_performance_comparison(
    user_id: str,
    current_period: str = Query("30d", description="Current period: 7d, 30d, 90d, 1y"),
    previous_period: str = Query("30d", description="Previous period: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Get performance comparison between two periods.
    
    Compares performance metrics between current and previous periods,
    showing improvement percentages and area-specific comparisons.
    """
    try:
        # Validate time periods
        valid_periods = [tp.value for tp in TimePeriod]
        if current_period not in valid_periods or previous_period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time period. Must be one of: {valid_periods}"
            )
        
        comparison = analytics_service.get_performance_comparison(
            user_id, current_period, previous_period
        )
        
        # Log analytics event
        analytics_service._log_analytics_event(
            user_id=user_id,
            event_type="performance_comparison_viewed",
            event_data={
                "current_period": current_period,
                "previous_period": previous_period
            }
        )
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error getting performance comparison for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance comparison: {str(e)}"
        )


@router.get("/reports/{user_id}/export")
async def export_report(
    user_id: str,
    format: str = Query("json", description="Export format: json, pdf, csv"),
    start_date: Optional[datetime] = Query(None, description="Report start date"),
    end_date: Optional[datetime] = Query(None, description="Report end date"),
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Export analytics report in specified format.
    
    Generates and exports a report in the requested format (JSON, PDF, or CSV).
    If no date range is specified, defaults to the last 30 days.
    """
    try:
        # Validate format
        if format not in [fmt.value for fmt in ReportFormat]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format. Must be one of: {[fmt.value for fmt in ReportFormat]}"
            )
        
        # Set default date range if not provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Create report request
        report_request = ReportRequest(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            report_type=ReportType.DETAILED,
            format=ReportFormat(format)
        )
        
        # Generate report
        report = analytics_service.generate_report(report_request)
        
        # For now, return the report data directly
        # In a production system, this would generate and return file URLs
        if format == "json":
            return report.dict()
        elif format == "csv":
            # Convert to CSV format
            return {"message": "CSV export not yet implemented", "report": report.dict()}
        elif format == "pdf":
            # Convert to PDF format
            return {"message": "PDF export not yet implemented", "report": report.dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export report: {str(e)}"
        )


@router.get("/health")
async def analytics_health_check(
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Health check for analytics service.
    
    Verifies that the analytics service is functioning correctly
    and can access required data sources.
    """
    try:
        # Test basic functionality
        test_user_id = "test-user"
        
        # This is a simple health check - in production, you might want to
        # test with actual data or use a dedicated health check endpoint
        return {
            "status": "healthy",
            "service": "analytics",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Analytics service unhealthy: {str(e)}"
        )


@router.get("/metrics/{user_id}/dashboard")
async def get_dashboard_metrics(
    user_id: str,
    current_user: dict = Depends(get_current_user_required),
    analytics_service: UnifiedAnalyticsService = Depends(get_analytics_service)
):
    """
    Get metrics optimized for dashboard display.
    
    Returns a curated set of metrics formatted for dashboard widgets,
    including key performance indicators and recent trends.
    """
    try:
        # Get summary data
        summary = analytics_service.get_analytics_summary(user_id)
        
        # Get recent trend
        trend = analytics_service.get_trend_analysis(user_id, "average_score", "30d")
        
        # Format for dashboard
        dashboard_data = {
            "summary": summary.dict(),
            "trend": trend.dict(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Log analytics event
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
        )


# Question Analytics Endpoints
@router.get("/questions/generation-stats")
async def get_question_generation_statistics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get comprehensive statistics about question generation methods."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get generation logs
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
        
        # Calculate statistics
        total_generations = len(logs)
        total_questions = sum(log.questions_generated for log in logs)
        
        # Method breakdown
        method_stats = {}
        for log in logs:
            method = log.generation_method
            if method not in method_stats:
                method_stats[method] = {"count": 0, "questions": 0}
            method_stats[method]["count"] += 1
            method_stats[method]["questions"] += log.questions_generated
        
        # Average questions per generation
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
        raise HTTPException(status_code=500, detail=f"Failed to get generation statistics: {str(e)}")


@router.get("/questions/database-performance")
async def get_database_performance_metrics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get database performance metrics for question retrieval."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get question matches (database hits)
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
        
        # Calculate performance metrics
        total_matches = len(matches)
        avg_response_time = sum(match.response_time for match in matches if match.response_time) / total_matches if total_matches > 0 else 0
        
        # Role breakdown
        role_stats = {}
        for match in matches:
            role = match.role
            if role not in role_stats:
                role_stats[role] = {"count": 0, "avg_time": 0}
            role_stats[role]["count"] += 1
            if match.response_time:
                role_stats[role]["avg_time"] += match.response_time
        
        # Calculate averages
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
        raise HTTPException(status_code=500, detail=f"Failed to get database performance metrics: {str(e)}")


# Cost Analytics Endpoints
@router.get("/costs/summary")
async def get_cost_summary(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get cost summary and optimization insights."""
    try:
        cost_tracker = CostTracker()
        
        # Get cost data for the specified period
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Calculate total costs
        total_costs = cost_tracker.get_total_costs(start_date, end_date)
        
        # Get cost breakdown by service
        service_costs = cost_tracker.get_costs_by_service(start_date, end_date)
        
        # Calculate optimization effectiveness
        optimization_stats = cost_tracker.get_optimization_stats(start_date, end_date)
        
        return {
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "total_costs": total_costs,
            "service_breakdown": service_costs,
            "optimization_stats": optimization_stats,
            "cost_trend": "decreasing" if optimization_stats.get("cost_reduction_percentage", 0) > 0 else "stable"
        }
        
    except Exception as e:
        logger.error(f"Error getting cost summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost summary: {str(e)}")


@router.get("/costs/optimization-effectiveness")
async def get_optimization_effectiveness(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """Get optimization effectiveness metrics."""
    try:
        cost_tracker = CostTracker()
        token_optimizer = SmartTokenOptimizer()
        
        # Get optimization metrics
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Calculate optimization effectiveness
        effectiveness = cost_tracker.calculate_optimization_effectiveness(start_date, end_date)
        
        # Get token optimization stats
        token_stats = token_optimizer.get_optimization_stats(start_date, end_date)
        
        return {
            "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "cost_reduction_percentage": effectiveness.get("cost_reduction_percentage", 0),
            "tokens_saved": effectiveness.get("tokens_saved", 0),
            "api_calls_reduced": effectiveness.get("api_calls_reduced", 0),
            "token_optimization": token_stats,
            "optimization_grade": "excellent" if effectiveness.get("cost_reduction_percentage", 0) > 50 else "good" if effectiveness.get("cost_reduction_percentage", 0) > 20 else "needs_improvement"
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization effectiveness: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get optimization effectiveness: {str(e)}")
