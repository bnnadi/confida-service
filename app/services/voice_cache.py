"""
Voice Cache Service with Singleflight Pattern

This service caches TTS synthesis results using deterministic cache keys and implements
the singleflight pattern to prevent duplicate synthesis requests for concurrent requests
with the same text/voice combination.
"""

import hashlib
import asyncio
import base64
from typing import Optional, Dict, Any, Callable, Awaitable
from app.utils.cache import cache_manager
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VoiceCacheService:
    """
    Service for caching TTS synthesis results with singleflight pattern.
    
    The singleflight pattern ensures that concurrent requests for the same text/voice
    combination wait for the first synthesis to complete, preventing duplicate API calls.
    """
    
    def __init__(self):
        """Initialize voice cache service."""
        self.settings = get_settings()
        self.cache = cache_manager
        self.cache_enabled = self.settings.CACHE_ENABLED
        self.cache_ttl = self.settings.TTS_CACHE_TTL
        
        # Singleflight pattern: track in-flight requests by cache key
        # Maps cache_key -> future
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._in_flight_lock = asyncio.Lock()
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "singleflight_hits": 0  # Requests that waited for in-flight synthesis
        }
        
        logger.info(
            f"VoiceCacheService initialized: enabled={self.cache_enabled}, "
            f"ttl={self.cache_ttl}s"
        )
    
    def generate_settings_hash(self) -> str:
        """
        Generate hash of TTS settings that affect synthesis output.
        
        This ensures cache invalidation when settings change (e.g., voice version,
        provider configuration).
        
        Returns:
            str: SHA256 hash of relevant settings
        """
        settings_data = {
            "voice_version": self.settings.TTS_VOICE_VERSION,
            "default_voice_id": self.settings.TTS_DEFAULT_VOICE_ID,
            "default_format": self.settings.TTS_DEFAULT_FORMAT,
            "provider": self.settings.TTS_PROVIDER,
        }
        
        # Create deterministic string representation
        settings_str = "|".join(f"{k}:{v}" for k, v in sorted(settings_data.items()))
        return hashlib.sha256(settings_str.encode()).hexdigest()[:16]  # Use first 16 chars
    
    def _build_cache_value(
        self,
        file_id: str,
        voice_id: str,
        format: str,
        duration: float,
        question_id: Optional[str],
        version: int,
        settings_hash: str,
        audio_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Build cache value dictionary.
        
        Args:
            file_id: File ID where audio is stored
            voice_id: Voice identifier
            format: Audio format
            duration: Audio duration in seconds
            question_id: Optional question ID
            version: Voice version number
            settings_hash: Settings hash
            audio_data: Optional raw audio bytes
            
        Returns:
            Dict with cache value
        """
        cache_value = {
            "file_id": file_id,
            "question_id": question_id,
            "voice_id": voice_id,
            "version": version,
            "duration": duration,
            "format": format,
            "settings_hash": settings_hash
        }
        if audio_data:
            cache_value["audio_data"] = base64.b64encode(audio_data).decode('utf-8')
        return cache_value
    
    def generate_cache_key(
        self,
        text: str,
        voice_id: str,
        format: str,
        settings_hash: str
    ) -> str:
        """
        Generate deterministic cache key for TTS request.
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            format: Audio format
            settings_hash: Hash of TTS settings
            
        Returns:
            str: Cache key (SHA256 hash)
        """
        # Create deterministic key data
        key_data = f"{text}|{voice_id}|{format}|{settings_hash}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"voice_cache:{key_hash}"
    
    def _get_cache_key_with_hash(
        self,
        text: str,
        voice_id: str,
        format: str,
        settings_hash: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Get cache key and settings hash. Helper to avoid duplication.
        
        Returns:
            tuple: (cache_key, settings_hash)
        """
        if settings_hash is None:
            settings_hash = self.generate_settings_hash()
        cache_key = self.generate_cache_key(text, voice_id, format, settings_hash)
        return cache_key, settings_hash
    
    async def get_cached_voice(
        self,
        text: str,
        voice_id: str,
        format: str,
        settings_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached voice synthesis result.
        
        Args:
            text: Text that was synthesized
            voice_id: Voice identifier used
            format: Audio format
            settings_hash: Optional settings hash (generated if not provided)
            
        Returns:
            Dict with voice metadata (file_id, question_id, voice_id, version, duration, format)
            or None if not cached
        """
        if not self.cache_enabled:
            return None
        
        cache_key, _ = self._get_cache_key_with_hash(text, voice_id, format, settings_hash)
        
        try:
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                self.stats["hits"] += 1
                logger.debug(f"Voice cache hit for key: {cache_key[:32]}...")
                return cached_data
            else:
                self.stats["misses"] += 1
                logger.debug(f"Voice cache miss for key: {cache_key[:32]}...")
                return None
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Error getting cached voice: {e}")
            return None
    
    async def cache_voice(
        self,
        text: str,
        voice_id: str,
        format: str,
        file_id: str,
        duration: float,
        question_id: Optional[str] = None,
        version: int = 1,
        settings_hash: Optional[str] = None,
        audio_data: Optional[bytes] = None
    ) -> bool:
        """
        Cache voice synthesis result.
        
        Args:
            text: Text that was synthesized
            voice_id: Voice identifier used
            format: Audio format
            file_id: File ID where audio is stored
            duration: Audio duration in seconds
            question_id: Optional question ID associated with this voice
            version: Voice version number
            settings_hash: Optional settings hash (generated if not provided)
            audio_data: Optional raw audio bytes (for backward compatibility)
            
        Returns:
            bool: True if cached successfully, False otherwise
        """
        if not (self.cache_enabled and file_id):
            return False
        
        cache_key, settings_hash = self._get_cache_key_with_hash(text, voice_id, format, settings_hash)
        
        # Build cache value with metadata
        cache_value = self._build_cache_value(
            file_id, voice_id, format, duration, question_id, version, settings_hash, audio_data
        )
        
        try:
            success = await self.cache.set(cache_key, cache_value, ttl=self.cache_ttl)
            if success:
                logger.debug(f"Cached voice metadata for key: {cache_key[:32]}...")
            return success
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"Error caching voice: {e}")
            return False
    
    async def get_or_synthesize(
        self,
        cache_key: str,
        synthesize_fn: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Get cached voice or synthesize using singleflight pattern.
        
        This method implements the singleflight pattern: if multiple concurrent requests
        ask for the same cache key, they all wait for the first synthesis to complete.
        
        Args:
            cache_key: Cache key for this request
            synthesize_fn: Async function that performs synthesis and returns voice metadata
            
        Returns:
            Dict with voice metadata (file_id, question_id, voice_id, version, duration, format)
        """
        # Check cache first (outside of singleflight to avoid blocking on cache reads)
        cached = await self.cache.get(cache_key)
        if cached:
            self.stats["hits"] += 1
            logger.debug(f"Voice cache hit (before singleflight) for key: {cache_key[:32]}...")
            return cached
        
        # Singleflight pattern: check if synthesis is already in progress
        async with self._in_flight_lock:
            if cache_key in self._in_flight:
                # Another request is already synthesizing, wait for it
                future = self._in_flight[cache_key]
                logger.debug(f"Singleflight: waiting for in-flight synthesis for key: {cache_key[:32]}...")
                self.stats["singleflight_hits"] += 1
                return await future  # Let exceptions propagate naturally
            
            # Create a new future for this synthesis
            future = asyncio.Future()
            self._in_flight[cache_key] = future
        
        # Perform synthesis
        try:
            result = await synthesize_fn()
            
            # Cache the result
            if result:
                await self.cache.set(cache_key, result, ttl=self.cache_ttl)
            
            # Set the future result so waiting requests can proceed
            future.set_result(result)
            
            self.stats["misses"] += 1
            logger.debug(f"Voice synthesis completed and cached for key: {cache_key[:32]}...")
            return result
            
        except Exception as e:
            # Set exception on future so waiting requests get the error
            future.set_exception(e)
            self.stats["errors"] += 1
            logger.error(f"Voice synthesis failed: {e}")
            # Ensure the future's exception is "retrieved" to avoid "Future exception
            # was never retrieved" when waiters are cancelled (e.g. by gather)
            future.add_done_callback(lambda f: f.exception())
            raise

        finally:
            # Clean up in-flight tracking
            async with self._in_flight_lock:
                self._in_flight.pop(cache_key, None)  # Safer than del
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics (hits, misses, errors, singleflight_hits, hit_rate)
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "singleflight_hits": self.stats["singleflight_hits"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "in_flight_count": len(self._in_flight)
        }
    
    def reset_stats(self):
        """Reset cache statistics."""
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
            "singleflight_hits": 0
        }
        logger.info("Voice cache statistics reset")


# Global voice cache service instance
_voice_cache_service: Optional[VoiceCacheService] = None


def get_voice_cache_service() -> VoiceCacheService:
    """
    Get the global voice cache service instance.
    
    Returns:
        VoiceCacheService: Voice cache service instance
    """
    global _voice_cache_service
    if _voice_cache_service is None:
        _voice_cache_service = VoiceCacheService()
    return _voice_cache_service

