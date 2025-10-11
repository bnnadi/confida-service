from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

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
    role: str
    job_description: str
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
    role: str = Field(..., min_length=1, max_length=200, description="Job role for the interview")
    job_description: str = Field(..., min_length=10, max_length=10000, description="Job description text")
    
    @validator('role')
    def validate_role(cls, v):
        if not v or not v.strip():
            raise ValueError('Role cannot be empty')
        return v.strip()
    
    @validator('job_description')
    def validate_job_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Job description cannot be empty')
        if len(v.strip()) < 10:
            raise ValueError('Job description must be at least 10 characters')
        return v.strip()

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

# Optional: Enhanced models for future features (legacy)
class InterviewSession(BaseModel):
    session_id: str
    role: str
    job_description: str
    questions: List[str]
    answers: List[dict]
    created_at: str 