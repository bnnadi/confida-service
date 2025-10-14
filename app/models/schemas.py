from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

# Request Models
class ParseJDRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=200, description="The job role/title")
    jobDescription: str = Field(..., min_length=10, max_length=10000, description="The full job description")
    
    @validator('role')
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError('Role cannot be empty')
        return v.strip()
    
    @validator('jobDescription')
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
    
    @validator('jobDescription', 'question', 'answer')
    def validate_text_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()

# Response Models
class ParseJDResponse(BaseModel):
    questions: List[str] = Field(..., description="Generated interview questions")

class Score(BaseModel):
    clarity: int = Field(..., ge=1, le=10, description="Clarity score 1-10")
    confidence: int = Field(..., ge=1, le=10, description="Confidence score 1-10")

class AnalyzeAnswerResponse(BaseModel):
    score: Score
    missingKeywords: List[str] = Field(..., description="Missing keywords from job description")
    improvements: List[str] = Field(..., description="Suggested improvements")
    idealAnswer: str = Field(..., description="Example of an ideal answer")

# Database response models for interview data
class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_order: int
    created_at: str
    
    class Config:
        from_attributes = True

class AnswerResponse(BaseModel):
    id: int
    answer_text: str
    analysis_result: Optional[Dict[str, Any]] = None
    score: Optional[Dict[str, Any]] = None
    created_at: str
    
    class Config:
        from_attributes = True

class InterviewSessionResponse(BaseModel):
    id: int
    user_id: int
    mode: str
    role: str
    job_description: Optional[str] = None
    scenario_id: Optional[str] = None
    question_source: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    
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
    
    @validator('mode')
    def validate_mode(cls, v):
        if v not in ['practice', 'interview']:
            raise ValueError('Mode must be either "practice" or "interview"')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError('Role cannot be empty')
        return v.strip()
    
    @validator('scenario_id')
    def validate_scenario_id(cls, v, values):
        if values.get('mode') == 'practice' and not v:
            raise ValueError('scenario_id is required for practice mode')
        return v
    
    @validator('job_title', 'job_description')
    def validate_job_fields(cls, v, values):
        if values.get('mode') == 'interview':
            if not v or not v.strip():
                raise ValueError(f'{"job_title" if "job_title" in values else "job_description"} is required for interview mode')
            if len(v.strip()) < 10:
                raise ValueError(f'{"job_title" if "job_title" in values else "job_description"} must be at least 10 characters')
        return v.strip() if v else v

class AddQuestionsRequest(BaseModel):
    questions: List[str] = Field(..., min_items=1, max_items=20, description="List of interview questions")
    
    @validator('questions')
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
    
    @validator('answer_text')
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
class UserRegistrationRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")

class UserProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    experience_level: Optional[str] = Field(None, description="Experience level")
    preferred_industries: Optional[List[str]] = Field(None, description="Preferred industries")
    skills: Optional[List[str]] = Field(None, description="User skills")

class AuthStatusResponse(BaseModel):
    is_authenticated: bool
    user: Optional[UserResponse] = None
    token_expires_in: Optional[int] = None

class AuthErrorResponse(BaseModel):
    error: str
    detail: str
    error_code: Optional[str] = None

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
    created_at: str
    expires_at: str
    download_url: Optional[str] = None

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