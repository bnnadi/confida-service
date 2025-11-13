"""
Real-time speech analysis service for processing audio chunks and providing live feedback.
"""
import re
from typing import Dict, Any, Optional, List
from collections import deque
from app.models.real_time_models import SpeechAnalysis
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SpeechAnalyzer:
    """Service for analyzing speech in real-time."""
    
    # Common filler words
    FILLER_WORDS = {
        "um", "uh", "er", "ah", "like", "you know", "so", "well", 
        "actually", "basically", "literally", "right", "okay", "ok"
    }
    
    # Optimal speaking pace (words per minute)
    OPTIMAL_PACE_MIN = 140
    OPTIMAL_PACE_MAX = 180
    
    def __init__(self):
        self.transcript_buffer = deque(maxlen=1000)  # Keep last 1000 words
        self.audio_chunks = deque(maxlen=100)  # Keep last 100 audio chunks for analysis
    
    def analyze_transcript(self, transcript: str) -> SpeechAnalysis:
        """
        Analyze transcript text for speech patterns.
        
        Args:
            transcript: Text transcript to analyze
            
        Returns:
            SpeechAnalysis object with metrics
        """
        if not transcript or not transcript.strip():
            return SpeechAnalysis()
        
        words = transcript.lower().split()
        word_count = len(words)
        
        # Count filler words
        filler_count = sum(1 for word in words if word in self.FILLER_WORDS)
        
        # Calculate pace (words per minute)
        # For real-time, we estimate based on word count and time
        # This is a simplified calculation - in production, use actual timing
        pace = word_count * 2  # Rough estimate: 2 words per second = 120 WPM
        
        # Calculate clarity (based on filler word ratio and sentence structure)
        filler_ratio = filler_count / word_count if word_count > 0 else 0
        clarity = max(0.0, min(1.0, 1.0 - (filler_ratio * 2)))  # Penalize filler words
        
        # Detect pauses (multiple spaces or punctuation patterns)
        pause_pattern = r'[.!?]\s+|,\s+'
        pauses = len(re.findall(pause_pattern, transcript))
        
        # Confidence score (combination of clarity and pace)
        pace_score = 1.0 if self.OPTIMAL_PACE_MIN <= pace <= self.OPTIMAL_PACE_MAX else 0.7
        confidence = (clarity * 0.7) + (pace_score * 0.3)
        
        return SpeechAnalysis(
            filler_words=filler_count,
            pace=pace,
            clarity=clarity,
            volume=0.8,  # Placeholder - would need audio analysis
            pauses=pauses,
            confidence=confidence,
            transcript=transcript
        )
    
    def analyze_audio_chunk(self, audio_data: bytes, transcript: Optional[str] = None) -> SpeechAnalysis:
        """
        Analyze audio chunk for speech metrics.
        
        Args:
            audio_data: Raw audio bytes
            transcript: Optional transcript if available
            
        Returns:
            SpeechAnalysis object
        """
        # Store chunk for potential analysis
        self.audio_chunks.append(audio_data)
        
        # If transcript is available, use it for analysis
        if transcript:
            return self.analyze_transcript(transcript)
        
        # Basic audio analysis (simplified - in production, use proper audio processing)
        # For now, return basic metrics
        return SpeechAnalysis(
            filler_words=0,
            pace=0.0,
            clarity=0.5,  # Default until we have transcript
            volume=0.7,  # Placeholder
            pauses=0,
            confidence=0.5,
            transcript=None
        )
    
    def get_realtime_suggestions(self, analysis: SpeechAnalysis) -> List[str]:
        """
        Generate real-time suggestions based on speech analysis.
        
        Args:
            analysis: SpeechAnalysis object
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Pace suggestions
        if analysis.pace < self.OPTIMAL_PACE_MIN:
            suggestions.append("Try speaking a bit faster to maintain engagement")
        elif analysis.pace > self.OPTIMAL_PACE_MAX:
            suggestions.append("Consider slowing down slightly for better clarity")
        
        # Filler word suggestions
        if analysis.filler_words > 5:
            suggestions.append(f"Try to reduce filler words (detected {analysis.filler_words})")
        
        # Clarity suggestions
        if analysis.clarity < 0.6:
            suggestions.append("Focus on clear articulation and reducing filler words")
        
        # Pause suggestions
        if analysis.pauses < 2:
            suggestions.append("Consider adding brief pauses for emphasis")
        elif analysis.pauses > 10:
            suggestions.append("Too many pauses - try to speak more continuously")
        
        return suggestions
    
    def reset(self):
        """Reset analyzer state for new session."""
        self.transcript_buffer.clear()
        self.audio_chunks.clear()

