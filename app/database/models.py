"""
SQLAlchemy models for InterviewIQ database schema.
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import uuid

class User(Base):
    """User model for authentication and user management."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    user_performance = relationship("UserPerformance", back_populates="user", cascade="all, delete-orphan")
    analytics_events = relationship("AnalyticsEvent", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

class InterviewSession(Base):
    """Interview session model for managing complete interview sessions."""
    __tablename__ = "interview_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(255), nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String(50), default="active", nullable=False, index=True)
    total_questions = Column(Integer, default=0, nullable=False)
    completed_questions = Column(Integer, default=0, nullable=False)
    overall_score = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan")
    user_performance = relationship("UserPerformance", back_populates="session", cascade="all, delete-orphan")
    analytics_events = relationship("AnalyticsEvent", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<InterviewSession(id={self.id}, user_id={self.user_id}, role={self.role}, status={self.status})>"

class Question(Base):
    """Question model for storing interview questions."""
    __tablename__ = "questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_order = Column(Integer, nullable=False)
    difficulty_level = Column(String(20), default="medium", nullable=False)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("InterviewSession", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question(id={self.id}, session_id={self.session_id}, order={self.question_order})>"

class Answer(Base):
    """Answer model for storing user answers and analysis results."""
    __tablename__ = "answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    analysis_result = Column(JSONB, nullable=True)
    score = Column(JSONB, nullable=True)
    multi_agent_scores = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    question = relationship("Question", back_populates="answers")
    
    def __repr__(self):
        return f"<Answer(id={self.id}, question_id={self.question_id})>"

class UserPerformance(Base):
    """User performance tracking model for analytics."""
    __tablename__ = "user_performance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_category = Column(String(100), nullable=True)
    score = Column(Float, nullable=True)
    improvement_rate = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_performance")
    session = relationship("InterviewSession", back_populates="user_performance")
    
    def __repr__(self):
        return f"<UserPerformance(id={self.id}, user_id={self.user_id}, skill_category={self.skill_category})>"

class AnalyticsEvent(Base):
    """Analytics events model for tracking user interactions."""
    __tablename__ = "analytics_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSONB, nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="analytics_events")
    session = relationship("InterviewSession", back_populates="analytics_events")
    
    def __repr__(self):
        return f"<AnalyticsEvent(id={self.id}, user_id={self.user_id}, event_type={self.event_type})>"

class AgentConfiguration(Base):
    """Multi-agent configuration model for AI service management."""
    __tablename__ = "agent_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), unique=True, nullable=False)
    agent_type = Column(String(50), nullable=False)
    configuration = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AgentConfiguration(id={self.id}, agent_name={self.agent_name}, agent_type={self.agent_type})>"

# Create indexes for performance optimization
Index('idx_users_email', User.email)
Index('idx_sessions_user_id', InterviewSession.user_id)
Index('idx_sessions_status', InterviewSession.status)
Index('idx_questions_session_id', Question.session_id)
Index('idx_answers_question_id', Answer.question_id)
Index('idx_performance_user_id', UserPerformance.user_id)
Index('idx_analytics_user_id', AnalyticsEvent.user_id)
Index('idx_analytics_event_type', AnalyticsEvent.event_type)
Index('idx_analytics_created_at', AnalyticsEvent.created_at)

# JSONB indexes for flexible queries (PostgreSQL only)
# These will be created in migration scripts
