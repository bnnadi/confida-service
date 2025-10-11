from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Request Models
class ParseJDRequest(BaseModel):
    role: str = Field(..., description="The job role/title")
    jobDescription: str = Field(..., description="The full job description")

class AnalyzeAnswerRequest(BaseModel):
    jobDescription: str = Field(..., description="The job description")
    question: str = Field(..., description="The interview question")
    answer: str = Field(..., description="The candidate's answer")

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
    role: str = Field(..., description="Job role for the interview")
    job_description: str = Field(..., description="Job description text")

class AddQuestionsRequest(BaseModel):
    questions: List[str] = Field(..., description="List of interview questions")

class AddAnswerRequest(BaseModel):
    answer_text: str = Field(..., description="Answer text")
    analysis_result: Optional[Dict[str, Any]] = Field(None, description="AI analysis result")
    score: Optional[Dict[str, Any]] = Field(None, description="Scoring data")

# Optional: Enhanced models for future features (legacy)
class InterviewSession(BaseModel):
    session_id: str
    role: str
    job_description: str
    questions: List[str]
    answers: List[dict]
    created_at: str 