"""
Unit tests for TTS provider implementations.

Tests all TTS providers (Coqui, ElevenLabs, PlayHT) with mocked HTTP calls.
Covers retry logic, timeout handling, error handling, and health checks.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from app.services.tts.base import (
    BaseTTSProvider,
    TTSProviderError,
    TTSProviderTimeoutError,
    TTSProviderRateLimitError
)
from app.services.tts.coqui import CoquiTTSProvider
from app.services.tts.elevenlabs import ElevenLabsTTSProvider
from app.services.tts.playht import PlayHTTTSProvider
from app.services.tts.service import TTSService, CircuitBreaker
from app.services.tts.factory import TTSProviderFactory


class TestCoquiTTSProvider:
    """Tests for CoquiTTSProvider."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_success(self):
        """Test successful synthesis with Coqui provider."""
        config = {
            "base_url": "http://localhost:5002",
            "timeout": 30,
            "voice_id": "test-voice",
            "voice_version": 1
        }
        provider = CoquiTTSProvider(config)
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            audio_data = await provider.synthesize("Hello world", "test-voice", "mp3")
            assert audio_data == b"fake_audio_data"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_timeout(self):
        """Test timeout handling in Coqui provider."""
        config = {
            "base_url": "http://localhost:5002",
            "timeout": 30,
            "voice_id": "test-voice"
        }
        provider = CoquiTTSProvider(config)
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )
            
            with pytest.raises(TTSProviderTimeoutError):
                await provider.synthesize("Hello world")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_invalid_text(self):
        """Test validation of invalid text input."""
        config = {"base_url": "http://localhost:5002", "timeout": 30}
        provider = CoquiTTSProvider(config)
        
        with pytest.raises(TTSProviderError, match="Invalid text input"):
            await provider.synthesize("")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_invalid_format(self):
        """Test validation of invalid audio format."""
        config = {"base_url": "http://localhost:5002", "timeout": 30}
        provider = CoquiTTSProvider(config)
        
        with pytest.raises(TTSProviderError, match="Unsupported audio format"):
            await provider.synthesize("Hello", format="invalid")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        config = {"base_url": "http://localhost:5002", "timeout": 30}
        provider = CoquiTTSProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            is_healthy = await provider.health_check()
            assert is_healthy is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        config = {"base_url": "http://localhost:5002", "timeout": 30}
        provider = CoquiTTSProvider(config)
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Connection error")
            )
            
            is_healthy = await provider.health_check()
            assert is_healthy is False


class TestElevenLabsTTSProvider:
    """Tests for ElevenLabsTTSProvider."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_success(self):
        """Test successful synthesis with ElevenLabs provider."""
        config = {
            "api_key": "test-api-key-12345678901234567890",
            "base_url": "https://api.elevenlabs.io/v1",
            "timeout": 30,
            "voice_id": "test-voice"
        }
        provider = ElevenLabsTTSProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            audio_data = await provider.synthesize("Hello world", "test-voice", "mp3")
            assert audio_data == b"fake_audio_data"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_rate_limit(self):
        """Test rate limit error handling."""
        config = {
            "api_key": "test-api-key",
            "base_url": "https://api.elevenlabs.io/v1",
            "timeout": 30
        }
        provider = ElevenLabsTTSProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 429
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(TTSProviderRateLimitError):
                await provider.synthesize("Hello world")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_invalid_api_key(self):
        """Test invalid API key error."""
        config = {
            "api_key": "invalid-key",
            "base_url": "https://api.elevenlabs.io/v1",
            "timeout": 30
        }
        provider = ElevenLabsTTSProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(TTSProviderError, match="API key is invalid"):
                await provider.synthesize("Hello world")
    
    @pytest.mark.unit
    def test_missing_api_key(self):
        """Test initialization fails without API key."""
        config = {"base_url": "https://api.elevenlabs.io/v1", "timeout": 30}
        
        with pytest.raises(TTSProviderError, match="API key is required"):
            ElevenLabsTTSProvider(config)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        config = {
            "api_key": "test-api-key",
            "base_url": "https://api.elevenlabs.io/v1",
            "timeout": 30
        }
        provider = ElevenLabsTTSProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            is_healthy = await provider.health_check()
            assert is_healthy is True


class TestPlayHTTTSProvider:
    """Tests for PlayHTTTSProvider."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_success(self):
        """Test successful synthesis with PlayHT provider."""
        config = {
            "api_key": "test-api-key",
            "user_id": "test-user-id",
            "base_url": "https://api.play.ht/api/v1",
            "timeout": 30,
            "voice_id": "test-voice"
        }
        provider = PlayHTTTSProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake_audio_data"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            audio_data = await provider.synthesize("Hello world", "test-voice", "mp3")
            assert audio_data == b"fake_audio_data"
    
    @pytest.mark.unit
    def test_missing_api_key(self):
        """Test initialization fails without API key."""
        config = {
            "user_id": "test-user-id",
            "base_url": "https://api.play.ht/api/v1",
            "timeout": 30
        }
        
        with pytest.raises(TTSProviderError, match="API key is required"):
            PlayHTTTSProvider(config)
    
    @pytest.mark.unit
    def test_missing_user_id(self):
        """Test initialization fails without User ID."""
        config = {
            "api_key": "test-api-key",
            "base_url": "https://api.play.ht/api/v1",
            "timeout": 30
        }
        
        with pytest.raises(TTSProviderError, match="User ID is required"):
            PlayHTTTSProvider(config)


