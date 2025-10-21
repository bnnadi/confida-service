from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.middleware.enhanced_rate_limiter import EnhancedRateLimiter
from app.exceptions import RateLimitExceededError
from typing import Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with per-endpoint and per-user-type configuration."""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = EnhancedRateLimiter()
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limiting(request):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get user type from request state (set by auth middleware)
        user_type = getattr(request.state, 'user_type', 'free')
        
        # Check rate limit
        try:
            rate_limit_result = self.rate_limiter.check_rate_limit(
                request=request,
                client_id=client_id,
                user_type=user_type
            )
            
            if not rate_limit_result["allowed"]:
                return self._create_rate_limit_response(rate_limit_result)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers only if rate limiting is enabled
            if rate_limit_result.get("reason") != "rate_limiting_disabled":
                self._add_rate_limit_headers(response, rate_limit_result)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in rate limiting middleware: {e}")
            # Continue with request if rate limiting fails
            return await call_next(request)
    
    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        skip_paths = [
            "/health",
            "/ready",
            "/docs",
            "/openapi.json",
            "/metrics"
        ]
        
        return request.url.path in skip_paths
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get user ID from authentication
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # Try to get user ID from request headers
        user_id_header = request.headers.get("X-User-ID")
        if user_id_header:
            return f"user:{user_id_header}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _create_rate_limit_response(self, rate_limit_result: dict) -> Response:
        """Create rate limit exceeded response."""
        reason = rate_limit_result.get("reason", "rate_limit_exceeded")
        retry_after = rate_limit_result.get("retry_after", 3600)
        
        error_message = self._get_error_message(reason, rate_limit_result)
        
        response = Response(
            content=error_message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            media_type="application/json"
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["effective_limit"])
        response.headers["X-RateLimit-Window"] = str(rate_limit_result["effective_window"])
        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["Retry-After"] = str(retry_after)
        response.headers["X-RateLimit-Reason"] = reason
        
        return response
    
    def _get_error_message(self, reason: str, rate_limit_result: dict) -> str:
        """Get appropriate error message based on rate limit reason."""
        if reason == "endpoint_rate_limit_exceeded":
            return f"Rate limit exceeded for endpoint {rate_limit_result['endpoint']}. " \
                   f"Limit: {rate_limit_result['effective_limit']} requests per {rate_limit_result['effective_window']} seconds."
        elif reason == "user_type_rate_limit_exceeded":
            return f"Rate limit exceeded for user type {rate_limit_result['user_type']}. " \
                   f"Limit: {rate_limit_result['effective_limit']} requests per {rate_limit_result['effective_window']} seconds."
        else:
            return f"Rate limit exceeded. Limit: {rate_limit_result['effective_limit']} requests per {rate_limit_result['effective_window']} seconds."
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_result: dict):
        """Add rate limit headers to response."""
        response.headers["X-RateLimit-Limit"] = str(rate_limit_result["effective_limit"])
        response.headers["X-RateLimit-Window"] = str(rate_limit_result["effective_window"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["effective_remaining"])
        response.headers["X-RateLimit-Client-ID"] = rate_limit_result["client_id"]
        response.headers["X-RateLimit-User-Type"] = rate_limit_result["user_type"]
        
        # Add endpoint-specific headers
        response.headers["X-RateLimit-Endpoint-Limit"] = str(rate_limit_result["endpoint_limit"]["requests"])
        response.headers["X-RateLimit-Endpoint-Window"] = str(rate_limit_result["endpoint_limit"]["window"])
        response.headers["X-RateLimit-User-Limit"] = str(rate_limit_result["user_limit"]["requests"])
        response.headers["X-RateLimit-User-Window"] = str(rate_limit_result["user_limit"]["window"])
