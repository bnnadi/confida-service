"""
Authentication middleware for protecting routes and extracting user information.
"""
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database.connection import get_db
from app.services.auth_service import AuthService
from app.models.schemas import TokenPayload, TokenType
from app.utils.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware:
    """Authentication middleware for protecting routes."""
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService(db)
    
    def get_current_user(self, credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[dict]:
        """
        Get current authenticated user from JWT token.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User information if authenticated, None otherwise
        """
        if not credentials:
            return None
        
        try:
            # Verify token
            token_payload = self.auth_service.verify_token(
                credentials.credentials, 
                token_type=TokenType.ACCESS
            )
            
            if not token_payload:
                return None
            
            # Get user from database
            user = self.auth_service.get_user_by_id(token_payload.sub)
            if not user or not user.is_active:
                return None
            
            # Return user information
            name_parts = (user.name or '').split(' ', 1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            return {
                "id": user.id,
                "email": user.email,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": user.name,
                "is_active": user.is_active,
                "is_verified": True,  # Default to True since field doesn't exist
                "role": "user",  # Default role, can be enhanced
                "created_at": user.created_at,
                "last_login": user.last_login
            }
            
        except Exception as e:
            logger.warning(f"Authentication error: {e}")
            return None
    
    def require_auth(self, credentials: Optional[HTTPAuthorizationCredentials] = None) -> dict:
        """
        Require authentication and return user information.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User information
            
        Raises:
            HTTPException: If not authenticated
        """
        user = self.get_current_user(credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    
    def require_admin(self, credentials: Optional[HTTPAuthorizationCredentials] = None) -> dict:
        """
        Require admin authentication.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            Admin user information
            
        Raises:
            HTTPException: If not authenticated or not admin
        """
        user = self.require_auth(credentials)
        
        # Check if user is admin (this can be enhanced with proper role checking)
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return user


# Dependency functions for FastAPI
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    FastAPI dependency to get current user (optional).
    
    Returns user information if authenticated, None otherwise.
    """
    auth_middleware = AuthMiddleware(db)
    return auth_middleware.get_current_user(credentials)


def get_current_user_required(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    FastAPI dependency to require authentication.
    
    Returns user information or raises 401 if not authenticated.
    """
    auth_middleware = AuthMiddleware(db)
    return auth_middleware.require_auth(credentials)


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    FastAPI dependency to require admin authentication.
    
    Returns admin user information or raises 401/403 if not authenticated/authorized.
    """
    auth_middleware = AuthMiddleware(db)
    return auth_middleware.require_admin(credentials)


# Utility functions for role checking
def check_user_permission(user: dict, required_role: str = "user") -> bool:
    """
    Check if user has required permission.
    
    Args:
        user: User information dictionary
        required_role: Required role level
        
    Returns:
        True if user has permission, False otherwise
    """
    if not user:
        return False
    
    # Simple role hierarchy (can be enhanced)
    role_hierarchy = {
        "user": 1,
        "moderator": 2,
        "admin": 3
    }
    
    user_role_level = role_hierarchy.get(user.get("role", "user"), 0)
    required_role_level = role_hierarchy.get(required_role, 0)
    
    return user_role_level >= required_role_level


def get_user_id_from_token(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[int]:
    """
    Extract user ID from JWT token without database lookup.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User ID if token is valid, None otherwise
    """
    if not credentials:
        return None
    
    try:
        from app.services.auth_service import AuthService
        from app.database.connection import SessionLocal
        
        db = SessionLocal()
        auth_service = AuthService(db)
        
        token_payload = auth_service.verify_token(
            credentials.credentials, 
            token_type=TokenType.ACCESS
        )
        
        if token_payload:
            return token_payload.sub
        
    except Exception as e:
        logger.warning(f"Error extracting user ID from token: {e}")
    
    return None


# Middleware for logging authentication attempts
async def auth_logging_middleware(request: Request, call_next):
    """
    Middleware to log authentication attempts.
    
    This can be added to the main app to log all authentication-related requests.
    """
    # Log the request
    logger.info(f"Auth request: {request.method} {request.url}")
    
    # Check for authorization header
    auth_header = request.headers.get("authorization")
    if auth_header:
        logger.info(f"Authorization header present: {auth_header[:20]}...")
    else:
        logger.info("No authorization header")
    
    # Process request
    response = await call_next(request)
    
    # Log response status
    logger.info(f"Auth response: {response.status_code}")
    
    return response
