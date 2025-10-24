from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from app.utils.logger import get_logger
import time
import os
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

class FileUploadSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for file upload security and monitoring."""
    
    def __init__(self, app, max_file_size: int = 50 * 1024 * 1024):  # 50MB default
        super().__init__(app)
        self.max_file_size = max_file_size
        self.upload_stats = {
            "total_uploads": 0,
            "total_size": 0,
            "failed_uploads": 0,
            "blocked_uploads": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process file upload requests with security checks."""
        
        # Only process file upload endpoints
        if not self._is_file_upload_endpoint(request.url.path):
            return await call_next(request)
        
        # Security checks
        try:
            await self._perform_security_checks(request)
        except HTTPException as e:
            self.upload_stats["blocked_uploads"] += 1
            logger.warning(f"File upload blocked: {e.detail}")
            return Response(
                content=f'{{"detail": "{e.detail}"}}',
                status_code=e.status_code,
                media_type="application/json"
            )
        
        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            
            # Update stats on successful upload
            if response.status_code == 200:
                self.upload_stats["total_uploads"] += 1
                # Note: File size would be calculated in the endpoint
                logger.info(f"File upload successful: {request.url.path}")
            else:
                self.upload_stats["failed_uploads"] += 1
                logger.warning(f"File upload failed with status {response.status_code}: {request.url.path}")
            
            # Add processing time header
            processing_time = time.time() - start_time
            response.headers["X-File-Processing-Time"] = str(processing_time)
            
            return response
            
        except Exception as e:
            self.upload_stats["failed_uploads"] += 1
            logger.error(f"File upload error: {e}")
            raise
    
    def _is_file_upload_endpoint(self, path: str) -> bool:
        """Check if the request is to a file upload endpoint."""
        upload_paths = [
            "/api/v1/files/upload",
            "/api/v1/files/audio/upload",
            "/api/v1/files/documents/upload",
            "/api/v1/files/images/upload",
            "/api/v1/speech/transcribe"
        ]
        return any(path.startswith(upload_path) for upload_path in upload_paths)
    
    async def _perform_security_checks(self, request: Request) -> None:
        """Perform security checks on file upload requests."""
        
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {self.max_file_size // (1024*1024)}MB"
                )
        
        # Check for suspicious headers
        suspicious_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "x-originating-ip",
            "x-remote-ip",
            "x-remote-addr"
        ]
        
        for header in suspicious_headers:
            if header in request.headers:
                logger.warning(f"Suspicious header detected: {header}")
        
        # Check user agent
        user_agent = request.headers.get("user-agent", "").lower()
        if not user_agent or len(user_agent) < 10:
            logger.warning("Suspicious or missing user agent")
        
        # Rate limiting check (basic)
        client_ip = request.client.host if request.client else "unknown"
        # In a real implementation, you'd check against a rate limiting service
        
        # Check for multipart content type
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("multipart/form-data"):
            raise HTTPException(
                status_code=400,
                detail="Invalid content type. Expected multipart/form-data"
            )

class FileUploadMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring file upload metrics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            "uploads_by_type": {},
            "uploads_by_size": {"small": 0, "medium": 0, "large": 0},
            "error_rates": {},
            "processing_times": []
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor file upload metrics."""
        
        if not self._is_file_upload_endpoint(request.url.path):
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            processing_time = time.time() - start_time
            self._record_metrics(request, response, processing_time)
            
            return response
            
        except Exception as e:
            # Record error metrics
            self._record_error_metrics(request, str(e))
            raise
    
    def _is_file_upload_endpoint(self, path: str) -> bool:
        """Check if the request is to a file upload endpoint."""
        return path.startswith("/api/v1/files/") or path.startswith("/api/v1/speech/")
    
    def _record_metrics(self, request: Request, response: Response, processing_time: float) -> None:
        """Record file upload metrics."""
        # Record processing time
        self.metrics["processing_times"].append(processing_time)
        
        # Keep only last 1000 processing times
        if len(self.metrics["processing_times"]) > 1000:
            self.metrics["processing_times"] = self.metrics["processing_times"][-1000:]
        
        # Record by endpoint
        endpoint = request.url.path
        if endpoint not in self.metrics["error_rates"]:
            self.metrics["error_rates"][endpoint] = {"success": 0, "error": 0}
        
        if response.status_code < 400:
            self.metrics["error_rates"][endpoint]["success"] += 1
        else:
            self.metrics["error_rates"][endpoint]["error"] += 1
    
    def _record_error_metrics(self, request: Request, error: str) -> None:
        """Record error metrics."""
        endpoint = request.url.path
        if endpoint not in self.metrics["error_rates"]:
            self.metrics["error_rates"][endpoint] = {"success": 0, "error": 0}
        
        self.metrics["error_rates"][endpoint]["error"] += 1
        logger.error(f"File upload error on {endpoint}: {error}")
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        # Calculate average processing time
        if self.metrics["processing_times"]:
            avg_processing_time = sum(self.metrics["processing_times"]) / len(self.metrics["processing_times"])
        else:
            avg_processing_time = 0
        
        return {
            **self.metrics,
            "average_processing_time": avg_processing_time,
            "total_requests": sum(
                rates["success"] + rates["error"] 
                for rates in self.metrics["error_rates"].values()
            )
        }

class FileUploadCleanupMiddleware(BaseHTTPMiddleware):
    """Middleware for periodic file cleanup."""
    
    def __init__(self, app, cleanup_interval: int = 3600):  # 1 hour default
        super().__init__(app)
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check if cleanup is needed."""
        
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            await self._perform_cleanup()
            self.last_cleanup = current_time
        
        return await call_next(request)
    
    async def _perform_cleanup(self) -> None:
        """Perform file cleanup."""
        try:
            # This would integrate with the FileService cleanup method
            logger.info("Performing file cleanup...")
            # In a real implementation, you'd call file_service.cleanup_expired_files()
        except Exception as e:
            logger.error(f"File cleanup error: {e}")

def create_file_upload_middleware_stack(app):
    """Create the complete file upload middleware stack."""
    # Add security middleware
    app.add_middleware(FileUploadSecurityMiddleware, max_file_size=settings.FILE_MAX_SIZE_AUDIO)
    
    # Add monitoring middleware
    app.add_middleware(FileUploadMonitoringMiddleware)
    
    # Add cleanup middleware
    app.add_middleware(FileUploadCleanupMiddleware, cleanup_interval=settings.FILE_CLEANUP_INTERVAL_HOURS * 3600)
    
    return app
