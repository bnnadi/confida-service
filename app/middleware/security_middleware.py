from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
from app.utils.logger import get_logger
from typing import Optional
import uuid

logger = get_logger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
    
    async def dispatch(self, request: Request, call_next):
        # Add request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add security headers if enabled
        if self.settings.SECURITY_HEADERS_ENABLED:
            self._add_security_headers(request, response)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    def _add_security_headers(self, request: Request, response: Response):
        """Add comprehensive security headers to response."""
        try:
            # Add all configured security headers
            for header, value in self.settings.security_headers.items():
                response.headers[header] = value
            
            # Add CORS headers
            self._add_cors_headers(request, response)
            
            # Add additional security headers
            self._add_additional_security_headers(request, response)
            
            logger.debug(f"Security headers added to response for {request.url.path}")
            
        except Exception as e:
            logger.error(f"Error adding security headers: {e}")
    
    def _add_cors_headers(self, request: Request, response: Response):
        """Add CORS headers to response."""
        origin = request.headers.get("origin")
        
        if origin and origin in self.settings.CORS_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.settings.CORS_METHODS)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.settings.CORS_HEADERS)
            response.headers["Access-Control-Max-Age"] = str(self.settings.CORS_MAX_AGE)
            
            # Expose headers for client access
            expose_headers = self.settings.cors_config["expose_headers"]
            response.headers["Access-Control-Expose-Headers"] = ", ".join(expose_headers)
    
    def _add_additional_security_headers(self, request: Request, response: Response):
        """Add additional security headers based on request context."""
        # Add API version header
        if request.url.path.startswith("/api/"):
            response.headers["API-Version"] = "v1"
        
        # Add cache control for sensitive endpoints
        if self._is_sensitive_endpoint(request.url.path):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        # Add X-Request-ID for tracking
        if hasattr(request.state, 'request_id'):
            response.headers["X-Request-ID"] = request.state.request_id
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Check if endpoint contains sensitive data."""
        sensitive_paths = [
            "/api/v1/auth/",
            "/api/v1/admin/",
            "/api/v1/sessions/",
            "/api/v1/files/"
        ]
        return any(path.startswith(sensitive) for sensitive in sensitive_paths)
