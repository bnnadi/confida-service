"""
Authentication service for user management and JWT token handling.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.database.models import User, UserInvite
from app.models.schemas import TokenPayload, TokenType, UserRole
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

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
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        # Bcrypt has a 72-byte limit, so truncate if necessary
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str = UserRole.USER,
        organization_id: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> str:
        """Create a JWT access token."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "token_type": TokenType.ACCESS,
        }
        if organization_id:
            payload["organization_id"] = organization_id
        if organization_name:
            payload["organization"] = organization_name
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user_id: str, email: str, role: str = UserRole.USER) -> str:
        """Create a JWT refresh token."""
        now = datetime.utcnow()
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
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
    
    def get_user_by_id(self, user_id) -> Optional[User]:
        """Get user by ID (accepts str or UUID)."""
        from uuid import UUID
        try:
            uuid_id = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
            return self.db.query(User).filter(User.id == uuid_id).first()
        except (ValueError, TypeError):
            return None
    
    def create_user(
        self,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        role: str = UserRole.USER,
        organization_id: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> User:
        """Create a new user. Optionally assign organization and department (for invited users)."""
        # Check if user already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        # Truncate password to 72 bytes for bcrypt compatibility
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        hashed_password = self.get_password_hash(password)
        full_name = f"{first_name or ''} {last_name or ''}".strip()
        user = User(
            email=email,
            password_hash=hashed_password,
            name=full_name,
            role=role,
            is_active=True,
        )
        if organization_id:
            from uuid import UUID
            try:
                user.organization_id = UUID(organization_id)
            except (ValueError, TypeError):
                pass
        if department_id:
            from uuid import UUID
            try:
                user.department_id = UUID(department_id)
            except (ValueError, TypeError):
                pass
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"User created: {email}")
        return user

    def validate_invite(self, token: str) -> Dict[str, Any]:
        """
        Validate an invite token and return invite details for the signup form.
        Returns org name, inviter name, email. Raises HTTPException if invalid.
        """
        from uuid import UUID
        invite = self.db.query(UserInvite).filter(
            UserInvite.invite_token == token,
            UserInvite.status == "pending",
        ).first()
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite token invalid or expired"
            )
        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            invite.status = "expired"
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite has expired"
            )
        org = invite.organization
        inviter = invite.creator
        return {
            "email": invite.email,
            "organization_name": org.name if org else "",
            "inviter_name": inviter.name if inviter else "",
            "role": invite.role,
        }

    def accept_invite(self, token: str, password: str, name: str) -> User:
        """
        Accept an invite: create user with org/department/role, mark invite accepted, return user.
        """
        from uuid import UUID
        invite = self.db.query(UserInvite).filter(
            UserInvite.invite_token == token,
            UserInvite.status == "pending",
        ).first()
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invite token invalid or expired"
            )
        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            invite.status = "expired"
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invite has expired"
            )
        existing_user = self.get_user_by_email(invite.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        name_parts = (name or "").strip().split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        user = self.create_user(
            email=invite.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=invite.role,
            organization_id=str(invite.organization_id),
            department_id=str(invite.department_id) if invite.department_id else None,
        )
        invite.status = "accepted"
        self.db.commit()
        logger.info(f"Invite accepted: {invite.email} -> user {user.id}")
        return user
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        # Truncate password to 72 bytes for bcrypt compatibility
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        
        if not self.verify_password(password, user.password_hash):
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
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Truncate passwords to 72 bytes for bcrypt compatibility
        if len(current_password.encode('utf-8')) > 72:
            current_password = current_password[:72]
        if len(new_password.encode('utf-8')) > 72:
            new_password = new_password[:72]
            
        if not self.verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        user.password_hash = self.get_password_hash(new_password)
        self.db.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        return True
    
    def update_user_profile(self, user_id: str, **kwargs) -> User:
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
                if field in ['first_name', 'last_name']:
                    # Update the name field by combining first and last name
                    current_name = user.name or ''
                    name_parts = current_name.split(' ', 1)
                    if field == 'first_name':
                        user.name = f"{value} {name_parts[1] if len(name_parts) > 1 else ''}".strip()
                    else:  # last_name
                        user.name = f"{name_parts[0] if len(name_parts) > 0 else ''} {value}".strip()
                else:
                    setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"Profile updated for user: {user.email}")
        return user
    
    def deactivate_user(self, user_id: str) -> bool:
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
    
    def get_user_sessions(self, user_id: str, limit: int = 10, offset: int = 0):
        """Get user's interview sessions."""
        from app.database.models import InterviewSession
        from uuid import UUID
        
        try:
            uuid_id = UUID(user_id)
            return self.db.query(InterviewSession)\
                .filter(InterviewSession.user_id == uuid_id)\
                .order_by(InterviewSession.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
        except ValueError:
            return []
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics."""
        from app.database.models import InterviewSession, Question, Answer
        from sqlalchemy import func
        from uuid import UUID
        
        try:
            uuid_id = UUID(user_id)
            
            # Get session count
            session_count = self.db.query(InterviewSession)\
                .filter(InterviewSession.user_id == uuid_id)\
                .count()
            
            # Get question count
            question_count = self.db.query(Question)\
                .join(InterviewSession)\
                .filter(InterviewSession.user_id == uuid_id)\
                .count()
            
            # Get answer count
            answer_count = self.db.query(Answer)\
                .join(Question)\
                .join(InterviewSession)\
                .filter(InterviewSession.user_id == uuid_id)\
                .count()
            
            # Get average score (if available)
            avg_score = self.db.query(func.avg(Answer.score['overall'].astext.cast(func.Float)))\
                .join(Question)\
                .join(InterviewSession)\
                .filter(InterviewSession.user_id == uuid_id)\
                .scalar()
            
            return {
                "session_count": session_count,
                "question_count": question_count,
                "answer_count": answer_count,
                "average_score": float(avg_score) if avg_score else None
            }
        except ValueError:
            return {
                "session_count": 0,
                "question_count": 0,
                "answer_count": 0,
                "average_score": None
            }
