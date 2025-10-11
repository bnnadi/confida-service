from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Request Models
class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")

class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    bio: Optional[str] = Field(None, description="User bio")
    experience_level: Optional[str] = Field(None, description="Experience level")
    preferred_industries: Optional[list] = Field(None, description="Preferred industries")
    skills: Optional[list] = Field(None, description="User skills")

# Response Models
class UserResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    bio: Optional[str]
    experience_level: Optional[str]
    preferred_industries: Optional[list]
    skills: Optional[list]
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")

class LoginResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse

class MessageResponse(BaseModel):
    message: str = Field(..., description="Response message")
    success: bool = Field(default=True, description="Operation success status")

# JWT Token Payload
class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    token_type: str = Field(..., description="Token type (access or refresh)")