"""
Cost Tracking Service

Tracks AI service costs, token usage, and optimization effectiveness
to provide insights for cost management and optimization decisions.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.logger import get_logger
from app.database.models import Base
from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON

logger = get_logger(__name__)

@dataclass
class CostTrackingRequest:
    """Request data for cost tracking."""
    service: str
    operation: str
    tokens_used: int
    estimated_cost: float
    role: Optional[str] = None
    complexity_score: Optional[float] = None
    optimization_applied: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CostTrackingRecord(Base):
    """Database model for tracking AI service costs."""
    __tablename__ = "cost_tracking"
    
    id = Column(String(50), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    service = Column(String(50), nullable=False)
    operation = Column(String(100), nullable=False)
    tokens_used = Column(Integer, nullable=False)
    estimated_cost = Column(Float, nullable=False)
    actual_cost = Column(Float, nullable=True)
    role = Column(String(100), nullable=True)
    complexity_score = Column(Float, nullable=True)
    optimization_applied = Column(String(200), nullable=True)
    success = Column(String(10), nullable=False, default="success")
    error_message = Column(Text, nullable=True)
    request_metadata = Column(JSON, nullable=True)

@dataclass
class CostSummary:
    """Summary of costs for a time period."""
    total_cost: float
    total_tokens: int
    request_count: int
    average_cost_per_request: float
    cost_by_service: Dict[str, float]
    cost_by_operation: Dict[str, float]
    optimization_savings: float

class CostTracker:
    """
    Service for tracking and analyzing AI service costs and optimization effectiveness.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.cost_thresholds = {
            "daily_warning": 10.0,    # $10 per day
            "daily_critical": 50.0,   # $50 per day
            "monthly_warning": 200.0, # $200 per month
            "monthly_critical": 500.0 # $500 per month
        }
        
        # Service cost tracking
        self.service_costs = {
            "ollama": 0.0,
            "openai": 0.0,
            "anthropic": 0.0
        }
        
        # Optimization tracking
        self.optimization_stats = {
            "total_requests": 0,
            "optimized_requests": 0,
            "total_savings": 0.0,
            "average_savings_per_request": 0.0
        }
    
    def track_request(self, request: CostTrackingRequest) -> str:
        """
        Track an AI service request and its costs using dataclass input.
        
        Args:
            request: CostTrackingRequest dataclass with all tracking data
            
        Returns:
            Tracking ID for the request
        """
        try:
            # Generate tracking ID
            tracking_id = self._generate_tracking_id(request.service, request.operation)
            
            # Update in-memory tracking
            self._update_memory_tracking(request)
            
            # Store in database if available
            if self.db_session:
                self._store_database_record(tracking_id, request)
            
            # Check cost thresholds
            self._check_cost_thresholds()
            
            logger.info(f"Cost tracked: {request.service} {request.operation} - "
                       f"{request.tokens_used} tokens, ${request.estimated_cost:.4f}")
            
            return tracking_id
            
        except Exception as e:
            logger.error(f"Error tracking cost: {e}")
            return f"error_{int(time.time())}"
    
    def track_request_legacy(self, service: str, operation: str, tokens_used: int, 
                           estimated_cost: float, role: str = None, 
                           complexity_score: float = None, optimization_applied: str = None,
                           success: bool = True, error_message: str = None,
                           metadata: Dict[str, Any] = None) -> str:
        """
        Legacy method for backward compatibility.
        Converts parameters to CostTrackingRequest and calls track_request.
        """
        request = CostTrackingRequest(
            service=service,
            operation=operation,
            tokens_used=tokens_used,
            estimated_cost=estimated_cost,
            role=role,
            complexity_score=complexity_score,
            optimization_applied=optimization_applied,
            success=success,
            error_message=error_message,
            metadata=metadata
        )
        return self.track_request(request)
    
    def _update_memory_tracking(self, request: CostTrackingRequest):
        """Update in-memory tracking statistics."""
        self.service_costs[request.service] += request.estimated_cost
        self.optimization_stats["total_requests"] += 1
        
        if request.optimization_applied and request.optimization_applied != "fallback_default":
            self.optimization_stats["optimized_requests"] += 1
    
    def _store_database_record(self, tracking_id: str, request: CostTrackingRequest):
        """Store tracking record in database."""
        record = CostTrackingRecord(
            id=tracking_id,
            service=request.service,
            operation=request.operation,
            tokens_used=request.tokens_used,
            estimated_cost=request.estimated_cost,
            role=request.role,
            complexity_score=request.complexity_score,
            optimization_applied=request.optimization_applied,
            success="success" if request.success else "error",
            error_message=request.error_message,
            request_metadata=request.metadata or {}
        )
        
        self.db_session.add(record)
        self.db_session.commit()
    
    def get_cost_summary(self, days: int = 7) -> CostSummary:
        """Get cost summary for the specified number of days."""
        try:
            if not self.db_session:
                return self._get_in_memory_summary()
            
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Query database for cost data
            query = text("""
                SELECT 
                    service,
                    operation,
                    SUM(estimated_cost) as total_cost,
                    SUM(tokens_used) as total_tokens,
                    COUNT(*) as request_count
                FROM cost_tracking 
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                GROUP BY service, operation
            """)
            
            result = self.db_session.execute(query, {
                "start_date": start_date,
                "end_date": end_date
            }).fetchall()
            
            # Process results
            total_cost = 0.0
            total_tokens = 0
            total_requests = 0
            cost_by_service = {}
            cost_by_operation = {}
            
            for row in result:
                total_cost += row.total_cost
                total_tokens += row.total_tokens
                total_requests += row.request_count
                
                cost_by_service[row.service] = cost_by_service.get(row.service, 0) + row.total_cost
                cost_by_operation[row.operation] = cost_by_operation.get(row.operation, 0) + row.total_cost
            
            # Calculate optimization savings
            optimization_savings = self._calculate_optimization_savings(start_date, end_date)
            
            return CostSummary(
                total_cost=total_cost,
                total_tokens=total_tokens,
                request_count=total_requests,
                average_cost_per_request=total_cost / max(total_requests, 1),
                cost_by_service=cost_by_service,
                cost_by_operation=cost_by_operation,
                optimization_savings=optimization_savings
            )
            
        except Exception as e:
            logger.error(f"Error getting cost summary: {e}")
            return self._get_in_memory_summary()
    
    def get_optimization_effectiveness(self, days: int = 7) -> Dict[str, Any]:
        """Get optimization effectiveness metrics."""
        try:
            if not self.db_session:
                return self._get_in_memory_optimization_stats()
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Query optimization data
            query = text("""
                SELECT 
                    optimization_applied,
                    COUNT(*) as request_count,
                    AVG(estimated_cost) as avg_cost,
                    AVG(complexity_score) as avg_complexity,
                    AVG(tokens_used) as avg_tokens
                FROM cost_tracking 
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                GROUP BY optimization_applied
            """)
            
            result = self.db_session.execute(query, {
                "start_date": start_date,
                "end_date": end_date
            }).fetchall()
            
            optimization_data = {}
            for row in result:
                optimization_data[row.optimization_applied] = {
                    "request_count": row.request_count,
                    "average_cost": row.avg_cost,
                    "average_complexity": row.avg_complexity,
                    "average_tokens": row.avg_tokens
                }
            
            return {
                "optimization_breakdown": optimization_data,
                "total_requests": sum(row.request_count for row in result),
                "optimization_coverage": len([r for r in result if r.optimization_applied != "fallback_default"]) / max(len(result), 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting optimization effectiveness: {e}")
            return self._get_in_memory_optimization_stats()
    
    def _generate_tracking_id(self, service: str, operation: str) -> str:
        """Generate unique tracking ID."""
        timestamp = int(time.time())
        return f"{service}_{operation}_{timestamp}"
    
    def _check_cost_thresholds(self):
        """Check if costs exceed warning or critical thresholds."""
        daily_summary = self.get_cost_summary(days=1)
        monthly_summary = self.get_cost_summary(days=30)
        
        # Check daily thresholds
        if daily_summary.total_cost >= self.cost_thresholds["daily_critical"]:
            logger.critical(f"Daily cost threshold exceeded: ${daily_summary.total_cost:.2f}")
        elif daily_summary.total_cost >= self.cost_thresholds["daily_warning"]:
            logger.warning(f"Daily cost warning threshold: ${daily_summary.total_cost:.2f}")
        
        # Check monthly thresholds
        if monthly_summary.total_cost >= self.cost_thresholds["monthly_critical"]:
            logger.critical(f"Monthly cost threshold exceeded: ${monthly_summary.total_cost:.2f}")
        elif monthly_summary.total_cost >= self.cost_thresholds["monthly_warning"]:
            logger.warning(f"Monthly cost warning threshold: ${monthly_summary.total_cost:.2f}")
    
    def _calculate_optimization_savings(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate estimated savings from optimization."""
        try:
            # Get baseline cost (assuming no optimization)
            query = text("""
                SELECT 
                    AVG(estimated_cost) as avg_cost,
                    COUNT(*) as request_count
                FROM cost_tracking 
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                AND optimization_applied = 'fallback_default'
            """)
            
            baseline_result = self.db_session.execute(query, {
                "start_date": start_date,
                "end_date": end_date
            }).fetchone()
            
            if not baseline_result or baseline_result.request_count == 0:
                return 0.0
            
            # Get optimized cost
            query = text("""
                SELECT 
                    AVG(estimated_cost) as avg_cost,
                    COUNT(*) as request_count
                FROM cost_tracking 
                WHERE timestamp >= :start_date AND timestamp <= :end_date
                AND optimization_applied != 'fallback_default'
            """)
            
            optimized_result = self.db_session.execute(query, {
                "start_date": start_date,
                "end_date": end_date
            }).fetchone()
            
            if not optimized_result or optimized_result.request_count == 0:
                return 0.0
            
            # Calculate savings
            baseline_cost = baseline_result.avg_cost * baseline_result.request_count
            optimized_cost = optimized_result.avg_cost * optimized_result.request_count
            total_requests = baseline_result.request_count + optimized_result.request_count
            
            # Estimate what all requests would have cost without optimization
            estimated_baseline_total = baseline_result.avg_cost * total_requests
            actual_total = baseline_cost + optimized_cost
            
            savings = estimated_baseline_total - actual_total
            return max(savings, 0.0)
            
        except Exception as e:
            logger.error(f"Error calculating optimization savings: {e}")
            return 0.0
    
    def _get_in_memory_summary(self) -> CostSummary:
        """Get summary from in-memory data when database is not available."""
        total_cost = sum(self.service_costs.values())
        total_requests = self.optimization_stats["total_requests"]
        
        return CostSummary(
            total_cost=total_cost,
            total_tokens=0,  # Not tracked in memory
            request_count=total_requests,
            average_cost_per_request=total_cost / max(total_requests, 1),
            cost_by_service=self.service_costs.copy(),
            cost_by_operation={},
            optimization_savings=self.optimization_stats["total_savings"]
        )
    
    def _get_in_memory_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization stats from in-memory data."""
        return {
            "optimization_breakdown": {},
            "total_requests": self.optimization_stats["total_requests"],
            "optimization_coverage": (
                self.optimization_stats["optimized_requests"] / 
                max(self.optimization_stats["total_requests"], 1)
            )
        }
    
    def get_cost_alerts(self) -> List[Dict[str, Any]]:
        """Get current cost alerts and warnings."""
        alerts = []
        
        daily_summary = self.get_cost_summary(days=1)
        monthly_summary = self.get_cost_summary(days=30)
        
        # Daily alerts
        if daily_summary.total_cost >= self.cost_thresholds["daily_critical"]:
            alerts.append({
                "level": "critical",
                "type": "daily_cost",
                "message": f"Daily cost critical: ${daily_summary.total_cost:.2f}",
                "threshold": self.cost_thresholds["daily_critical"]
            })
        elif daily_summary.total_cost >= self.cost_thresholds["daily_warning"]:
            alerts.append({
                "level": "warning",
                "type": "daily_cost",
                "message": f"Daily cost warning: ${daily_summary.total_cost:.2f}",
                "threshold": self.cost_thresholds["daily_warning"]
            })
        
        # Monthly alerts
        if monthly_summary.total_cost >= self.cost_thresholds["monthly_critical"]:
            alerts.append({
                "level": "critical",
                "type": "monthly_cost",
                "message": f"Monthly cost critical: ${monthly_summary.total_cost:.2f}",
                "threshold": self.cost_thresholds["monthly_critical"]
            })
        elif monthly_summary.total_cost >= self.cost_thresholds["monthly_warning"]:
            alerts.append({
                "level": "warning",
                "type": "monthly_cost",
                "message": f"Monthly cost warning: ${monthly_summary.total_cost:.2f}",
                "threshold": self.cost_thresholds["monthly_warning"]
            })
        
        return alerts
