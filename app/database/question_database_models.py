"""
Question Database Models for Phase 2: Gradual Database Enhancement

This module defines the database schema for storing and managing
interview questions to reduce AI service calls and optimize costs.
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class QuestionTemplate(Base):
    """Template for interview questions with metadata for intelligent matching."""
    
    __tablename__ = "question_templates"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Question content
    question_text = Column(Text, nullable=False, index=True)
    question_type = Column(String(50), nullable=False, index=True)  # technical, behavioral, system_design, etc.
    difficulty_level = Column(String(20), nullable=False, index=True)  # easy, medium, hard
    
    # Role and context matching
    target_roles = Column(JSON, nullable=True)  # ["software_engineer", "data_scientist", "product_manager"]
    seniority_levels = Column(JSON, nullable=True)  # ["junior", "mid", "senior"]
    industries = Column(JSON, nullable=True)  # ["fintech", "healthcare", "ecommerce"]
    
    # Technical context
    required_skills = Column(JSON, nullable=True)  # ["python", "react", "aws"]
    technical_domains = Column(JSON, nullable=True)  # ["backend", "frontend", "devops", "data"]
    complexity_keywords = Column(JSON, nullable=True)  # ["microservices", "scalability", "security"]
    
    # Quality and usage metrics
    quality_score = Column(Float, default=0.0)  # 0.0 to 1.0
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)  # Based on user feedback
    last_used = Column(DateTime, nullable=True)
    
    # Metadata
    source = Column(String(50), default="ai_generated")  # ai_generated, human_curated, imported
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Indexes for performance (removed JSON indexes for PostgreSQL compatibility)
    __table_args__ = (
        Index('idx_question_type_difficulty', 'question_type', 'difficulty_level'),
        Index('idx_quality_usage', 'quality_score', 'usage_count'),
        Index('idx_active_created', 'is_active', 'created_at'),
    )

class QuestionMatch(Base):
    """Track successful matches between user requests and question templates."""
    
    __tablename__ = "question_matches"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Match details
    question_template_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_request_hash = Column(String(64), nullable=False, index=True)  # Hash of role + job_description
    
    # Request context
    role = Column(String(200), nullable=False)
    job_description_hash = Column(String(64), nullable=False)  # Hash of job description
    complexity_score = Column(Float, nullable=False)
    matched_criteria = Column(JSON, nullable=True)  # Which criteria matched
    
    # Match quality
    match_score = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence_level = Column(Float, nullable=False)  # 0.0 to 1.0
    
    # Usage tracking
    questions_generated = Column(Integer, default=0)
    user_satisfaction = Column(Float, nullable=True)  # User feedback score
    ai_fallback_used = Column(Boolean, default=False)  # Whether AI was needed as fallback
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, default=func.now())
    
    # Indexes (simplified for PostgreSQL compatibility)
    __table_args__ = (
        Index('idx_template_hash', 'question_template_id', 'user_request_hash'),
        Index('idx_match_score_confidence', 'match_score', 'confidence_level'),
        Index('idx_created_last_used', 'created_at', 'last_used'),
    )

class QuestionGenerationLog(Base):
    """Log all question generation requests for analytics and optimization."""
    
    __tablename__ = "question_generation_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request details
    user_id = Column(String(100), nullable=True, index=True)
    role = Column(String(200), nullable=False)
    job_description_length = Column(Integer, nullable=False)
    complexity_score = Column(Float, nullable=False)
    
    # Generation method
    generation_method = Column(String(50), nullable=False, index=True)  # database, ai, hybrid
    ai_service_used = Column(String(50), nullable=True)  # openai, anthropic, ollama
    tokens_used = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    
    # Results
    questions_generated = Column(Integer, nullable=False)
    questions_from_database = Column(Integer, default=0)
    questions_from_ai = Column(Integer, default=0)
    match_quality_score = Column(Float, nullable=True)
    
    # Performance metrics
    processing_time_ms = Column(Integer, nullable=False)
    cache_hit = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Indexes (simplified for PostgreSQL compatibility)
    __table_args__ = (
        Index('idx_method_service', 'generation_method', 'ai_service_used'),
        Index('idx_complexity_tokens', 'complexity_score', 'tokens_used'),
        Index('idx_created_method', 'created_at', 'generation_method'),
    )

class QuestionFeedback(Base):
    """Store user feedback on generated questions for continuous improvement."""
    
    __tablename__ = "question_feedback"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Feedback details
    question_template_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    generation_log_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    
    # Feedback scores
    relevance_score = Column(Float, nullable=False)  # 1-5 scale
    difficulty_appropriateness = Column(Float, nullable=False)  # 1-5 scale
    quality_score = Column(Float, nullable=False)  # 1-5 scale
    overall_satisfaction = Column(Float, nullable=False)  # 1-5 scale
    
    # Feedback details
    feedback_text = Column(Text, nullable=True)
    suggested_improvements = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Indexes (simplified for PostgreSQL compatibility)
    __table_args__ = (
        Index('idx_template_satisfaction', 'question_template_id', 'overall_satisfaction'),
        Index('idx_log_satisfaction', 'generation_log_id', 'overall_satisfaction'),
        Index('idx_created_satisfaction', 'created_at', 'overall_satisfaction'),
    )