class TestTTSProviderFactory:
    """Tests for TTSProviderFactory."""
    
    @pytest.mark.unit
    def test_create_coqui_provider(self):
        """Test factory creates Coqui provider."""
        with patch("app.services.tts.factory.get_settings") as mock_settings:
            mock_settings.return_value.TTS_PROVIDER = "coqui"
            mock_settings.return_value.TTS_DEFAULT_VOICE_ID = "test-voice"
            mock_settings.return_value.TTS_VOICE_VERSION = 1
            mock_settings.return_value.TTS_TIMEOUT = 30
            
            provider = TTSProviderFactory.create_provider("coqui")
            assert isinstance(provider, CoquiTTSProvider)
    
    @pytest.mark.unit
    def test_create_elevenlabs_provider(self):
        """Test factory creates ElevenLabs provider."""
        with patch("app.services.tts.factory.get_settings") as mock_settings:
            mock_settings.return_value.TTS_PROVIDER = "elevenlabs"
            mock_settings.return_value.TTS_DEFAULT_VOICE_ID = "test-voice"
            mock_settings.return_value.TTS_VOICE_VERSION = 1
            mock_settings.return_value.TTS_TIMEOUT = 30
            mock_settings.return_value.ELEVENLABS_API_KEY = "test-key-12345678901234567890"
            
            provider = TTSProviderFactory.create_provider("elevenlabs")
            assert isinstance(provider, ElevenLabsTTSProvider)
    
    @pytest.mark.unit
    def test_create_elevenlabs_provider_missing_key(self):
        """Test factory fails when API key is missing."""
        with patch("app.services.tts.factory.get_settings") as mock_settings:
            mock_settings.return_value.TTS_PROVIDER = "elevenlabs"
            mock_settings.return_value.TTS_DEFAULT_VOICE_ID = "test-voice"
            mock_settings.return_value.TTS_VOICE_VERSION = 1
            mock_settings.return_value.TTS_TIMEOUT = 30
            mock_settings.return_value.ELEVENLABS_API_KEY = ""
            
            with pytest.raises(TTSProviderError, match="ELEVENLABS_API_KEY is required"):
                TTSProviderFactory.create_provider("elevenlabs")
    
    @pytest.mark.unit
    def test_create_invalid_provider(self):
        """Test factory raises error for invalid provider."""
        with pytest.raises(TTSProviderError, match="Unknown TTS provider"):
            TTSProviderFactory.create_provider("invalid_provider")


