from pydantic import BaseModel, Field
from typing import List, Optional

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

# Optional: Enhanced models for future features
class InterviewSession(BaseModel):
    session_id: str
    role: str
    job_description: str
    questions: List[str]
    answers: List[dict]
    created_at: str 