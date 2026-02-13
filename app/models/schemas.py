from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

# Request Models
class ParseJDRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=200, description="The job role/title")
    jobDescription: str = Field(..., min_length=10, max_length=10000, description="The full job description")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError('Role cannot be empty')
        return v.strip()
    
    @field_validator('jobDescription')
    @classmethod
    def validate_job_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Job description cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Job description must be at least 10 characters')
        return v.strip()

class AnalyzeAnswerRequest(BaseModel):
    jobDescription: str = Field(..., min_length=10, max_length=10000, description="The job description")
    question: str = Field(..., min_length=5, max_length=1000, description="The interview question")
    answer: str = Field(..., min_length=1, max_length=5000, description="The candidate's answer")
    audio_file_id: Optional[str] = Field(None, description="File ID of the user's answer audio recording")
    
    @field_validator('jobDescription', 'question', 'answer')
    @classmethod
    def validate_text_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()

# Response Models
class ParseJDResponse(BaseModel):
    questions: List[str] = Field(..., description="Generated interview questions")

class Score(BaseModel):
    """Legacy score model - maintained for backward compatibility."""
    clarity: int = Field(..., ge=1, le=10, description="Clarity score 1-10 (legacy)")
    confidence: int = Field(..., ge=1, le=10, description="Confidence score 1-10 (legacy)")
    
class EnhancedScore(BaseModel):
    """Enhanced 100-point scoring system."""
    total_score: float = Field(..., ge=0.0, le=100.0, description="Total score out of 100")
    grade_tier: str = Field(..., description="Grade tier: Excellent, Strong, Average, or At Risk")
    verbal_communication: float = Field(..., ge=0.0, le=40.0, description="Verbal Communication score (0-40)")
    interview_readiness: float = Field(..., ge=0.0, le=20.0, description="Interview Readiness score (0-20)")
    non_verbal_communication: float = Field(..., ge=0.0, le=25.0, description="Non-verbal Communication score (0-25)")
    adaptability_engagement: float = Field(..., ge=0.0, le=15.0, description="Adaptability & Engagement score (0-15)")

class AnalyzeAnswerResponse(BaseModel):
    analysis: str = Field(..., description="Analysis of the answer")
    score: Dict[str, Any] = Field(..., description="Score breakdown (legacy format)")
    enhanced_score: Optional[Dict[str, Any]] = Field(None, description="Enhanced 100-point scoring rubric")
    suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")
    jobDescription: str = Field(..., description="Job description used for analysis")
    answer: str = Field(..., description="The analyzed answer")
    service_used: str = Field(..., description="AI service used for analysis")
    multi_agent_analysis: Optional[Dict[str, Any]] = Field(None, description="Full multi-agent analysis data")

# Database response models for interview data
class QuestionResponse(BaseModel):
    id: str  # UUID as string
    question_text: str
    question_order: int
    created_at: str
    
    class Config:
        from_attributes = True

class AnswerResponse(BaseModel):
    id: str  # UUID as string
    answer_text: str
    analysis_result: Optional[Dict[str, Any]] = None
    score: Optional[Dict[str, Any]] = None
    audio_file_id: Optional[str] = None
    created_at: str

    @field_validator("id", mode="before")
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("created_at", mode="before")
    @classmethod
    def datetime_to_str(cls, v):
        if v is None:
            return ""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True

