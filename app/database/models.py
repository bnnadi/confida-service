"""
SQLAlchemy models for Confida database schema.
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
import uuid

class User(Base):
    """User model for authentication and user management."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user", index=True)  # user, admin, premium, enterprise
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    user_performance = relationship("UserPerformance", back_populates="user", cascade="all, delete-orphan")
    analytics_events = relationship("AnalyticsEvent", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("UserGoal", back_populates="user", cascade="all, delete-orphan")
    consents = relationship("UserConsent", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"

class InterviewSession(Base):
    """Interview session model for managing complete interview sessions."""
    __tablename__ = "interview_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(20), default="interview", nullable=False, index=True)  # "practice" or "interview"
    role = Column(String(255), nullable=False)
    job_description = Column(Text, nullable=True)  # Can be null for practice mode
    scenario_id = Column(String(100), nullable=True, index=True)  # For practice mode
    question_source = Column(String(50), nullable=False, default="generated")  # "scenario" or "generated"
    question_ids = Column(JSONB, nullable=True)  # Store question order and metadata
    job_context = Column(JSONB, nullable=True)  # Store job-specific context for interview mode
    status = Column(String(50), default="active", nullable=False, index=True)
    total_questions = Column(Integer, default=0, nullable=False)
    completed_questions = Column(Integer, default=0, nullable=False)
    overall_score = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    session_questions = relationship("SessionQuestion", back_populates="session", cascade="all, delete-orphan")  # Question bank relationship
    user_performance = relationship("UserPerformance", back_populates="session", cascade="all, delete-orphan")
    analytics_events = relationship("AnalyticsEvent", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<InterviewSession(id={self.id}, user_id={self.user_id}, role={self.role}, status={self.status})>"

class Question(Base):
    """Global question bank with rich metadata for intelligent question selection."""
    __tablename__ = "questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_text = Column(Text, nullable=False)
    question_metadata = Column(JSONB, nullable=False, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    difficulty_level = Column(String(20), default="medium", nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    compatible_roles = Column(JSONB, nullable=True)  # List of compatible roles
    required_skills = Column(JSONB, nullable=True)   # List of required skills
    industry_tags = Column(JSONB, nullable=True)     # List of industry tags
    usage_count = Column(Integer, default=0, nullable=False)
    average_score = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    ai_service_used = Column(String(50), nullable=True)
    generation_prompt_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    session_questions = relationship("SessionQuestion", back_populates="question", cascade="all, delete-orphan")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Question(id={self.id}, category={self.category}, difficulty={self.difficulty_level})>"

class SessionQuestion(Base):
    """Junction table linking sessions to questions from the global question bank."""
    __tablename__ = "session_questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_order = Column(Integer, nullable=False)
    session_specific_context = Column(JSONB, nullable=True)  # Session-specific modifications
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("InterviewSession", back_populates="session_questions")
    question = relationship("Question", back_populates="session_questions")
    
    def __repr__(self):
        return f"<SessionQuestion(id={self.id}, session_id={self.session_id}, question_id={self.question_id}, order={self.question_order})>"

class Answer(Base):
    """Answer model for storing user answers and analysis results."""
    __tablename__ = "answers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    analysis_result = Column(JSONB, nullable=True)
    score = Column(JSONB, nullable=True)
    multi_agent_scores = Column(JSONB, nullable=True)
    audio_file_id = Column(String(255), nullable=True, index=True)  # File ID of the user's answer audio recording
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    question = relationship("Question", back_populates="answers")
    
    def __repr__(self):
        return f"<Answer(id={self.id}, question_id={self.question_id})>"

class Scenario(Base):
    """Practice scenario model for managing interview practice scenarios."""
    __tablename__ = "scenarios"
    
    id = Column(String(100), primary_key=True)  # Use string ID for easier scenario identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    difficulty_level = Column(String(20), default="medium", nullable=False, index=True)
    compatible_roles = Column(JSONB, nullable=True)  # List of compatible roles
    question_ids = Column(JSONB, nullable=True)  # References to questions in the global question bank
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    usage_count = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<Scenario(id={self.id}, name={self.name}, category={self.category})>"

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


class UserGoal(Base):
    """User goals model for tracking personal interview preparation targets."""
    __tablename__ = "user_goals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal_type = Column(String(50), nullable=False, index=True)  # score, sessions, streak, completion_rate, dimension_score
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0, nullable=False)
    dimension = Column(String(100), nullable=True)  # For dimension_score goals
    target_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="active", nullable=False, index=True)  # active, completed, expired, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="goals")
    
    def __repr__(self):
        return f"<UserGoal(id={self.id}, user_id={self.user_id}, title={self.title}, status={self.status})>"


class UserConsent(Base):
    """User consent preferences for GDPR/CCPA compliance."""
    __tablename__ = "user_consents"
    __table_args__ = (UniqueConstraint("user_id", "consent_type", name="uq_user_consent_type"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False, index=True)  # essential, analytics, marketing
    granted = Column(Boolean, nullable=False)
    policy_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="consents")

    def __repr__(self):
        return f"<UserConsent(id={self.id}, user_id={self.user_id}, consent_type={self.consent_type}, granted={self.granted})>"


class ConsentHistory(Base):
    """Consent change history for audit trail."""
    __tablename__ = "consent_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)  # granted, withdrawn
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)

    def __repr__(self):
        return f"<ConsentHistory(id={self.id}, user_id={self.user_id}, consent_type={self.consent_type}, action={self.action})>"


# Create indexes for performance optimization
Index('idx_users_email', User.email)
Index('idx_sessions_user_id', InterviewSession.user_id)
Index('idx_sessions_status', InterviewSession.status)
Index('idx_answers_question_id', Answer.question_id)
Index('idx_performance_user_id', UserPerformance.user_id)
Index('idx_analytics_user_id', AnalyticsEvent.user_id)
Index('idx_analytics_event_type', AnalyticsEvent.event_type)
Index('idx_analytics_created_at', AnalyticsEvent.created_at)

# Question Bank indexes for performance optimization
Index('idx_questions_category', Question.category)
Index('idx_questions_difficulty', Question.difficulty_level)
Index('idx_questions_subcategory', Question.subcategory)
Index('idx_questions_usage_count', Question.usage_count)
Index('idx_session_questions_session_id', SessionQuestion.session_id)
Index('idx_session_questions_question_id', SessionQuestion.question_id)
Index('idx_session_questions_order', SessionQuestion.question_order)

# User Goals indexes
Index('idx_user_goals_user_id', UserGoal.user_id)
Index('idx_user_goals_status', UserGoal.status)
Index('idx_user_goals_goal_type', UserGoal.goal_type)

# Consent indexes
Index('idx_user_consents_user_id', UserConsent.user_id)
Index('idx_user_consents_consent_type', UserConsent.consent_type)
Index('idx_consent_history_user_id', ConsentHistory.user_id)
Index('idx_consent_history_consent_type', ConsentHistory.consent_type)
Index('idx_consent_history_created_at', ConsentHistory.created_at)

# JSONB indexes for flexible queries (PostgreSQL only)
# These will be created in migration scripts
