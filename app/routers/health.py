"""
Health check and metrics endpoints for monitoring and observability.
"""
from fastapi import APIRouter, Response, HTTPException, Depends
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
import time
from app.utils.metrics import metrics, get_metrics_output
from app.config import get_settings
from app.utils.logger import get_logger
from app.database.connection import get_db
from app.database.async_connection import get_async_db
from app.services.unified_ai_service import UnifiedAIService, AsyncUnifiedAIService
from app.dependencies import get_ai_service, get_async_ai_service
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])
settings = get_settings()

@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Confida API",
        "version": "1.0.0",
        "monitoring_enabled": settings.MONITORING_ENABLED
    }

@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check(
    db: Session = Depends(get_db)
):
    """Detailed health check with system status."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Confida API",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database health check
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # AI services health check
    ai_services_status = _check_ai_services()
    health_status["checks"]["ai_services"] = ai_services_status
    if ai_services_status["status"] == "unhealthy":
        health_status["status"] = "unhealthy"
    
    # Cache and monitoring health checks
    cache_status = _check_cache_system()
    monitoring_status = _check_monitoring_system()
    
    health_status["checks"]["cache"] = cache_status
    health_status["checks"]["monitoring"] = monitoring_status
    
    if cache_status["status"] == "unhealthy" or monitoring_status["status"] == "unhealthy":
        health_status["status"] = "unhealthy"
    
    return health_status

@router.get("/metrics")
async def get_prometheus_metrics():
    """Get Prometheus metrics in the standard format."""
    _require_monitoring_enabled()
    
    try:
        metrics_output = get_metrics_output()
        return Response(
            content=metrics_output,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")

@router.get("/stats", response_model=Dict[str, Any])
async def get_api_stats():
    """Get API statistics and performance metrics."""
    _require_monitoring_enabled()
    
    try:
        stats = metrics.get_metrics_summary()
        stats["system_info"] = _get_system_info()
        return stats
    except Exception as e:
        logger.error(f"Error getting API stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get API statistics")

@router.get("/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    try:
        # Check if the service is ready to accept traffic
        # This could include checks for database connectivity, external services, etc.
        
        # For now, we'll do a simple database check
        db = next(get_db())
        db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

@router.get("/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    # Simple liveness check - if this endpoint responds, the service is alive
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/startup")
async def startup_check():
    """Kubernetes startup probe endpoint."""
    # Check if the service has finished starting up
    # This could include initialization checks, migrations, etc.
    
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Service has completed startup"
    }

@router.post("/metrics/reset")
async def reset_metrics():
    """Reset all metrics (for testing purposes)."""
    _require_monitoring_enabled()
    
    try:
        logger.info("Metrics reset requested")
        return {
            "status": "success",
            "message": "Metrics reset requested (Prometheus metrics are cumulative)",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error resetting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset metrics")

@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics():
    """Get performance metrics and system health indicators."""
    _require_monitoring_enabled()
    
    try:
        stats = metrics.get_metrics_summary()
        performance_data = _calculate_performance_indicators(stats)
        performance_data["timestamp"] = datetime.utcnow().isoformat()
        return performance_data
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")

# Helper functions for health checks
def _check_ai_services() -> Dict[str, Any]:
    """Check AI services configuration."""
    try:
        services = {
            "openai": "configured" if settings.OPENAI_API_KEY else "not_configured",
            "anthropic": "configured" if settings.ANTHROPIC_API_KEY else "not_configured",
            "ollama": "configured" if settings.OLLAMA_BASE_URL else "not_configured"
        }
        return {"status": "healthy", "services": services}
    except Exception as e:
        return {"status": "unhealthy", "message": f"AI services check failed: {str(e)}"}

def _check_cache_system() -> Dict[str, Any]:
    """Check cache system status."""
    try:
        if settings.CACHE_ENABLED:
            return {
                "status": "healthy",
                "backend": settings.CACHE_BACKEND,
                "message": "Cache system enabled"
            }
        else:
            return {"status": "disabled", "message": "Cache system disabled"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Cache check failed: {str(e)}"}

def _check_monitoring_system() -> Dict[str, Any]:
    """Check monitoring system status."""
    try:
        if settings.MONITORING_ENABLED:
            return {
                "status": "healthy",
                "prometheus_port": settings.PROMETHEUS_PORT,
                "message": "Monitoring system enabled"
            }
        else:
            return {"status": "disabled", "message": "Monitoring system disabled"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Monitoring check failed: {str(e)}"}

def _require_monitoring_enabled():
    """Require monitoring to be enabled, raise exception if not."""
    if not settings.MONITORING_ENABLED:
        raise HTTPException(status_code=404, detail="Monitoring is disabled")

def _get_system_info() -> Dict[str, Any]:
    """Get system information for stats endpoint."""
    return {
        "monitoring_enabled": settings.MONITORING_ENABLED,
        "prometheus_port": settings.PROMETHEUS_PORT,
        "cache_enabled": settings.CACHE_ENABLED,
        "cache_backend": settings.CACHE_BACKEND,
        "timestamp": datetime.utcnow().isoformat()
    }

def _calculate_performance_indicators(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate performance indicators from stats."""
    total_requests = stats["request_count"]["total"]
    total_errors = stats["error_count"]["total"]
    
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
    cache_hit_rate = stats["cache_requests"]["hit_rate"]
    
    # Performance status logic
    if error_rate > 5:
        performance_status = "poor"
    elif error_rate > 1:
        performance_status = "fair"
    elif cache_hit_rate < 50:
        performance_status = "good"
    else:
        performance_status = "excellent"
    
    return {
        "performance_status": performance_status,
        "error_rate": round(error_rate, 2),
        "cache_hit_rate": cache_hit_rate,
        "total_requests": total_requests,
        "total_errors": total_errors,
        "active_connections": stats["system_metrics"]["active_connections"],
        "active_sessions": stats["system_metrics"]["active_sessions"]
    }


