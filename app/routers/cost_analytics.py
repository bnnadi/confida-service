"""
Cost Analytics API Endpoints

Provides endpoints for viewing AI service costs, optimization effectiveness,
and cost management insights.
"""
from functools import wraps
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.cost_tracker import CostTracker
from app.services.smart_token_optimizer import SmartTokenOptimizer
from app.middleware.auth_middleware import get_current_user_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

def handle_cost_analytics_errors(func):
    """Decorator for consistent error handling in cost analytics endpoints."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to {func.__name__}: {str(e)}")
    return wrapper

router = APIRouter(prefix="/api/v1/analytics", tags=["cost-analytics"])

@router.get("/costs/summary")
@handle_cost_analytics_errors
async def get_cost_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get cost summary for the specified time period.
    
    Returns:
        - Total costs by service and operation
        - Cost trends and optimization savings
        - Cost per request metrics
    """
    cost_tracker = CostTracker(db)
    summary = cost_tracker.get_cost_summary(days=days)
    
    return {
        "period_days": days,
        "total_cost": summary.total_cost,
        "total_tokens": summary.total_tokens,
        "request_count": summary.request_count,
        "average_cost_per_request": summary.average_cost_per_request,
        "cost_by_service": summary.cost_by_service,
        "cost_by_operation": summary.cost_by_operation,
        "optimization_savings": summary.optimization_savings,
        "savings_percentage": (
            (summary.optimization_savings / max(summary.total_cost, 0.01)) * 100
            if summary.total_cost > 0 else 0
        )
    }

@router.get("/costs/optimization-effectiveness")
@handle_cost_analytics_errors
async def get_optimization_effectiveness(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get optimization effectiveness metrics.
    
    Returns:
        - Optimization coverage and success rates
        - Cost savings by optimization type
        - Performance metrics by complexity level
    """
    cost_tracker = CostTracker(db)
    effectiveness = cost_tracker.get_optimization_effectiveness(days=days)
    
    return {
        "period_days": days,
        "optimization_breakdown": effectiveness.get("optimization_breakdown", {}),
        "total_requests": effectiveness.get("total_requests", 0),
        "optimization_coverage": effectiveness.get("optimization_coverage", 0),
        "coverage_percentage": effectiveness.get("optimization_coverage", 0) * 100
    }

@router.get("/costs/alerts")
@handle_cost_analytics_errors
async def get_cost_alerts(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get current cost alerts and warnings.
    
    Returns:
        - Active cost alerts
        - Threshold warnings
        - Budget recommendations
    """
    cost_tracker = CostTracker(db)
    alerts = cost_tracker.get_cost_alerts()
    
    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "has_critical_alerts": any(alert["level"] == "critical" for alert in alerts),
        "has_warnings": any(alert["level"] == "warning" for alert in alerts)
    }

@router.get("/optimization/config")
@handle_cost_analytics_errors
async def get_optimization_config(
    current_user: dict = Depends(get_current_user_required)
):
    """
    Get current token optimization configuration.
    
    Returns:
        - Service configurations and cost structures
        - Role complexity mappings
        - Optimization rules and thresholds
    """
    optimizer = SmartTokenOptimizer()
    config = optimizer.get_optimization_stats()
    
    return {
        "service_configs": config["service_configs"],
        "role_complexity_map": config["role_complexity_map"],
        "technical_keywords_count": config["technical_keywords_count"],
        "industry_complexity_factors": config["industry_complexity_factors"],
        "complexity_weights": config.get("complexity_weights", {}),
        "constraints": config.get("constraints", {}),
        "config_source": config.get("config_source", "unknown")
    }

@router.post("/optimization/test")
@handle_cost_analytics_errors
async def test_optimization(
    role: str,
    job_description: str,
    service: str = Query("openai", description="AI service to test"),
    current_user: dict = Depends(get_current_user_required)
):
    """
    Test token optimization for a specific role and job description.
    
    Returns:
        - Optimal token count
        - Complexity analysis
        - Cost estimation
        - Optimization recommendations
    """
    optimizer = SmartTokenOptimizer()
    result = optimizer.optimize_request(
        role=role,
        job_description=job_description,
        service=service,
        target_questions=10
    )
    
    return {
        "role": role,
        "service": service,
        "optimal_tokens": result.optimal_tokens,
        "complexity_score": result.complexity_score,
        "estimated_cost": result.estimated_cost,
        "optimization_applied": result.optimization_applied,
        "confidence_score": result.confidence_score,
        "recommendations": {
            "use_optimization": result.confidence_score > 0.7,
            "cost_effective": result.estimated_cost < 0.05,
            "suitable_for_service": result.optimal_tokens <= 2000
        }
    }

@router.get("/costs/forecast")
@handle_cost_analytics_errors
async def get_cost_forecast(
    days: int = Query(30, ge=7, le=365, description="Forecast period in days"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get cost forecast based on current usage patterns.
    
    Returns:
        - Projected costs for the specified period
        - Growth trends and recommendations
        - Budget planning insights
    """
    cost_tracker = CostTracker(db)
    
    # Get historical data for trend analysis
    weekly_summary = cost_tracker.get_cost_summary(days=7)
    monthly_summary = cost_tracker.get_cost_summary(days=30)
    
    # Calculate growth rate
    if weekly_summary.total_cost > 0 and monthly_summary.total_cost > 0:
        weekly_rate = weekly_summary.total_cost / 7
        monthly_rate = monthly_summary.total_cost / 30
        growth_rate = (weekly_rate - monthly_rate) / monthly_rate if monthly_rate > 0 else 0
    else:
        growth_rate = 0
    
    # Project future costs
    current_daily_rate = weekly_summary.total_cost / 7
    projected_cost = current_daily_rate * days * (1 + growth_rate)
    
    return {
        "forecast_period_days": days,
        "current_daily_rate": current_daily_rate,
        "growth_rate": growth_rate,
        "projected_cost": projected_cost,
        "projected_monthly_cost": current_daily_rate * 30 * (1 + growth_rate),
        "recommendations": {
            "monitor_growth": abs(growth_rate) > 0.1,
            "optimize_usage": projected_cost > 100,
            "scale_budget": projected_cost > 500
        },
        "historical_data": {
            "weekly_cost": weekly_summary.total_cost,
            "monthly_cost": monthly_summary.total_cost,
            "optimization_savings": weekly_summary.optimization_savings
        }
    }
