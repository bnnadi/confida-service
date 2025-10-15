"""
Monitoring middleware for comprehensive API request/response tracking.
"""
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.metrics import metrics
from app.utils.logger import get_logger
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting API metrics and monitoring request/response data."""
    
    def __init__(self, app):
        super().__init__(app)
        self.monitoring_enabled = settings.MONITORING_ENABLED
    
    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        if not self.monitoring_enabled:
            return await call_next(request)
        
        start_time = time.time()
        
        # Record active connection
        metrics.active_connections.inc()
        
        # Extract request information
        method = request.method
        endpoint = self._normalize_endpoint(request.url.path)
        client_ip = self._get_client_ip(request)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            metrics.record_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration
            )
            
            # Record errors
            if response.status_code >= 400:
                error_type = self._get_error_type(response.status_code)
                metrics.record_error(error_type, endpoint)
            
            # Log request details
            self._log_request(method, endpoint, response.status_code, duration, client_ip)
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            error_type = "internal_error"
            
            metrics.record_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration=duration
            )
            metrics.record_error(error_type, endpoint)
            
            # Log error
            logger.error(f"Request failed: {method} {endpoint} - {duration:.3f}s - Error: {str(e)}")
            raise
        
        finally:
            # Decrement active connections
            metrics.active_connections.dec()
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for consistent metrics."""
        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]
        
        # Normalize common patterns
        if path.startswith('/api/v1/'):
            # Keep API version in path
            return path
        elif path.startswith('/api/'):
            # Add version if missing
            return path.replace('/api/', '/api/v1/')
        else:
            # Keep as-is for non-API endpoints
            return path
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return 'unknown'
    
    def _get_error_type(self, status_code: int) -> str:
        """Get error type from status code."""
        if 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown_error"
    
    def _log_request(self, method: str, endpoint: str, status_code: int, duration: float, client_ip: str):
        """Log request details for monitoring."""
        # Log level based on status code and duration
        if status_code >= 500:
            log_level = "error"
        elif status_code >= 400:
            log_level = "warning"
        elif duration > 5.0:  # Slow requests
            log_level = "warning"
        else:
            log_level = "info"
        
        # Create log message
        message = f"{method} {endpoint} - {status_code} - {duration:.3f}s - {client_ip}"
        
        # Log with appropriate level
        if log_level == "error":
            logger.error(message)
        elif log_level == "warning":
            logger.warning(message)
        else:
            logger.info(message)

# Note: Database and AI service monitoring are handled directly in the services
# and through the main MonitoringMiddleware. Separate middleware classes are not needed
# as they would add unnecessary complexity without providing additional value.
