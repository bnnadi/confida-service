"""
Integration tests for TTS fallback behavior.

Tests the complete TTS service with fallback chain, circuit breaker,
and retry logic in realistic scenarios.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.tts.base import TTSProviderError
from app.services.tts.service import CircuitBreaker
from app.services.tts.factory import TTSProviderFactory


class TestTTSFallbackBehavior:
    """Tests for fallback behavior in TTSService."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fallback_to_secondary_provider(self, mock_tts_settings, tts_service_with_providers):
        """Test fallback chain: primary fails, fallback succeeds."""
        mock_tts_settings.TTS_FALLBACK_PROVIDER = "elevenlabs"
        mock_tts_settings.TTS_RETRY_ATTEMPTS = 1  # Quick test
        
        # Create mock providers
        primary_provider = AsyncMock()
        primary_provider.synthesize = AsyncMock(
            side_effect=TTSProviderError("Primary provider failed")
        )
        
        fallback_provider = AsyncMock()
        fallback_provider.synthesize = AsyncMock(
            return_value=b"fallback_audio_data"
        )
        
        service = tts_service_with_providers(primary_provider, fallback_provider)
        
        audio_data = await service.synthesize("Hello world", use_cache=False)
        
        assert audio_data == b"fallback_audio_data"
        assert primary_provider.synthesize.call_count >= 1
        assert fallback_provider.synthesize.call_count >= 1
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fallback_both_providers_fail(self, mock_tts_settings, tts_service_with_providers):
        """Test fallback chain: both primary and fallback fail."""
        mock_tts_settings.TTS_FALLBACK_PROVIDER = "elevenlabs"
        mock_tts_settings.TTS_RETRY_ATTEMPTS = 1
        
        primary_provider = AsyncMock()
        primary_provider.synthesize = AsyncMock(
            side_effect=TTSProviderError("Primary provider failed")
        )
        
        fallback_provider = AsyncMock()
        fallback_provider.synthesize = AsyncMock(
            side_effect=TTSProviderError("Fallback provider failed")
        )
        
        service = tts_service_with_providers(primary_provider, fallback_provider)
        
        with pytest.raises(TTSProviderError, match="All TTS providers failed"):
            await service.synthesize("Hello world", use_cache=False)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_execution(self, mock_tts_settings, tts_service_with_providers):
        """Test circuit breaker prevents execution when open."""
        provider = AsyncMock()
        provider.synthesize = AsyncMock(return_value=b"audio_data")
        
        circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        # Open the circuit
        for _ in range(5):
            circuit_breaker.record_failure()
        
        service = tts_service_with_providers(provider)
        service.circuit_breakers["coqui"] = circuit_breaker
        
        with pytest.raises(TTSProviderError, match="Circuit breaker is open"):
            await service.synthesize("Hello world", use_cache=False)
        
        # Provider should not be called when circuit is open
        assert provider.synthesize.call_count == 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self, mock_tts_settings, tts_service_with_providers):
        """Test circuit breaker recovers through half-open state."""
        provider = AsyncMock()
        provider.synthesize = AsyncMock(return_value=b"audio_data")
        
        import time
        
        circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=1.0)  # 1 second
        # Open the circuit
        for _ in range(5):
            circuit_breaker.record_failure()
        
        # Fast-forward past recovery timeout instead of sleeping
        with patch('app.services.tts.service.time.time', return_value=time.time() + 1.1):
            service = tts_service_with_providers(provider)
            service.circuit_breakers["coqui"] = circuit_breaker
            
            # Should succeed now (circuit is half-open)
            audio_data = await service.synthesize("Hello world", use_cache=False)
            assert audio_data == b"audio_data"
        
        # Circuit should be closed after success
        assert circuit_breaker.state == "closed"
        assert circuit_breaker.failure_count == 0


