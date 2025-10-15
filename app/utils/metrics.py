"""
Prometheus metrics collection for API monitoring and performance tracking.
"""
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server, generate_latest
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

class MetricsCollector:
    """Prometheus metrics collector for comprehensive API monitoring."""
    
    def __init__(self):
        # Request metrics
        self.request_count = Counter(
            'api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float('inf')]
        )
        
        # Error metrics
        self.error_count = Counter(
            'api_errors_total',
            'Total API errors',
            ['error_type', 'endpoint']
        )
        
        # AI service metrics
        self.ai_service_requests = Counter(
            'ai_service_requests_total',
            'Total AI service requests',
            ['service', 'operation', 'status']
        )
        
        self.ai_service_duration = Histogram(
            'ai_service_duration_seconds',
            'AI service request duration in seconds',
            ['service', 'operation'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, float('inf')]
        )
        
        # Cache metrics
        self.cache_requests = Counter(
            'cache_requests_total',
            'Total cache requests',
            ['operation', 'result']
        )
        
        self.cache_duration = Histogram(
            'cache_duration_seconds',
            'Cache operation duration in seconds',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float('inf')]
        )
        
        # Rate limiting metrics
        self.rate_limit_hits = Counter(
            'rate_limit_hits_total',
            'Total rate limit hits',
            ['endpoint', 'client_type']
        )
        
        # Authentication metrics
        self.auth_attempts = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['method', 'result']
        )
        
        # System metrics
        self.active_connections = Gauge(
            'api_active_connections',
            'Active API connections'
        )
        
        self.active_sessions = Gauge(
            'api_active_sessions',
            'Active interview sessions'
        )
        
        # Database metrics
        self.db_connections = Gauge(
            'database_connections_active',
            'Active database connections'
        )
        
        self.db_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float('inf')]
        )
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record API request metrics."""
        self.request_count.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_error(self, error_type: str, endpoint: str):
        """Record API error metrics."""
        self.error_count.labels(
            error_type=error_type,
            endpoint=endpoint
        ).inc()
    
    def record_ai_service_request(self, service: str, operation: str, status: str, duration: float):
        """Record AI service request metrics."""
        self.ai_service_requests.labels(
            service=service,
            operation=operation,
            status=status
        ).inc()
        
        self.ai_service_duration.labels(
            service=service,
            operation=operation
        ).observe(duration)
    
    def record_cache_request(self, operation: str, result: str, duration: float):
        """Record cache operation metrics."""
        self.cache_requests.labels(
            operation=operation,
            result=result
        ).inc()
        
        self.cache_duration.labels(
            operation=operation
        ).observe(duration)
    
    def record_rate_limit_hit(self, endpoint: str, client_type: str):
        """Record rate limit hit."""
        self.rate_limit_hits.labels(
            endpoint=endpoint,
            client_type=client_type
        ).inc()
    
    def record_auth_attempt(self, method: str, result: str):
        """Record authentication attempt."""
        self.auth_attempts.labels(
            method=method,
            result=result
        ).inc()
    
    def record_db_query(self, operation: str, duration: float):
        """Record database query metrics."""
        self.db_query_duration.labels(
            operation=operation
        ).observe(duration)
    
    def set_active_connections(self, count: int):
        """Set active connections count."""
        self.active_connections.set(count)
    
    def set_active_sessions(self, count: int):
        """Set active sessions count."""
        self.active_sessions.set(count)
    
    def set_db_connections(self, count: int):
        """Set active database connections count."""
        self.db_connections.set(count)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics for API endpoints."""
        return {
            "request_count": self._get_counter_summary(self.request_count, "by_status", [200, 400, 401, 403, 404, 500]),
            "error_count": self._get_counter_summary(self.error_count, "by_type", ["client_error", "server_error", "internal_error"]),
            "ai_service_requests": self._get_counter_summary(self.ai_service_requests, "by_service", ["openai", "anthropic", "ollama"]),
            "cache_requests": {
                "total": self._get_total_count(self.cache_requests),
                "hit_rate": self._calculate_cache_hit_rate()
            },
            "system_metrics": {
                "active_connections": self.active_connections._value._value,
                "active_sessions": self.active_sessions._value._value,
                "db_connections": self.db_connections._value._value
            }
        }
    
    def _get_total_count(self, counter) -> int:
        """Get total count for a counter metric."""
        return sum(metric._value._value for metric in counter._metrics.values())
    
    def _get_counter_summary(self, counter, group_by: str, filter_values: list) -> Dict[str, Any]:
        """Get counter summary with grouping."""
        total = self._get_total_count(counter)
        grouped = {}
        
        for value in filter_values:
            grouped[str(value)] = sum(
                metric._value._value for metric in counter._metrics.values()
                if metric._labelvalues[0] == str(value)
            )
        
        return {"total": total, group_by: grouped}
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_requests = sum([
            metric._value._value for metric in self.cache_requests._metrics.values()
        ])
        
        if total_requests == 0:
            return 0.0
        
        hit_requests = sum([
            metric._value._value for metric in self.cache_requests._metrics.values()
            if metric._labelvalues[1] == "hit"
        ])
        
        return round((hit_requests / total_requests) * 100, 2)

# Global metrics collector instance
metrics = MetricsCollector()

def start_metrics_server():
    """Start Prometheus metrics server."""
    if settings.MONITORING_ENABLED:
        try:
            start_http_server(settings.PROMETHEUS_PORT)
            logger.info(f"✅ Prometheus metrics server started on port {settings.PROMETHEUS_PORT}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start Prometheus metrics server: {e}")
            return False
    else:
        logger.info("⚠️ Monitoring is disabled, skipping Prometheus server startup")
        return False

def get_metrics_output() -> str:
    """Get Prometheus metrics output."""
    return generate_latest().decode('utf-8')
