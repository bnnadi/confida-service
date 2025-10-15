"""
Connection Pool Monitoring and Metrics.

This module provides monitoring and metrics collection for database connection pools,
enabling observability and performance optimization.
"""
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConnectionEvent:
    """Represents a connection pool event."""
    timestamp: datetime
    event_type: str  # 'acquire', 'release', 'timeout', 'error'
    connection_id: Optional[str] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class PoolMetrics:
    """Connection pool metrics."""
    pool_size: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    average_connection_time_ms: float = 0.0
    max_connection_time_ms: float = 0.0
    min_connection_time_ms: float = float('inf')
    events_per_minute: float = 0.0
    pool_utilization_percent: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


class ConnectionPoolMonitor:
    """Monitors connection pool performance and health."""
    
    def __init__(self, max_events: int = 10000):
        self.events: List[ConnectionEvent] = []
        self.max_events = max_events
        self.metrics = PoolMetrics()
        self._lock = None  # Would be asyncio.Lock in async context
    
    def record_event(self, event_type: str, connection_id: Optional[str] = None, 
                    duration_ms: Optional[float] = None, error_message: Optional[str] = None):
        """Record a connection pool event."""
        event = ConnectionEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            connection_id=connection_id,
            duration_ms=duration_ms,
            error_message=error_message
        )
        
        self.events.append(event)
        
        # Keep only recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Update metrics
        self._update_metrics()
    
    def _update_metrics(self):
        """Update metrics based on recent events."""
        now = datetime.utcnow()
        recent_events = [
            event for event in self.events 
            if now - event.timestamp < timedelta(minutes=5)
        ]
        
        if not recent_events:
            return
        
        # Count events by type
        event_counts = {}
        connection_times = []
        
        for event in recent_events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            
            if event.duration_ms is not None:
                connection_times.append(event.duration_ms)
        
        # Update metrics
        self.metrics.total_requests = event_counts.get('acquire', 0)
        self.metrics.successful_requests = event_counts.get('release', 0)
        self.metrics.failed_requests = event_counts.get('error', 0)
        self.metrics.timeout_requests = event_counts.get('timeout', 0)
        
        # Calculate connection times
        if connection_times:
            self.metrics.average_connection_time_ms = sum(connection_times) / len(connection_times)
            self.metrics.max_connection_time_ms = max(connection_times)
            self.metrics.min_connection_time_ms = min(connection_times)
        
        # Calculate events per minute
        time_span_minutes = 5  # Last 5 minutes
        self.metrics.events_per_minute = len(recent_events) / time_span_minutes
        
        # Calculate pool utilization
        if self.metrics.pool_size > 0:
            self.metrics.pool_utilization_percent = (self.metrics.active_connections / self.metrics.pool_size) * 100
        
        self.metrics.last_updated = now
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as dictionary."""
        return {
            "pool_size": self.metrics.pool_size,
            "active_connections": self.metrics.active_connections,
            "idle_connections": self.metrics.idle_connections,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "timeout_requests": self.metrics.timeout_requests,
            "average_connection_time_ms": round(self.metrics.average_connection_time_ms, 2),
            "max_connection_time_ms": self.metrics.max_connection_time_ms,
            "min_connection_time_ms": self.metrics.min_connection_time_ms if self.metrics.min_connection_time_ms != float('inf') else 0,
            "events_per_minute": round(self.metrics.events_per_minute, 2),
            "pool_utilization_percent": round(self.metrics.pool_utilization_percent, 2),
            "last_updated": self.metrics.last_updated.isoformat()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get connection pool health status."""
        status = "healthy"
        warnings = []
        errors = []
        
        # Check utilization
        if self.metrics.pool_utilization_percent > 90:
            status = "warning"
            warnings.append("High pool utilization (>90%)")
        elif self.metrics.pool_utilization_percent > 95:
            status = "critical"
            errors.append("Critical pool utilization (>95%)")
        
        # Check error rate
        if self.metrics.total_requests > 0:
            error_rate = (self.metrics.failed_requests / self.metrics.total_requests) * 100
            if error_rate > 10:
                status = "warning"
                warnings.append(f"High error rate ({error_rate:.1f}%)")
            elif error_rate > 20:
                status = "critical"
                errors.append(f"Critical error rate ({error_rate:.1f}%)")
        
        # Check timeout rate
        if self.metrics.total_requests > 0:
            timeout_rate = (self.metrics.timeout_requests / self.metrics.total_requests) * 100
            if timeout_rate > 5:
                status = "warning"
                warnings.append(f"High timeout rate ({timeout_rate:.1f}%)")
            elif timeout_rate > 10:
                status = "critical"
                errors.append(f"Critical timeout rate ({timeout_rate:.1f}%)")
        
        # Check connection times
        if self.metrics.average_connection_time_ms > 1000:
            status = "warning"
            warnings.append(f"Slow connection times ({self.metrics.average_connection_time_ms:.0f}ms avg)")
        
        return {
            "status": status,
            "warnings": warnings,
            "errors": errors,
            "metrics": self.get_metrics()
        }
    
    def get_recent_events(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get recent events within specified time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent_events = [
            event for event in self.events 
            if event.timestamp >= cutoff
        ]
        
        return [
            {
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type,
                "connection_id": event.connection_id,
                "duration_ms": event.duration_ms,
                "error_message": event.error_message
            }
            for event in recent_events
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring dashboards."""
        return {
            "current_status": self.get_health_status(),
            "performance_metrics": {
                "throughput": self.metrics.events_per_minute,
                "latency": {
                    "average_ms": self.metrics.average_connection_time_ms,
                    "max_ms": self.metrics.max_connection_time_ms,
                    "min_ms": self.metrics.min_connection_time_ms
                },
                "reliability": {
                    "success_rate": (self.metrics.successful_requests / max(self.metrics.total_requests, 1)) * 100,
                    "error_rate": (self.metrics.failed_requests / max(self.metrics.total_requests, 1)) * 100,
                    "timeout_rate": (self.metrics.timeout_requests / max(self.metrics.total_requests, 1)) * 100
                }
            },
            "resource_utilization": {
                "pool_utilization_percent": self.metrics.pool_utilization_percent,
                "active_connections": self.metrics.active_connections,
                "idle_connections": self.metrics.idle_connections
            }
        }
    
    def reset_metrics(self):
        """Reset all metrics and events."""
        self.events.clear()
        self.metrics = PoolMetrics()
        logger.info("Connection pool metrics reset")


# Global monitor instance
_pool_monitor: Optional[ConnectionPoolMonitor] = None


def get_pool_monitor() -> ConnectionPoolMonitor:
    """Get the global connection pool monitor."""
    global _pool_monitor
    if _pool_monitor is None:
        _pool_monitor = ConnectionPoolMonitor()
    return _pool_monitor


def record_connection_event(event_type: str, connection_id: Optional[str] = None, 
                          duration_ms: Optional[float] = None, error_message: Optional[str] = None):
    """Record a connection pool event."""
    monitor = get_pool_monitor()
    monitor.record_event(event_type, connection_id, duration_ms, error_message)