class InterviewSessionResponse(BaseModel):
    id: str  # UUID as string
    user_id: str  # UUID as string
    mode: str
    role: str
    job_description: Optional[str] = None
    scenario_id: Optional[str] = None
    question_source: str
    status: str
    total_questions: Optional[int] = 0
    completed_questions: Optional[int] = 0
    created_at: str
    updated_at: Optional[str] = None

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def datetime_to_str(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    @field_validator("total_questions", "completed_questions", mode="before")
    @classmethod
    def int_default(cls, v):
        return v if v is not None else 0

    class Config:
        from_attributes = True

class CompleteSessionResponse(BaseModel):
    session: InterviewSessionResponse
    questions: List[QuestionResponse]
    
    class Config:
        from_attributes = True

# Request models for creating sessions
class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., description="User ID for the session")
    mode: str = Field(..., description="Session mode: 'practice' or 'interview'")
    role: str = Field(..., min_length=1, max_length=200, description="Job role for the interview")
    
    # For practice mode
    scenario_id: Optional[str] = Field(None, description="Scenario ID for practice mode")
    
    # For interview mode
    job_title: Optional[str] = Field(None, description="Job title for interview mode")
    job_description: Optional[str] = Field(None, description="Job description for interview mode")
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id_uuid(cls, v):
        try:
            UUID(v)
        except (ValueError, TypeError):
            raise ValueError('user_id must be a valid UUID format')
        return v

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v):
        if v not in ['practice', 'interview']:
            raise ValueError('Mode must be either "practice" or "interview"')
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError('Role cannot be empty')
        return v.strip()
    
    @field_validator('scenario_id')
    @classmethod
    def validate_scenario_id(cls, v, info):
        if info.data.get('mode') == 'practice' and not v:
            raise ValueError('scenario_id is required for practice mode')
        return v
    
    @field_validator('job_title', 'job_description')
    @classmethod
    def validate_job_fields(cls, v, info):
        if info.data.get('mode') == 'interview':
            if not v or (isinstance(v, str) and not v.strip()):
                raise ValueError('job_title and job_description are required for interview mode')
            if isinstance(v, str) and len(v.strip()) < 10:
                raise ValueError('job_title and job_description must be at least 10 characters')
        return v.strip() if v and isinstance(v, str) else v

    @model_validator(mode='after')
    def validate_interview_job_fields(self):
        """Ensure job_title and job_description are provided for interview mode."""
        if self.mode == 'interview':
            if not self.job_title or (isinstance(self.job_title, str) and not self.job_title.strip()):
                raise ValueError('job_title is required for interview mode')
            if not self.job_description or (isinstance(self.job_description, str) and not self.job_description.strip()):
                raise ValueError('job_description is required for interview mode')
            if len((self.job_title or '').strip()) < 10:
                raise ValueError('job_title must be at least 10 characters')
            if len((self.job_description or '').strip()) < 10:
                raise ValueError('job_description must be at least 10 characters')
        return self

class AddQuestionsRequest(BaseModel):
    questions: List[str] = Field(..., min_items=1, max_items=20, description="List of interview questions")
    
    @field_validator('questions')
    @classmethod
    def validate_questions(cls, v):
        if not v:
            raise ValueError('Questions list cannot be empty')
        
        validated_questions = []
        for i, question in enumerate(v):
            if not question or not question.strip():
                raise ValueError(f'Question {i+1} cannot be empty')
            if len(question.strip()) < 5:
                raise ValueError(f'Question {i+1} must be at least 5 characters')
            if len(question.strip()) > 1000:
                raise ValueError(f'Question {i+1} must be no more than 1000 characters')
            validated_questions.append(question.strip())
        
        return validated_questions

class AddAnswerRequest(BaseModel):
    answer_text: str = Field(..., min_length=1, max_length=5000, description="Answer text")
    analysis_result: Optional[Dict[str, Any]] = Field(None, description="AI analysis result")
    score: Optional[Dict[str, Any]] = Field(None, description="Scoring data")
    audio_file_id: Optional[str] = Field(None, description="File ID of the user's answer audio recording")
    
    @field_validator('answer_text')
    @classmethod
    def validate_answer_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Answer text cannot be empty')
        return v.strip()

# Speech-to-text models
class TranscribeResponse(BaseModel):
    transcription: str = Field(..., description="Transcribed text from audio")
    language: str = Field(..., description="Language code used for transcription")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of transcription")
    file_id: Optional[str] = Field(None, description="ID of saved audio file if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the transcription")

class SupportedFormatsResponse(BaseModel):
    formats: List[Dict[str, str]] = Field(..., description="List of supported audio formats")
    supported_languages: List[str] = Field(..., description="List of supported language codes")

