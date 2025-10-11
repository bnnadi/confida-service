from fastapi import APIRouter, Request, HTTPException, Depends
from app.config import get_settings
from app.utils.security_validator import SecurityValidator
from app.utils.logger import get_logger
from typing import Dict, Any, List
import time

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/security", tags=["security"])

@router.get("/headers")
async def get_security_headers(request: Request):
    """Get current security headers configuration."""
    try:
        return {
            "security_headers_enabled": settings.SECURITY_HEADERS_ENABLED,
            "cors_origins": settings.CORS_ORIGINS,
            "cors_methods": settings.CORS_METHODS,
            "cors_headers": settings.CORS_HEADERS,
            "csp_policy": settings.CSP_POLICY,
            "hsts_max_age": settings.HSTS_MAX_AGE,
            "hsts_include_subdomains": settings.HSTS_INCLUDE_SUBDOMAINS,
            "hsts_preload": settings.HSTS_PRELOAD,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "origin": request.headers.get("origin", "unknown"),
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error getting security headers: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve security headers configuration"
        )

@router.get("/test")
async def test_security_headers(request: Request):
    """Test security headers by returning a response with all headers."""
    try:
        # This endpoint will have security headers added by middleware
        return {
            "message": "Security headers test endpoint",
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "origin": request.headers.get("origin", "unknown"),
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "timestamp": time.time(),
            "note": "Check response headers for security headers"
        }
    except Exception as e:
        logger.error(f"Error in security test endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Security test failed"
        )

@router.post("/validate")
async def validate_request_security(request: Request):
    """Validate request for security issues."""
    try:
        # Validate the request
        SecurityValidator.validate_request(request)
        
        return {
            "valid": True,
            "message": "Request passed security validation",
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "timestamp": time.time()
        }
    except HTTPException as e:
        return {
            "valid": False,
            "message": e.detail,
            "status_code": e.status_code,
            "client_ip": request.client.host if request.client else "unknown",
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error validating request security: {e}")
        return {
            "valid": False,
            "message": "Security validation failed",
            "status_code": 500,
            "client_ip": request.client.host if request.client else "unknown",
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "timestamp": time.time()
        }

@router.get("/audit")
async def get_security_audit():
    """Get security audit report."""
    try:
        audit_report = SecurityValidator.get_security_audit_report()
        
        return {
            "audit_report": audit_report,
            "security_headers_config": {
                "enabled": settings.SECURITY_HEADERS_ENABLED,
                "hsts_configured": "Strict-Transport-Security" in settings.security_headers,
                "csp_configured": "Content-Security-Policy" in settings.security_headers,
                "cors_configured": len(settings.CORS_ORIGINS) > 0,
                "total_headers": len(settings.security_headers)
            },
            "recommendations": SecurityValidator.get_security_recommendations(),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error generating security audit: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate security audit report"
        )

@router.post("/sanitize")
async def sanitize_input(request: Request, text: str):
    """Sanitize input text."""
    try:
        sanitized_text = SecurityValidator.sanitize_input(text)
        
        return {
            "original_length": len(text),
            "sanitized_length": len(sanitized_text),
            "sanitized_text": sanitized_text,
            "changes_made": text != sanitized_text,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error sanitizing input: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to sanitize input"
        )

