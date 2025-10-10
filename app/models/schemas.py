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

# Speech-to-Text Models
class TranscribeRequest(BaseModel):
    language: str = Field(default="en-US", description="Language code for transcription")
    format: str = Field(default="wav", description="Audio format (wav, mp3, m4a)")

class TranscribeResponse(BaseModel):
    transcript: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    language: str = Field(..., description="Detected language")
    duration: float = Field(..., description="Audio duration in seconds")

class SupportedFormatsResponse(BaseModel):
    formats: List[str] = Field(..., description="List of supported audio formats")
    max_file_size: int = Field(..., description="Maximum file size in bytes")
    supported_languages: List[str] = Field(..., description="List of supported language codes")

# Optional: Enhanced models for future features
class InterviewSession(BaseModel):
    session_id: str
    role: str
    job_description: str
    questions: List[str]
    answers: List[dict]
    created_at: str 