class SynthesizeRequest(BaseModel):
    """Request model for text-to-speech synthesis (admin tooling)."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize to speech")
    voice_id: Optional[str] = Field(None, description="Voice identifier (uses default if not provided)")
    audio_format: Optional[str] = Field("mp3", pattern="^(mp3|wav)$", description="Audio format (mp3 or wav)")
    use_cache: Optional[bool] = Field(True, description="Whether to use cache for synthesis")
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Text cannot be empty')
        return v.strip()

class SynthesizeResponse(BaseModel):
    """Response model for text-to-speech synthesis (admin tooling)."""
    audio_data: str = Field(..., description="Base64-encoded audio data")
    voice_id: str = Field(..., description="Voice identifier used for synthesis")
    audio_format: str = Field(..., description="Audio format of the synthesized audio")
    text_length: int = Field(..., description="Length of the input text")
    cached: bool = Field(False, description="Whether the result was retrieved from cache")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the synthesis")

# Optional: Enhanced models for future features (legacy)
class InterviewSession(BaseModel):
    session_id: str
    role: str
    job_description: str
    questions: List[str]
    answers: List[dict]
    created_at: str

# Authentication Models
class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class TokenPayload(BaseModel):
    sub: str  # user ID
    email: str
    role: UserRole
    token_type: TokenType
    exp: int
    iat: int

class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserLoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")

class UserRegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    created_at: str
    last_login: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="User email address")

class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(..., description="Reset token")
    new_password: str = Field(..., min_length=8, description="New password")

# Additional auth models
class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    experience_level: Optional[str] = Field(None, description="Experience level")
    preferred_industries: Optional[List[str]] = Field(None, description="Preferred industries")
    skills: Optional[List[str]] = Field(None, description="User skills")

class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[dict] = None
    expires_at: Optional[str] = None

class AuthErrorResponse(BaseModel):
    error: str
    detail: str
    error_code: Optional[str] = None

# Consent and Data Rights Models (GDPR/CCPA)
class ConsentPreferenceItem(BaseModel):
    """Single consent preference for update."""
    consent_type: str = Field(..., description="Consent type: essential, analytics, marketing")
    granted: bool = Field(..., description="Whether consent is granted")

    @field_validator("consent_type")
    @classmethod
    def validate_consent_type(cls, v):
        allowed = {"essential", "analytics", "marketing"}
        if v not in allowed:
            raise ValueError(f"consent_type must be one of: {allowed}")
        return v


class ConsentPreferencesRequest(BaseModel):
    """Request to update consent preferences."""
    consents: List[ConsentPreferenceItem] = Field(..., description="List of consent preferences to update")


class ConsentItemResponse(BaseModel):
    """Single consent preference in response."""
    consent_type: str
    granted: bool
    updated_at: Optional[str] = None


class ConsentPreferencesResponse(BaseModel):
    """Response with current consent preferences."""
    consents: List[ConsentItemResponse] = Field(..., description="Current consent preferences")


class ConsentHistoryItem(BaseModel):
    """Single consent history entry."""
    consent_type: str
    action: str  # granted, withdrawn
    created_at: str


class ConsentHistoryResponse(BaseModel):
    """Response with consent change history."""
    history: List[ConsentHistoryItem] = Field(..., description="Consent change history")


class DeleteAccountRequest(BaseModel):
    """Request to delete user account (GDPR Right to Erasure)."""
    confirm: bool = Field(..., description="Must be true to confirm deletion")
    password: str = Field(..., min_length=1, description="Current password for verification")

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, v):
        if not v:
            raise ValueError("confirm must be true to delete account")
        return v


# Data export structure (GDPR Right to Access)
class DataExportResponse(BaseModel):
    """User data export for GDPR Right to Access."""
    exported_at: str = Field(..., description="Export timestamp")
    user: Dict[str, Any] = Field(..., description="User profile (excluding password)")
    sessions: List[Dict[str, Any]] = Field(default_factory=list, description="Interview sessions")
    answers: List[Dict[str, Any]] = Field(default_factory=list, description="User answers")
    performance: List[Dict[str, Any]] = Field(default_factory=list, description="Performance data")
    analytics_events: List[Dict[str, Any]] = Field(default_factory=list, description="Analytics events")
    goals: List[Dict[str, Any]] = Field(default_factory=list, description="User goals")
    consents: List[Dict[str, Any]] = Field(default_factory=list, description="Consent preferences")

# File Upload Models
class FileType(str, Enum):
    AUDIO = "audio"
    DOCUMENT = "document"
    IMAGE = "image"

class FileStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

class FileUploadRequest(BaseModel):
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file being uploaded")
    file_size: int = Field(..., gt=0, description="Size of file in bytes")

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: FileType
    file_size: int
    status: FileStatus
    upload_url: Optional[str] = None
    expires_at: str

class FileInfoResponse(BaseModel):
    file_id: str
    filename: str
    file_type: FileType
    file_size: int
    status: FileStatus
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    upload_url: Optional[str] = None
    download_url: Optional[str] = None
    mime_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_result: Optional[Dict[str, Any]] = None

class FileListResponse(BaseModel):
    files: List[FileInfoResponse]
    total: int
    page: int
    per_page: int

class FileDeleteResponse(BaseModel):
    file_id: str
    success: bool
    message: str

class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class FileValidationErrorResponse(BaseModel):
    """Response model for file validation errors."""
    message: str
    error_code: str
    field: Optional[str] = None

# Question Engine Models
class QuestionPreview(BaseModel):
    id: str
    text: str
    type: str
    difficulty_level: str
    category: str

class ScenarioInfo(BaseModel):
    id: str
    name: str
    description: str

class SessionPreviewResponse(BaseModel):
    mode: str
    role: str
    questions: List[QuestionPreview]
    total_questions: int
    estimated_duration: Optional[int] = None  # in minutes

class ScenarioListResponse(BaseModel):
    scenarios: List[ScenarioInfo]
    total: int

# Question Generation Models (New Structured API)
class JobRequest(BaseModel):
    """Request model for structured question generation."""
    role_name: str = Field(..., min_length=1, max_length=200, description="The job role/title")
    job_description: str = Field(..., min_length=10, max_length=10000, description="The full job description")
    resume: Optional[str] = Field(None, max_length=50000, description="Optional resume text for context")
    limit: Optional[int] = Field(10, ge=1, le=50, description="Maximum number of questions to generate")
    voice_id: Optional[str] = Field("confida-default-en", description="Voice identifier for TTS synthesis")
    format: Optional[str] = Field("mp3", pattern="^(mp3|wav)$", description="Audio format for voice synthesis")
    include_voice: Optional[bool] = Field(True, description="Whether to include voice synthesis for questions")
    
    @field_validator('role_name')
    @classmethod
    def validate_role_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Role name cannot be empty')
        return v.strip()
    
    @field_validator('job_description')
    @classmethod
    def validate_job_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Job description cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Job description must be at least 10 characters')
        return v.strip()

class QuestionIdentifier(BaseModel):
    """Identifier metadata for a question."""
    question_id: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    role: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)

class VoiceFile(BaseModel):
    """Voice audio file reference."""
    file_id: str = Field(..., description="File ID for the audio file")
    mime_type: str = Field(..., description="MIME type of the audio file")
    download_url: str = Field(..., description="URL to download the audio file")

class VoicePayload(BaseModel):
    """Voice synthesis payload for a question."""
    voice_id: str = Field(..., description="Voice identifier used for synthesis")
    version: int = Field(..., description="Voice version number")
    duration: float = Field(..., ge=0.0, description="Audio duration in seconds")
    files: List[VoiceFile] = Field(..., description="List of audio file references")

class StructuredQuestion(BaseModel):
    """Structured question with metadata."""
    text: str = Field(..., description="The question text")
    source: Literal["from_library", "newly_generated"] = Field(..., description="Question source")
    question_id: Optional[str] = Field(None, description="Question ID from database or ai-service")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Question metadata")
    identifiers: Optional[QuestionIdentifier] = None
    voice: Optional[VoicePayload] = Field(None, description="Voice synthesis payload if include_voice=true")

class StructuredQuestionResponse(BaseModel):
    """Response model for structured question generation."""
    identifiers: Dict[str, Any] = Field(..., description="Global identifiers for the question set")
    questions: List[StructuredQuestion] = Field(..., description="List of generated questions")
    embedding_vectors: Optional[Dict[str, List[float]]] = Field(None, description="Embedding vectors for questions") 