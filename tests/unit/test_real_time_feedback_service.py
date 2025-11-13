"""
Unit tests for RealTimeFeedbackService.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.real_time_feedback import RealTimeFeedbackService
from app.models.real_time_models import FeedbackType, SpeechAnalysis


class TestRealTimeFeedbackService:
    """Test cases for RealTimeFeedbackService."""
    
    @pytest.fixture
    def service(self):
        """Create RealTimeFeedbackService instance."""
        return RealTimeFeedbackService()
    
    @pytest.mark.unit
    def test_build_metrics_with_volume(self, service):
        """Test building metrics with volume."""
        analysis = SpeechAnalysis(
            filler_words=5,
            pace=150,
            clarity=0.8,
            volume=0.7,
            pauses=3,
            confidence=0.75
        )
        
        metrics = service._build_metrics(analysis, include_volume=True)
        
        assert "filler_words" in metrics
        assert "pace" in metrics
        assert "clarity" in metrics
        assert "volume" in metrics
        assert "pauses" in metrics
        assert "confidence" in metrics
        assert metrics["volume"] == 0.7
    
    @pytest.mark.unit
    def test_build_metrics_without_volume(self, service):
        """Test building metrics without volume."""
        analysis = SpeechAnalysis(
            filler_words=5,
            pace=150,
            clarity=0.8,
            volume=0.7,
            pauses=3,
            confidence=0.75
        )
        
        metrics = service._build_metrics(analysis, include_volume=False)
        
        assert "volume" not in metrics
        assert "filler_words" in metrics
        assert "pace" in metrics
    
    @pytest.mark.unit
    def test_create_error_feedback(self, service):
        """Test creating error feedback."""
        session_id = "test-session-123"
        message = "Test error message"
        
        feedback = service._create_error_feedback(session_id, message)
        
        assert feedback.session_id == session_id
        assert feedback.feedback_type == FeedbackType.ERROR
        assert feedback.message == message
        assert feedback.confidence == 0.0
        assert feedback.suggestions == []
        assert feedback.metrics == {}
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_audio_chunk_success(self, service):
        """Test processing audio chunk successfully."""
        session_id = "test-session"
        audio_data = b"fake_audio_data"
        transcript = "This is a test transcript"
        
        feedback = await service.process_audio_chunk(
            session_id=session_id,
            audio_data=audio_data,
            question_id=1,
            transcript=transcript
        )
        
        assert feedback.session_id == session_id
        assert feedback.feedback_type == FeedbackType.SPEECH_ANALYSIS
        assert feedback.confidence >= 0.0
        assert "metrics" in feedback.dict()
        assert feedback.data["question_id"] == 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_audio_chunk_error(self, service):
        """Test processing audio chunk with error."""
        session_id = "test-session"
        
        # Mock speech analyzer to raise exception
        with patch.object(service.speech_analyzer, 'analyze_audio_chunk', side_effect=Exception("Test error")):
            feedback = await service.process_audio_chunk(
                session_id=session_id,
                audio_data=b"data",
                question_id=None,
                transcript=None
            )
            
            assert feedback.feedback_type == FeedbackType.ERROR
            assert "error" in feedback.message.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_transcript_chunk_success(self, service):
        """Test processing transcript chunk successfully."""
        session_id = "test-session"
        transcript = "This is a test answer to an interview question."
        
        feedback = await service.process_transcript_chunk(
            session_id=session_id,
            transcript=transcript,
            question_id=1
        )
        
        assert feedback.session_id == session_id
        assert feedback.feedback_type == FeedbackType.CONTENT_ANALYSIS
        assert feedback.confidence >= 0.0
        assert feedback.data["transcript"] == transcript
        assert feedback.data["question_id"] == 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_transcript_chunk_with_ai_feedback(self, service):
        """Test processing transcript with AI feedback."""
        session_id = "test-session"
        transcript = "Test answer"
        job_description = "Test job description"
        question_text = "Test question"
        
        # Mock AI client
        mock_ai_feedback = {
            "suggestions": ["Add more detail", "Be more specific"],
            "score": {"clarity": 8, "confidence": 7}
        }
        
        with patch('app.services.real_time_feedback.get_ai_client_dependency') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.analyze_answer = AsyncMock(return_value=mock_ai_feedback)
            mock_get_client.return_value = mock_client
            
            feedback = await service.process_transcript_chunk(
                session_id=session_id,
                transcript=transcript,
                question_id=1,
                job_description=job_description,
                question_text=question_text
            )
            
            assert len(feedback.suggestions) >= 2  # Should include AI suggestions
            assert any("detail" in s.lower() or "specific" in s.lower() for s in feedback.suggestions)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_process_transcript_chunk_ai_unavailable(self, service):
        """Test processing transcript when AI is unavailable."""
        session_id = "test-session"
        transcript = "Test answer"
        
        with patch('app.services.real_time_feedback.get_ai_client_dependency', return_value=None):
            feedback = await service.process_transcript_chunk(
                session_id=session_id,
                transcript=transcript,
                question_id=1,
                job_description="JD",
                question_text="Question"
            )
            
            # Should still work without AI feedback
            assert feedback.feedback_type == FeedbackType.CONTENT_ANALYSIS
            assert feedback.suggestions is not None
    
    @pytest.mark.unit
    def test_register_session(self, service):
        """Test registering a session."""
        session_id = "test-session"
        user_id = "user-123"
        metadata = {"question_id": 1}
        
        service.register_session(session_id, user_id, metadata)
        
        session_info = service.get_session_info(session_id)
        assert session_info is not None
        assert session_info["user_id"] == user_id
        assert session_info["metadata"] == metadata
    
    @pytest.mark.unit
    def test_cleanup_session(self, service):
        """Test cleaning up a session."""
        session_id = "test-session"
        user_id = "user-123"
        
        service.register_session(session_id, user_id)
        assert service.get_session_info(session_id) is not None
        
        service.cleanup_session(session_id)
        assert service.get_session_info(session_id) is None
    
    @pytest.mark.unit
    def test_get_session_info_nonexistent(self, service):
        """Test getting info for non-existent session."""
        result = service.get_session_info("nonexistent-session")
        assert result is None
    
    @pytest.mark.unit
    def test_generate_feedback_message_no_suggestions(self, service):
        """Test generating feedback message with no suggestions."""
        analysis = SpeechAnalysis(
            filler_words=0,
            pace=150,
            clarity=0.8,
            volume=0.7,
            pauses=3,
            confidence=0.8
        )
        
        message = service._generate_feedback_message(analysis, [])
        
        assert "keep going" in message.lower() or "clear" in message.lower()
    
    @pytest.mark.unit
    def test_generate_feedback_message_with_suggestions(self, service):
        """Test generating feedback message with suggestions."""
        analysis = SpeechAnalysis(
            filler_words=10,
            pace=100,
            clarity=0.5,
            volume=0.7,
            pauses=1,
            confidence=0.5
        )
        
        suggestions = ["Try speaking faster", "Reduce filler words"]
        message = service._generate_feedback_message(analysis, suggestions)
        
        assert len(message) > 0
        assert any(s.lower() in message.lower() for s in suggestions)

