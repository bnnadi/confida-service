"""
Dashboard API endpoints for Confida.

This module provides REST API endpoints for dashboard data aggregation,
including overview, progress, analytics, metrics, trends, and insights.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from sqlalchemy.orm import Session

from app.services.database_service import get_db
from app.services.dashboard_service import DashboardService
from app.models.dashboard_models import (
    DashboardOverview, UserProgress, AnalyticsData, PerformanceMetrics,
    PerformanceTrends, UserInsights
)
from app.middleware.auth_middleware import get_current_user_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    """Dependency to get dashboard service."""
    return DashboardService(db)


@router.get("/overview/{user_id}", response_model=DashboardOverview)
async def get_dashboard_overview(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user_required),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get dashboard overview data.
    
    Returns comprehensive overview data including total sessions, average score,
    improvement rate, current streak, and recent activity.
    """
    try:
        # Verify user access
        if str(current_user.get("id")) != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user's data"
            )
        
        overview = dashboard_service.get_dashboard_overview(user_id, days)
        return overview
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard overview for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard overview: {str(e)}"
        ) from e


@router.get("/progress/{user_id}", response_model=UserProgress)
async def get_user_progress(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user_required),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get user progress data.
    
    Returns progress data including skill progression, difficulty progression,
    time progression, and overall trend.
    """
    try:
        # Verify user access
        if str(current_user.get("id")) != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user's data"
            )
        
        progress = dashboard_service.get_user_progress(user_id, days)
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user progress for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user progress: {str(e)}"
        ) from e


@router.get("/analytics/{user_id}", response_model=AnalyticsData)
async def get_analytics_data(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user_required),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get analytics data.
    
    Returns analytics data including performance metrics, skill breakdown,
    time analysis, and recommendations.
    """
    try:
        # Verify user access
        if str(current_user.get("id")) != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user's data"
            )
        
        analytics = dashboard_service.get_analytics_data(user_id, days)
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics data for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics data: {str(e)}"
        ) from e


@router.get("/metrics/{user_id}", response_model=PerformanceMetrics)
async def get_performance_metrics(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user_required),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get performance metrics.
    
    Returns detailed performance metrics including total sessions, completed sessions,
    average score, best/worst scores, completion rate, and session duration.
    """
    try:
        # Verify user access
        if str(current_user.get("id")) != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user's data"
            )
        
        metrics = dashboard_service.get_performance_metrics(user_id, days)
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance metrics for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        ) from e


@router.get("/trends/{user_id}", response_model=PerformanceTrends)
async def get_performance_trends(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user_required),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get performance trends.
    
    Returns performance trends including score trends, completion trends,
    skill-specific trends, and overall trend direction.
    """
    try:
        # Verify user access
        if str(current_user.get("id")) != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user's data"
            )
        
        trends = dashboard_service.get_performance_trends(user_id, days)
        return trends
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance trends for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance trends: {str(e)}"
        ) from e


@router.get("/insights/{user_id}", response_model=UserInsights)
async def get_user_insights(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: dict = Depends(get_current_user_required),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get user insights.
    
    Returns personalized insights including strengths, weaknesses, recommendations,
    milestones, and next goals.
    """
    try:
        # Verify user access
        if str(current_user.get("id")) != user_id and not current_user.get("is_admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this user's data"
            )
        
        insights = dashboard_service.get_user_insights(user_id, days)
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user insights for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user insights: {str(e)}"
        ) from e