class TestTTSServiceRetryLogic:
    """Tests for retry logic in TTSService."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self, mock_tts_settings):
        """Test retry logic succeeds on second attempt."""
        # Create a mock provider that fails once then succeeds
        mock_provider = AsyncMock()
        mock_provider.synthesize = AsyncMock(
            side_effect=[
                TTSProviderError("Temporary failure"),
                b"success_audio_data"
            ]
        )
        
        with patch("app.services.tts.service.TTSProviderFactory.create_provider") as mock_factory:
            mock_factory.return_value = mock_provider
            
            service = TTSService()
            service.primary_provider = mock_provider
            service.primary_provider_name = "coqui"
            service.circuit_breakers["coqui"] = CircuitBreaker()
            
            audio_data = await service.synthesize("Hello world", use_cache=False)
            assert audio_data == b"success_audio_data"
            assert mock_provider.synthesize.call_count == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_exhausts_all_attempts(self, mock_tts_settings):
        """Test retry logic exhausts all attempts before failing."""
        # Create a mock provider that always fails
        mock_provider = AsyncMock()
        mock_provider.synthesize = AsyncMock(
            side_effect=TTSProviderError("Persistent failure")
        )
        
        service = TTSService()
        service.primary_provider = mock_provider
        service.primary_provider_name = "coqui"
        service.circuit_breakers["coqui"] = CircuitBreaker()
        
        with pytest.raises(TTSProviderError, match="Persistent failure"):
            await service.synthesize("Hello world", use_cache=False)
        
        # Should have tried 4 times (initial + 3 retries)
        assert mock_provider.synthesize.call_count == 4
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_skips_rate_limit_error(self, mock_tts_settings):
        """Test retry logic doesn't retry on rate limit errors."""
        mock_tts_settings.TTS_PROVIDER = "elevenlabs"
        
        mock_provider = AsyncMock()
        mock_provider.synthesize = AsyncMock(
            side_effect=TTSProviderRateLimitError("Rate limit exceeded")
        )
        
        service = TTSService()
        service.primary_provider = mock_provider
        service.primary_provider_name = "elevenlabs"
        service.circuit_breakers["elevenlabs"] = CircuitBreaker()
        
        with pytest.raises(TTSProviderRateLimitError):
            await service.synthesize("Hello world", use_cache=False)
        
        # Should only try once (no retry for rate limit)
        assert mock_provider.synthesize.call_count == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff_delays(self, mock_tts_settings):
        """Test retry logic uses exponential backoff delays."""
        import time
        
        mock_tts_settings.TTS_RETRY_ATTEMPTS = 2  # 2 retries = 3 total attempts
        
        mock_provider = AsyncMock()
        call_times = []
        
        async def mock_synthesize(*args, **kwargs):
            call_times.append(time.time())
            raise TTSProviderError("Temporary failure")
        
        mock_provider.synthesize = AsyncMock(side_effect=mock_synthesize)
        
        service = TTSService()
        service.primary_provider = mock_provider
        service.primary_provider_name = "coqui"
        service.circuit_breakers["coqui"] = CircuitBreaker()
        
        with pytest.raises(TTSProviderError):
            await service.synthesize("Hello world", use_cache=False)
        
        # Check that delays increased exponentially
        # First retry should be ~1s after first attempt
        # Second retry should be ~2s after second attempt
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.9  # Allow some tolerance
            assert delay1 <= 1.5
        
        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert delay2 >= 1.9  # Allow some tolerance
            assert delay2 <= 2.5


class TestCircuitBreaker:
    """Tests for CircuitBreaker implementation."""
    
    @pytest.mark.unit
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        assert cb.can_execute() is True
        assert cb.state == "closed"
    
    @pytest.mark.unit
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        
        # Record 5 failures
        for _ in range(5):
            cb.record_failure()
        
        assert cb.state == "open"
        assert cb.can_execute() is False
    
    @pytest.mark.unit
    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on success."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        
        # Record success - should reset
        cb.record_success()
        
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.can_execute() is True
    
    @pytest.mark.unit
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker enters half-open state after recovery timeout."""
        import time
        
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1.0)  # 1 second timeout
        
        # Open the circuit
        for _ in range(5):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
        
        # Fast-forward past recovery timeout instead of sleeping
        with patch('app.services.tts.service.time.time', return_value=time.time() + 1.1):
            # Should be in half-open state
            assert cb.can_execute() is True
            assert cb.state == "half_open"
        
        # Success should close it
        cb.record_success()
        assert cb.state == "closed"

