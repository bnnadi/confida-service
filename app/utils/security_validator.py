from fastapi import Request, HTTPException
from app.utils.logger import get_logger
import re
from typing import List, Dict, Any

logger = get_logger(__name__)

class SecurityValidator:
    """Security validation utilities for request sanitization."""
    
    # Suspicious patterns for various attack types
    SQL_INJECTION_PATTERNS = [
        r"';?\s*(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|ALTER|CREATE|EXEC|EXECUTE)",
        r"(OR|AND)\s+1\s*=\s*1",
        r"(OR|AND)\s+true",
        r"UNION\s+SELECT",
        r"';?\s*--",
        r"';?\s*/\*",
        r"';?\s*#",
        r"';?\s*;",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
        r"<style[^>]*>",
        r"expression\s*\(",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"\.\.%2f",
        r"\.\.%5c",
    ]
    
    @staticmethod
    def validate_request(request: Request) -> bool:
        """Validate request for security issues."""
        try:
            # Check query parameters
            SecurityValidator._validate_query_params(request)
            
            # Check path parameters
            SecurityValidator._validate_path(request)
            
            # Check headers
            SecurityValidator._validate_headers(request)
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security validation error: {e}")
            raise HTTPException(status_code=400, detail="Security validation failed")
    
    @staticmethod
    def _validate_query_params(request: Request):
        """Validate query parameters for malicious content."""
        for param_name, param_value in request.query_params.items():
            if SecurityValidator._contains_sql_injection(param_value):
                logger.warning(f"SQL injection attempt in query param '{param_name}' from {request.client.host}")
                raise HTTPException(status_code=400, detail="Invalid query parameter")
            
            if SecurityValidator._contains_xss(param_value):
                logger.warning(f"XSS attempt in query param '{param_name}' from {request.client.host}")
                raise HTTPException(status_code=400, detail="Invalid query parameter")
            
            if SecurityValidator._contains_path_traversal(param_value):
                logger.warning(f"Path traversal attempt in query param '{param_name}' from {request.client.host}")
                raise HTTPException(status_code=400, detail="Invalid query parameter")
    
    @staticmethod
    def _validate_path(request: Request):
        """Validate URL path for malicious content."""
        path = request.url.path
        
        if SecurityValidator._contains_path_traversal(path):
            logger.warning(f"Path traversal attempt in URL path from {request.client.host}")
            raise HTTPException(status_code=400, detail="Invalid URL path")
        
        # Check for suspicious file extensions
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js']
        if any(path.lower().endswith(ext) for ext in suspicious_extensions):
            logger.warning(f"Suspicious file extension in URL path from {request.client.host}")
            raise HTTPException(status_code=400, detail="Invalid file type")
    
    @staticmethod
    def _validate_headers(request: Request):
        """Validate request headers for security issues."""
        # Check User-Agent for suspicious patterns
        user_agent = request.headers.get("user-agent", "")
        if SecurityValidator._is_suspicious_user_agent(user_agent):
            logger.warning(f"Suspicious User-Agent from {request.client.host}: {user_agent}")
            # Don't block, just log
        
        # Check for suspicious headers
        suspicious_headers = ["x-forwarded-for", "x-real-ip", "x-originating-ip"]
        for header in suspicious_headers:
            if header in request.headers:
                value = request.headers[header]
                if SecurityValidator._contains_sql_injection(value) or SecurityValidator._contains_xss(value):
                    logger.warning(f"Malicious content in header '{header}' from {request.client.host}")
                    raise HTTPException(status_code=400, detail="Invalid header value")
    
    @staticmethod
    def _contains_sql_injection(text: str) -> bool:
        """Check if text contains SQL injection patterns."""
        text_lower = text.lower()
        for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def _contains_xss(text: str) -> bool:
        """Check if text contains XSS patterns."""
        for pattern in SecurityValidator.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return True
        return False
    
    @staticmethod
    def _contains_path_traversal(text: str) -> bool:
        """Check if text contains path traversal patterns."""
        for pattern in SecurityValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def _is_suspicious_user_agent(user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        suspicious_patterns = [
            r"sqlmap",
            r"nikto",
            r"nmap",
            r"masscan",
            r"zap",
            r"burp",
            r"w3af",
            r"havij",
            r"pangolin",
            r"acunetix",
            r"nessus",
            r"openvas",
        ]
        
        user_agent_lower = user_agent.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent_lower):
                return True
        return False
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize input text by removing potentially dangerous characters."""
        if not text:
            return text
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        # Limit length
        if len(text) > 10000:  # 10KB limit
            text = text[:10000]
            logger.warning("Input truncated due to length limit")
        
        return text
    
    @staticmethod
    def get_security_audit_report() -> Dict[str, Any]:
        """Generate security audit report."""
        return {
            "sql_injection_patterns": len(SecurityValidator.SQL_INJECTION_PATTERNS),
            "xss_patterns": len(SecurityValidator.XSS_PATTERNS),
            "path_traversal_patterns": len(SecurityValidator.PATH_TRAVERSAL_PATTERNS),
            "validation_enabled": True,
            "max_input_length": 10000,
            "suspicious_user_agent_detection": True
        }
    
    @staticmethod
    def get_security_recommendations() -> List[str]:
        """Get security recommendations."""
        return [
            "Ensure HTTPS is enabled in production",
            "Regularly update security headers configuration",
            "Monitor security audit logs",
            "Implement rate limiting for security endpoints",
            "Use strong CORS policies",
            "Enable HSTS preload for better security",
            "Regularly review and update CSP policies",
            "Implement request validation middleware",
            "Monitor for suspicious user agents",
            "Use secure session management"
        ]
