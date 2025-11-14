"""
TTS Service

High-level service wrapper that provides fallback logic, circuit breaker pattern,
and caching for TTS providers.
"""

import time
import hashlib
import base64
from typing import Optional, Dict
from app.services.tts.base import BaseTTSProvider, TTSProviderError
from app.services.tts.factory import TTSProviderFactory
from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.cache import cache_manager

logger = get_logger(__name__)


class CircuitBreaker:
    """
    Simple circuit breaker implementation for TTS providers.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def can_execute(self) -> bool:
        """
        Check if operation can be executed.
        
        Returns:
            bool: True if operation can be executed
        """
        if self.state == "closed":
            return True
        
        if self.state == "half_open":
            return True
        
        # State is "open" - check if recovery timeout has passed
        if self.last_failure_time and \
           (time.time() - self.last_failure_time) > self.recovery_timeout:
            self.state = "half_open"
            logger.info("Circuit breaker entering half-open state")
            return True
        
        return False
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "closed"
        logger.debug("Circuit breaker closed after success")
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout}s"
            )


class TTSService:
    """
    High-level TTS service with fallback and circuit breaker support.
    """
    
    def __init__(self):
        """Initialize TTS service."""
        self.settings = get_settings()
        self.cache = cache_manager
        self.cache_enabled = self.settings.CACHE_ENABLED
        self.cache_ttl = self.settings.TTS_CACHE_TTL
        
        # Initialize primary provider
        self.primary_provider_name = self.settings.TTS_PROVIDER
        self.primary_provider: Optional[BaseTTSProvider] = None
        
        # Initialize fallback provider if configured
        self.fallback_provider_name = self.settings.TTS_FALLBACK_PROVIDER
        self.fallback_provider: Optional[BaseTTSProvider] = None
        
        # Circuit breakers for each provider
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # Initialize providers
        self._initialize_providers()
        
        logger.info(
            f"TTS Service initialized: primary={self.primary_provider_name}, "
            f"fallback={self.fallback_provider_name or 'none'}"
        )
    
    def _initialize_provider(self, provider_name: str, is_required: bool = False) -> Optional[BaseTTSProvider]:
        """
        Initialize a single TTS provider.
        
        Args:
            provider_name: Name of the provider to initialize
            is_required: If True, raises exception on failure; if False, returns None
            
        Returns:
            BaseTTSProvider or None: Provider instance if successful
        """
        try:
            provider = TTSProviderFactory.create_provider(provider_name)
            self.circuit_breakers[provider_name] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60.0
            )
            logger.info(f"TTS provider initialized: {provider_name}")
            return provider
        except Exception as e:
            error_msg = f"Failed to initialize TTS provider '{provider_name}': {e}"
            if is_required:
                logger.error(error_msg)
                raise
            else:
                logger.warning(error_msg)
                return None
    
    def _initialize_providers(self):
        """Initialize primary and fallback providers."""
        self.primary_provider = self._initialize_provider(
            self.primary_provider_name,
            is_required=True
        )
        
        if self.fallback_provider_name:
            self.fallback_provider = self._initialize_provider(
                self.fallback_provider_name,
                is_required=False
            )
    
    def _get_cache_key(
        self,
        text: str,
        voice_id: Optional[str],
        audio_format: str,
        provider_name: str
    ) -> str:
        """
        Generate cache key for TTS request.
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            format: Audio format
            provider_name: Provider name
            
        Returns:
            str: Cache key
        """
        key_data = f"tts:{provider_name}:{voice_id}:{audio_format}:{text}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def _get_cached_audio(
        self,
        text: str,
        voice_id: str,
        audio_format: str,
        provider_name: str
    ) -> Optional[bytes]:
        """
        Get cached audio if available.
        
        Args:
            text: Text that was synthesized
            voice_id: Voice identifier used
            audio_format: Audio format
            provider_name: Provider name
            
        Returns:
            bytes or None: Cached audio data if found, None otherwise
        """
        if not (self.cache_enabled):
            return None
        
        cache_key = self._get_cache_key(text, voice_id, audio_format, provider_name)
        cached_audio_b64 = await self.cache.get(cache_key)
        
        if not cached_audio_b64:
            return None
        
        try:
            logger.debug("TTS cache hit")
            return base64.b64decode(cached_audio_b64)
        except Exception as e:
            logger.warning(f"Failed to decode cached audio: {e}")
            return None
    
    async def _cache_audio(
        self,
        audio_data: bytes,
        text: str,
        voice_id: str,
        audio_format: str,
        provider_name: str
    ):
        """
        Cache synthesized audio.
        
        Args:
            audio_data: Audio data to cache
            text: Text that was synthesized
            voice_id: Voice identifier used
            audio_format: Audio format
            provider_name: Provider name
        """
        if not (self.cache_enabled and audio_data):
            return
        
        cache_key = self._get_cache_key(text, voice_id, audio_format, provider_name)
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        await self.cache.set(cache_key, audio_b64, ttl=self.cache_ttl)
    
    async def _synthesize_with_provider(
        self,
        provider: BaseTTSProvider,
        provider_name: str,
        text: str,
        voice_id: str,
        audio_format: str,
        use_cache: bool,
        **kwargs
    ) -> bytes:
        """
        Synthesize with a specific provider and handle caching.
        
        Args:
            provider: TTS provider instance
            provider_name: Name of the provider
            text: Text to synthesize
            voice_id: Voice identifier
            audio_format: Audio format
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            bytes: Audio data
            
        Raises:
            TTSProviderError: If synthesis fails
        """
        audio_data = await self._try_provider(
            provider,
            provider_name,
            text,
            voice_id,
            audio_format,
            **kwargs
        )
        
        if use_cache:
            await self._cache_audio(
                audio_data,
                text,
                voice_id,
                audio_format,
                provider_name
            )
        
        return audio_data
    
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        audio_format: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> bytes:
        """
        Synthesize text to speech with fallback support.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice identifier (uses default if not provided)
            format: Audio format (uses default if not provided)
            use_cache: Whether to use cache (default: True)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            bytes: Audio data
            
        Raises:
            TTSProviderError: If all providers fail
        """
        voice = voice_id or self.settings.TTS_DEFAULT_VOICE_ID
        audio_format = audio_format or self.settings.TTS_DEFAULT_FORMAT
        
        # Try cache first
        if use_cache:
            cached_audio = await self._get_cached_audio(
                text, voice, audio_format, self.primary_provider_name
            )
            if cached_audio:
                return cached_audio
        
        # Try primary provider
        if self.primary_provider:
            try:
                return await self._synthesize_with_provider(
                    self.primary_provider,
                    self.primary_provider_name,
                    text,
                    voice,
                    audio_format,
                    use_cache,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Primary provider failed: {e}")
        
        # Try fallback provider
        if self.fallback_provider:
            try:
                logger.info(f"Trying fallback provider: {self.fallback_provider_name}")
                return await self._synthesize_with_provider(
                    self.fallback_provider,
                    self.fallback_provider_name,
                    text,
                    voice,
                    audio_format,
                    use_cache,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"Fallback provider failed: {e}")
        
        # All providers failed
        raise TTSProviderError(
            f"All TTS providers failed. Primary: {self.primary_provider_name}, "
            f"Fallback: {self.fallback_provider_name or 'none'}"
        )
    
    async def _try_provider(
        self,
        provider: BaseTTSProvider,
        provider_name: str,
        text: str,
        voice_id: str,
        audio_format: str,
        **kwargs
    ) -> bytes:
        """
        Try to synthesize with a specific provider.
        
        Args:
            provider: TTS provider instance
            provider_name: Name of the provider
            text: Text to synthesize
            voice_id: Voice identifier
            format: Audio format
            **kwargs: Additional parameters
            
        Returns:
            bytes: Audio data
            
        Raises:
            TTSProviderError: If synthesis fails
        """
        # Check circuit breaker
        circuit_breaker = self.circuit_breakers.get(provider_name)
        if circuit_breaker and not circuit_breaker.can_execute():
            raise TTSProviderError(
                f"Circuit breaker is open for {provider_name}. "
                f"Provider is temporarily unavailable."
            )
        
        try:
            audio_data = await provider.synthesize(text, voice_id, audio_format, **kwargs)
            
            # Record success
            if circuit_breaker:
                circuit_breaker.record_success()
            
            return audio_data
        except Exception:
            # Record failure
            if circuit_breaker:
                circuit_breaker.record_failure()
            
            raise
    
    async def _check_provider_health(
        self,
        provider: BaseTTSProvider,
        provider_name: str
    ) -> bool:
        """
        Check health of a single provider.
        
        Args:
            provider: Provider instance to check
            provider_name: Name of the provider
            
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            return await provider.health_check()
        except Exception as e:
            logger.warning(f"Health check failed for {provider_name}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all providers.
        
        Returns:
            Dict[str, bool]: Health status for each provider
        """
        health_status = {}
        
        providers = [
            (self.primary_provider, self.primary_provider_name),
            (self.fallback_provider, self.fallback_provider_name)
        ]
        
        for provider, provider_name in providers:
            if provider:
                health_status[provider_name] = await self._check_provider_health(
                    provider, provider_name
                )
        
        return health_status


# Global TTS service instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """
    Get the global TTS service instance.
    
    Returns:
        TTSService: TTS service instance
    """
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