class TestTTSProviderFactoryIntegration:
    """Integration tests for TTSProviderFactory."""
    
    @pytest.mark.integration
    def test_factory_creates_coqui_provider(self):
        """Test factory creates Coqui provider with correct config."""
        with patch("app.services.tts.factory.get_settings") as mock_settings:
            mock_settings.return_value.TTS_PROVIDER = "coqui"
            mock_settings.return_value.TTS_DEFAULT_VOICE_ID = "test-voice"
            mock_settings.return_value.TTS_VOICE_VERSION = 1
            mock_settings.return_value.TTS_TIMEOUT = 30
            mock_settings.return_value.ELEVENLABS_API_KEY = ""
            mock_settings.return_value.PLAYHT_API_KEY = ""
            mock_settings.return_value.PLAYHT_USER_ID = ""
            
            provider = TTSProviderFactory.create_provider("coqui")
            
            assert provider is not None
            assert isinstance(provider, type(TTSProviderFactory.PROVIDER_REGISTRY["coqui"]))
            assert provider.config["voice_id"] == "test-voice"
            assert provider.config["timeout"] == 30
    
    @pytest.mark.integration
    def test_factory_validates_api_keys(self):
        """Test factory validates API keys for vendor providers."""
        with patch("app.services.tts.factory.get_settings") as mock_settings:
            mock_settings.return_value.TTS_PROVIDER = "elevenlabs"
            mock_settings.return_value.TTS_DEFAULT_VOICE_ID = "test-voice"
            mock_settings.return_value.TTS_VOICE_VERSION = 1
            mock_settings.return_value.TTS_TIMEOUT = 30
            mock_settings.return_value.ELEVENLABS_API_KEY = ""  # Missing key
            mock_settings.return_value.PLAYHT_API_KEY = ""
            mock_settings.return_value.PLAYHT_USER_ID = ""
            
            with pytest.raises(TTSProviderError, match="ELEVENLABS_API_KEY is required"):
                TTSProviderFactory.create_provider("elevenlabs")


class TestTTSRetryAndFallbackIntegration:
    """Integration tests combining retry logic and fallback."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_retry_then_fallback(self, mock_tts_settings, tts_service_with_providers):
        """Test retry on primary, then fallback succeeds."""
        mock_tts_settings.TTS_FALLBACK_PROVIDER = "elevenlabs"
        mock_tts_settings.TTS_RETRY_ATTEMPTS = 2  # 2 retries = 3 total attempts
        
        primary_provider = AsyncMock()
        # Primary fails twice (retries), then we move to fallback
        primary_provider.synthesize = AsyncMock(
            side_effect=TTSProviderError("Primary provider failed")
        )
        
        fallback_provider = AsyncMock()
        fallback_provider.synthesize = AsyncMock(
            return_value=b"fallback_audio_data"
        )
        
        service = tts_service_with_providers(primary_provider, fallback_provider)
        
        audio_data = await service.synthesize("Hello world", use_cache=False)
        
        assert audio_data == b"fallback_audio_data"
        # Primary should have been retried (3 attempts)
        assert primary_provider.synthesize.call_count == 3
        # Fallback should have been called once
        assert fallback_provider.synthesize.call_count == 1
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_primary_succeeds_after_retry(self, mock_tts_settings, tts_service_with_providers):
        """Test primary provider succeeds after retry, no fallback needed."""
        mock_tts_settings.TTS_FALLBACK_PROVIDER = "elevenlabs"
        
        primary_provider = AsyncMock()
        # Fail twice, then succeed
        primary_provider.synthesize = AsyncMock(
            side_effect=[
                TTSProviderError("Temporary failure"),
                TTSProviderError("Temporary failure"),
                b"success_audio_data"
            ]
        )
        
        fallback_provider = AsyncMock()
        
        service = tts_service_with_providers(primary_provider, fallback_provider)
        
        audio_data = await service.synthesize("Hello world", use_cache=False)
        
        assert audio_data == b"success_audio_data"
        # Primary should have succeeded on 3rd attempt
        assert primary_provider.synthesize.call_count == 3
        # Fallback should not have been called
        assert fallback_provider.synthesize.call_count == 0

