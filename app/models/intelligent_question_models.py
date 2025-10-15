"""
Models and schemas for intelligent question selection system.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

class QuestionCategory(str, Enum):
    """Question categories for intelligent selection."""
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    LEADERSHIP = "leadership"
    DATA_ANALYSIS = "data_analysis"
    PROBLEM_SOLVING = "problem_solving"
    COMMUNICATION = "communication"

class DifficultyLevel(str, Enum):
    """Difficulty levels for questions."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Industry(str, Enum):
    """Industry types for role analysis."""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    MEDIA = "media"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    OTHER = "other"

class SeniorityLevel(str, Enum):
    """Seniority levels for role analysis."""
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"

class CompanySize(str, Enum):
    """Company size categories."""
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"

class QuestionSource(str, Enum):
    """Source of questions."""
    DATABASE = "database"
    AI_GENERATED = "ai_generated"
    HYBRID = "hybrid"
    FALLBACK = "fallback"

# Pydantic Models for API responses
class RoleAnalysisModel(BaseModel):
    """Role analysis model for API responses."""
    primary_role: str
    required_skills: List[str] = Field(default_factory=list)
    industry: Industry
    seniority_level: SeniorityLevel
    company_size: CompanySize
    tech_stack: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    job_function: str
    experience_years: Optional[int] = None
    education_requirements: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)

class QuestionModel(BaseModel):
    """Question model for API responses."""
    id: str
    question_text: str
    category: QuestionCategory
    difficulty_level: DifficultyLevel
    tags: List[str] = Field(default_factory=list)
    role_relevance_score: float = Field(ge=0.0, le=1.0)
    quality_score: float = Field(ge=0.0, le=1.0)
    user_history_score: float = Field(default=0.5, ge=0.0, le=1.0)
    source: QuestionSource = QuestionSource.DATABASE
    created_at: Optional[datetime] = None

class UserContextModel(BaseModel):
    """User context model for personalization."""
    user_id: Optional[str] = None
    previous_questions: List[str] = Field(default_factory=list)
    performance_history: Dict[str, float] = Field(default_factory=dict)
    preferred_difficulty: Optional[DifficultyLevel] = None
    weak_areas: List[str] = Field(default_factory=list)
    strong_areas: List[str] = Field(default_factory=list)

class QuestionSelectionRequest(BaseModel):
    """Request model for intelligent question selection."""
    role: str
    job_description: str
    user_context: Optional[UserContextModel] = None
    target_count: int = Field(default=10, ge=1, le=50)
    prefer_database: bool = True
    enable_ai_fallback: bool = True

class QuestionSelectionResponse(BaseModel):
    """Response model for intelligent question selection."""
    questions: List[QuestionModel]
    source: QuestionSource
    database_hit_rate: float = Field(ge=0.0, le=1.0)
    ai_generated_count: int = Field(ge=0)
    diversity_score: float = Field(ge=0.0, le=1.0)
    selection_time: float = Field(ge=0.0)
    role_analysis: RoleAnalysisModel
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DiversityReport(BaseModel):
    """Diversity report model."""
    total_questions: int
    diversity_score: float = Field(ge=0.0, le=1.0)
    category_distribution: Dict[str, int]
    difficulty_distribution: Dict[str, int]
    tag_distribution: Dict[str, int]
    unique_categories: int
    unique_difficulties: int
    unique_tags: int

class QuestionGenerationRequest(BaseModel):
    """Request model for AI question generation."""
    role_analysis: RoleAnalysisModel
    missing_categories: List[QuestionCategory] = Field(default_factory=list)
    missing_difficulties: List[DifficultyLevel] = Field(default_factory=list)
    target_count: int = Field(default=5, ge=1, le=20)
    ai_service_preference: Optional[str] = None

class QuestionGenerationResponse(BaseModel):
    """Response model for AI question generation."""
    generated_questions: List[QuestionModel]
    generation_time: float = Field(ge=0.0)
    ai_service_used: str
    questions_stored: int = Field(ge=0)
    success_rate: float = Field(ge=0.0, le=1.0)
    storage_success_rate: float = Field(ge=0.0, le=1.0)

class IntelligentQuestionStats(BaseModel):
    """Statistics for intelligent question selection."""
    total_selections: int = 0
    database_hit_rate_avg: float = 0.0
    ai_generation_rate: float = 0.0
    diversity_score_avg: float = 0.0
    selection_time_avg: float = 0.0
    most_common_sources: Dict[str, int] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    difficulty_distribution: Dict[str, int] = Field(default_factory=dict)

# Database Models (if using SQLAlchemy)
@dataclass
class IntelligentQuestionSelection:
    """Database model for intelligent question selection records."""
    id: str
    user_id: Optional[str]
    role: str
    job_description_hash: str
    questions_selected: List[str]
    source: QuestionSource
    database_hit_rate: float
    ai_generated_count: int
    diversity_score: float
    selection_time: float
    role_analysis_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class QuestionPerformance:
    """Database model for question performance tracking."""
    id: str
    question_id: str
    user_id: Optional[str]
    role: str
    difficulty_rating: float
    relevance_rating: float
    quality_rating: float
    completion_time: float
    was_answered_correctly: Optional[bool]
    feedback: Optional[str]
    created_at: datetime

@dataclass
class UserQuestionHistory:
    """Database model for user question history."""
    id: str
    user_id: str
    question_id: str
    role: str
    category: QuestionCategory
    difficulty_level: DifficultyLevel
    performance_score: float
    time_spent: float
    was_completed: bool
    created_at: datetime

# Configuration Models
@dataclass
class DiversityConfig:
    """Configuration for diversity algorithms."""
    target_count: int = 10
    min_per_category: int = 1
    max_per_category: int = 4
    min_per_difficulty: int = 1
    max_per_difficulty: int = 5
    balance_categories: bool = True
    balance_difficulties: bool = True
    prefer_high_quality: bool = True
    avoid_recent_questions: bool = True

@dataclass
class ScoringWeights:
    """Weights for question scoring."""
    role_relevance: float = 0.4
    quality: float = 0.3
    diversity: float = 0.2
    user_preference: float = 0.1

@dataclass
class SelectionConfig:
    """Configuration for intelligent question selection."""
    min_database_questions: int = 5
    target_question_count: int = 10
    ai_fallback_threshold: float = 0.3
    max_ai_generation_attempts: int = 3
    generation_timeout: int = 30
    diversity_config: DiversityConfig = field(default_factory=DiversityConfig)
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)

# Utility Models
class QuestionSearchCriteria(BaseModel):
    """Search criteria for question database queries."""
    role: Optional[str] = None
    industry: Optional[Industry] = None
    seniority_level: Optional[SeniorityLevel] = None
    categories: List[QuestionCategory] = Field(default_factory=list)
    difficulties: List[DifficultyLevel] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    min_quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    max_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

class QuestionBankStats(BaseModel):
    """Statistics for question bank."""
    total_questions: int
    questions_by_category: Dict[str, int]
    questions_by_difficulty: Dict[str, int]
    questions_by_role: Dict[str, int]
    average_quality_score: float
    most_used_tags: List[Tuple[str, int]]
    recent_additions: int
    ai_generated_count: int
    database_generated_count: int

class PerformanceMetrics(BaseModel):
    """Performance metrics for intelligent question selection."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_selection_time: float = 0.0
    average_database_hit_rate: float = 0.0
    average_diversity_score: float = 0.0
    ai_generation_count: int = 0
    database_selection_count: int = 0
    hybrid_selection_count: int = 0
    error_rate: float = 0.0
