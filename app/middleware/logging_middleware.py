"""
Request/response logging middleware for better debugging.
"""

import time
from fastapi import Request
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def log_requests(request: Request, call_next):
    """Enhanced request/response logging."""
    start_time = time.time()
    
    # Log request details
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    
    # Log request body for POST/PUT requests (disabled to prevent body consumption issues)
    # if request.method in ["POST", "PUT", "PATCH"]:
    #     try:
    #         body = await request.body()
    #         if body:
    #             logger.debug(f"Request body: {body.decode('utf-8')[:500]}...")
    #     except Exception as e:
    #         logger.debug(f"Could not log request body: {e}")
    
    # Process request
    response = await call_next(request)
    
    # Log response details
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    logger.debug(f"Response headers: {dict(response.headers)}")
    
    return response
