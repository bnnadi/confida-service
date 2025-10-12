"""
Authentication service for user management and JWT token handling.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database.models import User
from app.models.schemas import TokenPayload, TokenType, UserRole
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class AuthService:
    """Service for handling authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def create_access_token(self, user_id: int, email: str, role: str = UserRole.USER) -> str:
        """Create a JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": TokenType.ACCESS
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user_id: int, email: str, role: str = UserRole.USER) -> str:
        """Create a JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": TokenType.REFRESH
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str, token_type: TokenType = TokenType.ACCESS) -> Optional[TokenPayload]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_payload = TokenPayload(**payload)
            
            # Verify token type
            if token_payload.token_type != token_type:
                logger.warning(f"Invalid token type: expected {token_type}, got {token_payload.token_type}")
                return None
            
            # Check expiration
            if datetime.utcnow().timestamp() > token_payload.exp:
                logger.warning("Token has expired")
                return None
            
            return token_payload
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create_user(self, email: str, password: str, first_name: Optional[str] = None, 
                   last_name: Optional[str] = None) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = self.get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_verified=False  # Email verification can be added later
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"User created: {email}")
        return user
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is deactivated"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not self.verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        user.hashed_password = self.get_password_hash(new_password)
        self.db.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        return True
    
    def update_user_profile(self, user_id: int, **kwargs) -> User:
        """Update user profile information."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update allowed fields
        allowed_fields = ['first_name', 'last_name', 'bio', 'experience_level', 
                         'preferred_industries', 'skills']
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Profile updated for user: {user.email}")
        return user
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = False
        self.db.commit()
        
        logger.info(f"User deactivated: {user.email}")
        return True
    
    def get_user_sessions(self, user_id: int, limit: int = 10, offset: int = 0):
        """Get user's interview sessions."""
        from app.database.models import InterviewSession
        
        return self.db.query(InterviewSession)\
            .filter(InterviewSession.user_id == user_id)\
            .order_by(InterviewSession.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics."""
        from app.database.models import InterviewSession, Question, Answer
        from sqlalchemy import func
        
        # Get session count
        session_count = self.db.query(InterviewSession)\
            .filter(InterviewSession.user_id == user_id)\
            .count()
        
        # Get question count
        question_count = self.db.query(Question)\
            .join(InterviewSession)\
            .filter(InterviewSession.user_id == user_id)\
            .count()
        
        # Get answer count
        answer_count = self.db.query(Answer)\
            .join(Question)\
            .join(InterviewSession)\
            .filter(InterviewSession.user_id == user_id)\
            .count()
        
        # Get average score (if available)
        avg_score = self.db.query(func.avg(Answer.score['overall'].astext.cast(func.Float)))\
            .join(Question)\
            .join(InterviewSession)\
            .filter(InterviewSession.user_id == user_id)\
            .scalar()
        
        return {
            "session_count": session_count,
            "question_count": question_count,
            "answer_count": answer_count,
            "average_score": float(avg_score) if avg_score else None
        }
