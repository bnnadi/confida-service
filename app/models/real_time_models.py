"""
Real-time feedback models for WebSocket communication.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FeedbackType(str, Enum):
    """Types of real-time feedback."""
    SPEECH_ANALYSIS = "speech_analysis"
    CONTENT_ANALYSIS = "content_analysis"
    SCORE_UPDATE = "score_update"
    SUGGESTION = "suggestion"
    ERROR = "error"
    CONNECTION_STATUS = "connection_status"


class RealTimeFeedback(BaseModel):
    """Real-time feedback model for WebSocket communication."""
    session_id: str = Field(..., description="Interview session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Feedback timestamp")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    message: str = Field(..., description="Feedback message")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score (0-1)")
    suggestions: List[str] = Field(default_factory=list, description="List of suggestions")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional feedback data")


class SpeechAnalysis(BaseModel):
    """Real-time speech analysis metrics."""
    filler_words: int = Field(0, ge=0, description="Number of filler words detected")
    pace: float = Field(0.0, ge=0.0, description="Speaking pace (words per minute)")
    clarity: float = Field(0.0, ge=0.0, le=1.0, description="Speech clarity score (0-1)")
    volume: float = Field(0.0, ge=0.0, le=1.0, description="Volume level (0-1)")
    pauses: int = Field(0, ge=0, description="Number of pauses detected")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall confidence score (0-1)")
    transcript: Optional[str] = Field(None, description="Partial transcript of speech")


class WebSocketMessage(BaseModel):
    """Base WebSocket message model."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class AudioChunkMessage(BaseModel):
    """Audio chunk message for streaming."""
    session_id: str = Field(..., description="Interview session ID")
    question_id: Optional[int] = Field(None, description="Question ID if available")
    chunk_index: int = Field(..., ge=0, description="Chunk index in sequence")
    audio_data: bytes = Field(..., description="Audio chunk data (base64 encoded)")
    is_final: bool = Field(False, description="Whether this is the final chunk")


class ConnectionStatus(BaseModel):
    """WebSocket connection status."""
    status: str = Field(..., description="Connection status (connected, disconnected, error)")
    session_id: str = Field(..., description="Interview session ID")
    message: Optional[str] = Field(None, description="Status message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Status timestamp")

