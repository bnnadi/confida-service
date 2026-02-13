"""
Unit tests for SpeechAnalyzer service.
"""
import pytest
from app.services.speech_analyzer import SpeechAnalyzer
from app.models.real_time_models import SpeechAnalysis


class TestSpeechAnalyzer:
    """Test cases for SpeechAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create SpeechAnalyzer instance."""
        return SpeechAnalyzer()
    
    @pytest.mark.unit
    def test_analyze_transcript_empty(self, analyzer):
        """Test analyzing empty transcript."""
        result = analyzer.analyze_transcript("")
        assert isinstance(result, SpeechAnalysis)
        assert result.filler_words == 0
        assert result.pace == 0.0
        assert result.clarity == 0.0
    
    @pytest.mark.unit
    def test_analyze_transcript_basic(self, analyzer):
        """Test analyzing basic transcript."""
        transcript = "This is a test transcript with some words."
        result = analyzer.analyze_transcript(transcript)
        
        assert isinstance(result, SpeechAnalysis)
        assert result.filler_words >= 0
        assert result.pace > 0
        assert 0.0 <= result.clarity <= 1.0
        assert result.confidence >= 0.0
        assert result.transcript == transcript
    
    @pytest.mark.unit
    def test_analyze_transcript_with_filler_words(self, analyzer):
        """Test analyzing transcript with filler words."""
        transcript = "Um, this is, uh, a test with, like, filler words, you know."
        result = analyzer.analyze_transcript(transcript)
        
        assert result.filler_words > 0
        assert result.clarity < 1.0  # Should be penalized for filler words
    
    @pytest.mark.unit
    def test_analyze_transcript_pace_calculation(self, analyzer):
        """Test pace calculation."""
        transcript = " ".join(["word"] * 100)  # 100 words
        result = analyzer.analyze_transcript(transcript)
        
        # Pace should be roughly 2 words per second = 120 WPM
        assert result.pace > 0
        assert result.pace == 200  # 100 words * 2
    
    @pytest.mark.unit
    def test_analyze_transcript_pauses(self, analyzer):
        """Test pause detection."""
        transcript = "First sentence. Second sentence. Third sentence!"
        result = analyzer.analyze_transcript(transcript)
        
        assert result.pauses >= 0
    
    @pytest.mark.unit
    def test_analyze_audio_chunk_with_transcript(self, analyzer):
        """Test analyzing audio chunk with transcript."""
        audio_data = b"fake_audio_data"
        transcript = "This is a transcript"
        
        result = analyzer.analyze_audio_chunk(audio_data, transcript)
        
        assert isinstance(result, SpeechAnalysis)
        assert result.transcript == transcript
    
    @pytest.mark.unit
    def test_analyze_audio_chunk_without_transcript(self, analyzer):
        """Test analyzing audio chunk without transcript."""
        audio_data = b"fake_audio_data"
        
        result = analyzer.analyze_audio_chunk(audio_data, None)
        
        assert isinstance(result, SpeechAnalysis)
        assert result.transcript is None
        assert result.clarity == 0.5  # Default value
    
    @pytest.mark.unit
    def test_get_realtime_suggestions_slow_pace(self, analyzer):
        """Test suggestions for slow speaking pace."""
        analysis = SpeechAnalysis(
            filler_words=0,
            pace=100,  # Below optimal (140-180)
            clarity=0.8,
            volume=0.7,
            pauses=3,
            confidence=0.7
        )
        
        suggestions = analyzer.get_realtime_suggestions(analysis)
        
        assert len(suggestions) > 0
        assert any("faster" in s.lower() for s in suggestions)
    
    @pytest.mark.unit
    def test_get_realtime_suggestions_fast_pace(self, analyzer):
        """Test suggestions for fast speaking pace."""
        analysis = SpeechAnalysis(
            filler_words=0,
            pace=200,  # Above optimal (140-180)
            clarity=0.8,
            volume=0.7,
            pauses=3,
            confidence=0.7
        )
        
        suggestions = analyzer.get_realtime_suggestions(analysis)
        
        assert len(suggestions) > 0
        assert any("slower" in s.lower() or "slowing" in s.lower() for s in suggestions)
    
    @pytest.mark.unit
    def test_get_realtime_suggestions_filler_words(self, analyzer):
        """Test suggestions for excessive filler words."""
        analysis = SpeechAnalysis(
            filler_words=10,  # Above threshold (5)
            pace=150,
            clarity=0.6,
            volume=0.7,
            pauses=3,
            confidence=0.6
        )
        
        suggestions = analyzer.get_realtime_suggestions(analysis)
        
        assert len(suggestions) > 0
        assert any("filler" in s.lower() for s in suggestions)
    
    @pytest.mark.unit
    def test_get_realtime_suggestions_excessive_pauses(self, analyzer):
        """Test suggestions when pauses exceed threshold (>10)."""
        analysis = SpeechAnalysis(
            filler_words=0,
            pace=150,
            clarity=0.8,
            volume=0.7,
            pauses=11,
            confidence=0.8
        )
        suggestions = analyzer.get_realtime_suggestions(analysis)
        assert any("continuously" in s.lower() or "pauses" in s.lower() for s in suggestions)

    @pytest.mark.unit
    def test_get_realtime_suggestions_low_clarity(self, analyzer):
        """Test suggestions for low clarity."""
        analysis = SpeechAnalysis(
            filler_words=2,
            pace=150,
            clarity=0.5,  # Below threshold (0.6)
            volume=0.7,
            pauses=3,
            confidence=0.5
        )
        
        suggestions = analyzer.get_realtime_suggestions(analysis)
        
        assert len(suggestions) > 0
        assert any("clarity" in s.lower() or "articulation" in s.lower() for s in suggestions)
    
    @pytest.mark.unit
    def test_get_realtime_suggestions_optimal(self, analyzer):
        """Test suggestions when speech is optimal."""
        analysis = SpeechAnalysis(
            filler_words=2,
            pace=160,  # Within optimal range
            clarity=0.8,
            volume=0.7,
            pauses=5,  # Within reasonable range
            confidence=0.8
        )
        
        suggestions = analyzer.get_realtime_suggestions(analysis)
        
        # Should have minimal or no suggestions for optimal speech
        assert isinstance(suggestions, list)
    
    @pytest.mark.unit
    def test_reset(self, analyzer):
        """Test resetting analyzer state."""
        # Add some data
        analyzer.analyze_transcript("test")
        analyzer.analyze_audio_chunk(b"data")
        
        # Reset
        analyzer.reset()
        
        # Buffers should be cleared
        assert len(analyzer.transcript_buffer) == 0
        assert len(analyzer.audio_chunks) == 0

