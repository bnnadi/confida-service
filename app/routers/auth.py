"""
Authentication router for user registration, login, and management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.models import Organization
from typing import Optional
from app.services.database_service import get_db
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import get_current_user_required, get_current_user
from app.models.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    PasswordChangeRequest,
    TokenRefreshRequest,
    UserProfileUpdateRequest,
    AuthStatusResponse,
    AuthErrorResponse
)
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Creates a new user with the provided email and password.
    Returns user information without sensitive data.
    """
    auth_service = AuthService(db)
    
    # Create user
    user = auth_service.create_user(
        email=request.email,
        password=request.password,
        first_name=request.name.split(' ', 1)[0] if request.name else '',
        last_name=request.name.split(' ', 1)[1] if ' ' in request.name else ''
    )
    
    logger.info(f"User registered successfully: {user.email}")
    
    # Convert User model to UserResponse
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else "",
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return access tokens.
    
    Validates user credentials and returns JWT access and refresh tokens.
    """
    auth_service = AuthService(db)
    
    # Authenticate user
    user = auth_service.authenticate_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create tokens with user's role from database
    user_role = user.role if hasattr(user, 'role') else "user"
    org_id = str(user.organization_id) if getattr(user, 'organization_id', None) else None
    org_name = None
    if org_id:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        org_name = org.name if org else None
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user_role,
        organization_id=org_id,
        organization_name=org_name,
    )
    refresh_token = auth_service.create_refresh_token(
        user_id=str(user.id),
        email=user.email,
        role=user_role,
    )
    
    logger.info(f"User logged in successfully: {user.email}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=30 * 60  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    
    Validates the refresh token and returns a new access token.
    """
    auth_service = AuthService(db)
    
    # Verify refresh token
    token_payload = auth_service.verify_token(request.refresh_token, token_type="refresh")
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Get user
    user = auth_service.get_user_by_id(token_payload.sub)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new access token with role from database (source of truth)
    user_role = user.role if hasattr(user, 'role') else (token_payload.role if hasattr(token_payload, 'role') else "user")
    org_id = str(user.organization_id) if getattr(user, 'organization_id', None) else None
    org_name = None
    if org_id:
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        org_name = org.name if org else None
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user_role,
        organization_id=org_id,
        organization_name=org_name,
    )
    
    logger.info(f"Token refreshed for user: {user.email}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Keep the same refresh token
        expires_in=30 * 60  # 30 minutes
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user_required)
):
    """
    Get current authenticated user information.
    
    Returns the profile information of the currently authenticated user.
    """
    return UserResponse(
        id=str(current_user["id"]),
        email=current_user["email"],
        name=current_user.get("full_name") or current_user.get("name") or f"{current_user.get('first_name', '')} {current_user.get('last_name', '')}".strip(),
        is_active=current_user.get("is_active", True),
        created_at=current_user["created_at"].isoformat() if current_user.get("created_at") else "",
        last_login=current_user["last_login"].isoformat() if current_user.get("last_login") else None
    )


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile information.
    
    Allows users to update their profile information like name, bio, etc.
    """
    auth_service = AuthService(db)
    
    # Update profile
    user = auth_service.update_user_profile(
        user_id=current_user["id"],
        **request.model_dump(exclude_unset=True)
    )
    
    logger.info(f"Profile updated for user: {user.email}")
    return user


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Change user password.
    
    Allows authenticated users to change their password by providing current password.
    """
    auth_service = AuthService(db)
    
    # Change password
    auth_service.change_password(
        user_id=current_user["id"],
        current_password=request.current_password,
        new_password=request.new_password
    )
    
    logger.info(f"Password changed for user: {current_user['email']}")
    return {"message": "Password changed successfully"}


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Get authentication status.
    
    Returns whether the user is authenticated and basic user info if so.
    """
    if current_user:
        return AuthStatusResponse(
            authenticated=True,
            user=current_user,
            expires_at=None  # Could be calculated from token
        )
    else:
        return AuthStatusResponse(authenticated=False)


@router.get("/stats")
async def get_user_stats(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get user statistics.
    
    Returns interview session statistics for the current user.
    """
    auth_service = AuthService(db)
    stats = auth_service.get_user_stats(current_user["id"])
    
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "stats": stats
    }


@router.get("/sessions")
async def get_user_sessions(
    limit: int = Query(10, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db)
):
    """
    Get user's interview sessions.
    
    Returns a paginated list of the user's interview sessions.
    """
    auth_service = AuthService(db)
    sessions = auth_service.get_user_sessions(
        user_id=current_user["id"],
        limit=limit,
        offset=offset
    )
    
    return {
        "sessions": sessions,
        "limit": limit,
        "offset": offset,
        "total": len(sessions)
    }


# Logout endpoint (token blacklisting would be implemented here)
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_user(
    current_user: dict = Depends(get_current_user_required)
):
    """
    Logout user.
    
    In a production system, this would blacklist the token.
    For now, it's a placeholder.
    """
    logger.info(f"User logged out: {current_user.get('email', 'unknown') if current_user else 'unknown'}")
    return {"message": "Logged out successfully"}
