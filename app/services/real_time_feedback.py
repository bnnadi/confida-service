"""
Real-time feedback service for processing and generating feedback during live interviews.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.models.real_time_models import RealTimeFeedback, FeedbackType, SpeechAnalysis
from app.services.speech_analyzer import SpeechAnalyzer
from app.utils.logger import get_logger
from app.dependencies import get_ai_client_dependency

logger = get_logger(__name__)


class RealTimeFeedbackService:
    """Service for generating real-time feedback during interviews."""
    
    def __init__(self):
        self.speech_analyzer = SpeechAnalyzer()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _build_metrics(self, speech_analysis: SpeechAnalysis, include_volume: bool = True) -> Dict[str, float]:
        """Build metrics dictionary from speech analysis."""
        metrics = {
            "filler_words": speech_analysis.filler_words,
            "pace": speech_analysis.pace,
            "clarity": speech_analysis.clarity,
            "pauses": speech_analysis.pauses,
            "confidence": speech_analysis.confidence
        }
        if include_volume:
            metrics["volume"] = speech_analysis.volume
        return metrics
    
    def _create_error_feedback(self, session_id: str, message: str) -> RealTimeFeedback:
        """Create standardized error feedback."""
        return RealTimeFeedback(
            session_id=session_id,
            feedback_type=FeedbackType.ERROR,
            message=message,
            confidence=0.0,
            suggestions=[],
            metrics={}
        )
    
    async def process_audio_chunk(
        self,
        session_id: str,
        audio_data: bytes,
        question_id: Optional[int] = None,
        transcript: Optional[str] = None
    ) -> RealTimeFeedback:
        """
        Process audio chunk and generate real-time feedback.
        
        Args:
            session_id: Interview session ID
            audio_data: Audio chunk bytes
            question_id: Optional question ID
            transcript: Optional transcript if available
            
        Returns:
            RealTimeFeedback object
        """
        try:
            # Analyze speech
            speech_analysis = self.speech_analyzer.analyze_audio_chunk(audio_data, transcript)
            
            # Get suggestions
            suggestions = self.speech_analyzer.get_realtime_suggestions(speech_analysis)
            
            # Build metrics
            metrics = self._build_metrics(speech_analysis, include_volume=True)
            
            # Generate feedback message
            message = self._generate_feedback_message(speech_analysis, suggestions)
            
            return RealTimeFeedback(
                session_id=session_id,
                feedback_type=FeedbackType.SPEECH_ANALYSIS,
                message=message,
                confidence=speech_analysis.confidence,
                suggestions=suggestions,
                metrics=metrics,
                data={
                    "speech_analysis": speech_analysis.dict(),
                    "question_id": question_id
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing audio chunk for session {session_id}: {e}")
            return self._create_error_feedback(session_id, f"Error processing audio: {str(e)}")
    
    async def process_transcript_chunk(
        self,
        session_id: str,
        transcript: str,
        question_id: Optional[int] = None,
        job_description: Optional[str] = None,
        question_text: Optional[str] = None
    ) -> RealTimeFeedback:
        """
        Process transcript chunk and generate content-based feedback.
        
        Args:
            session_id: Interview session ID
            transcript: Text transcript
            question_id: Optional question ID
            job_description: Optional job description for context
            question_text: Optional question text for context
            
        Returns:
            RealTimeFeedback object
        """
        try:
            # Analyze speech patterns
            speech_analysis = self.speech_analyzer.analyze_transcript(transcript)
            
            # Get basic suggestions
            suggestions = self.speech_analyzer.get_realtime_suggestions(speech_analysis)
            
            # If we have context, try to get AI-based feedback
            if question_text and job_description and transcript:
                ai_feedback = await self._get_ai_feedback(
                    job_description, question_text, transcript
                )
                if ai_feedback:
                    suggestions.extend(ai_feedback.get("suggestions", []))
            
            # Build metrics
            metrics = self._build_metrics(speech_analysis, include_volume=False)
            
            message = self._generate_feedback_message(speech_analysis, suggestions)
            
            return RealTimeFeedback(
                session_id=session_id,
                feedback_type=FeedbackType.CONTENT_ANALYSIS,
                message=message,
                confidence=speech_analysis.confidence,
                suggestions=suggestions,
                metrics=metrics,
                data={
                    "speech_analysis": speech_analysis.dict(),
                    "question_id": question_id,
                    "transcript": transcript
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing transcript for session {session_id}: {e}")
            return self._create_error_feedback(session_id, f"Error processing transcript: {str(e)}")
    
    async def _get_ai_feedback(
        self,
        job_description: str,
        question: str,
        answer: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get AI-based feedback for answer content.
        
        Args:
            job_description: Job description
            question: Question text
            answer: Answer text
            
        Returns:
            Optional feedback dictionary
        """
        try:
            ai_client = get_ai_client_dependency()
            if not ai_client:
                return None
            
            # Use AI service for quick feedback (simplified version)
            # In production, this might use a streaming endpoint
            response = await ai_client.analyze_answer(
                job_description=job_description,
                question=question,
                answer=answer,
                role=""
            )
            
            return {
                "suggestions": response.get("suggestions", []),
                "score": response.get("score", {})
            }
            
        except Exception as e:
            logger.warning(f"Could not get AI feedback: {e}")
            return None
    
    def _generate_feedback_message(
        self,
        speech_analysis: SpeechAnalysis,
        suggestions: List[str]
    ) -> str:
        """
        Generate human-readable feedback message.
        
        Args:
            speech_analysis: SpeechAnalysis object
            suggestions: List of suggestions
            
        Returns:
            Feedback message string
        """
        if not suggestions:
            return "Keep going! Your speech is clear and well-paced."
        
        # Prioritize most important suggestion
        primary_suggestion = suggestions[0] if suggestions else "Continue speaking clearly."
        
        # Add metrics summary
        metrics_summary = []
        if speech_analysis.clarity < 0.6:
            metrics_summary.append("clarity could be improved")
        if speech_analysis.filler_words > 5:
            metrics_summary.append(f"{speech_analysis.filler_words} filler words detected")
        
        if metrics_summary:
            return f"{primary_suggestion} ({', '.join(metrics_summary)})"
        
        return primary_suggestion
    
    def register_session(self, session_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Register a new active session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            metadata: Optional session metadata
        """
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "started_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        logger.info(f"Registered real-time feedback session: {session_id}")
    
    def cleanup_session(self, session_id: str):
        """
        Clean up session data.
        
        Args:
            session_id: Session ID
        """
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self.speech_analyzer.reset()
            logger.info(f"Cleaned up real-time feedback session: {session_id}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session info dictionary or None
        """
        return self.active_sessions.get(session_id)


# Global service instance
real_time_feedback_service = RealTimeFeedbackService()

