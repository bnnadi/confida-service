"""
Authentication models and schemas for user management.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class TokenType(str, Enum):
    """Token types for JWT authentication."""
    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(str, Enum):
    """User roles in the system."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


# Request models
class UserRegistrationRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    first_name: Optional[str] = Field(None, max_length=100, description="User first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User last name")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")


# Response models
class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """Response model for user information."""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    full_name: Optional[str] = Field(None, description="User full name")
    is_active: bool = Field(..., description="User active status")
    is_verified: bool = Field(..., description="User verification status")
    role: str = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login date")
    
    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    first_name: Optional[str] = Field(None, max_length=100, description="User first name")
    last_name: Optional[str] = Field(None, max_length=100, description="User last name")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")
    experience_level: Optional[str] = Field(None, description="Experience level")
    preferred_industries: Optional[str] = Field(None, description="Preferred industries")
    skills: Optional[str] = Field(None, description="User skills")


class AuthStatusResponse(BaseModel):
    """Response model for authentication status."""
    authenticated: bool = Field(..., description="Authentication status")
    user: Optional[UserResponse] = Field(None, description="User information if authenticated")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


# Internal models for JWT payload
class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: int = Field(..., description="User ID (subject)")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="User role")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    token_type: TokenType = Field(..., description="Token type")


# Error response models
class AuthErrorResponse(BaseModel):
    """Error response model for authentication failures."""
    detail: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")