# AI Service Health Endpoints
@router.get("/ai-services")
async def get_ai_service_health(ai_service: UnifiedAIService = Depends(get_ai_service)):
    """Get comprehensive AI service health status."""
    try:
        if not ai_service:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        health_status = ai_service.get_service_health()
        
        return {
            "overall_status": "healthy" if all(
                service["status"] == "healthy" for service in health_status.values()
            ) else "degraded",
            "services": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ai-health"
        }
        
    except Exception as e:
        logger.error(f"AI service health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI service health check failed: {str(e)}")


@router.get("/ai-services/detailed")
async def get_detailed_ai_health(ai_service: UnifiedAIService = Depends(get_ai_service)):
    """Get detailed AI service diagnostics and health information."""
    try:
        if not ai_service:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # Get detailed health information
        detailed_health = await ai_service.health_check()
        
        return {
            "detailed_health": detailed_health,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "ai-health-detailed"
        }
        
    except Exception as e:
        logger.error(f"Detailed AI health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detailed AI health check failed: {str(e)}")


@router.post("/ai-services/recovery")
async def trigger_ai_service_recovery(ai_service: UnifiedAIService = Depends(get_ai_service)):
    """Manually trigger AI service recovery and circuit breaker reset."""
    try:
        if not ai_service:
            raise HTTPException(status_code=503, detail="AI service not available")
        
        # Reset circuit breakers
        for service_name, circuit_breaker in ai_service.circuit_breakers.items():
            circuit_breaker.reset()
            ai_service.service_health[service_name].status = "healthy"
            ai_service.service_health[service_name].consecutive_failures = 0
        
        logger.info("AI service recovery triggered - circuit breakers reset")
        
        return {
            "message": "AI service recovery completed",
            "timestamp": datetime.utcnow().isoformat(),
            "services_reset": list(ai_service.circuit_breakers.keys())
        }
        
    except Exception as e:
        logger.error(f"AI service recovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI service recovery failed: {str(e)}")
