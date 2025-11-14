"""
Unit tests for Voice Cache Service.

Tests the voice cache service including:
- Cache key generation (deterministic)
- Cache hit/miss behavior
- Singleflight pattern
- Settings hash generation
- Statistics tracking
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.voice_cache import VoiceCacheService, get_voice_cache_service


class TestVoiceCacheService:
    """Tests for VoiceCacheService."""
    
    @pytest.fixture
    def voice_cache(self):
        """Create VoiceCacheService instance for testing."""
        return VoiceCacheService()
    
    @pytest.mark.unit
    def test_settings_hash_generation(self, voice_cache):
        """Test settings hash is deterministic."""
        hash1 = voice_cache.generate_settings_hash()
        hash2 = voice_cache.generate_settings_hash()
        
        # Same settings should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # First 16 chars of SHA256
    
    @pytest.mark.unit
    def test_cache_key_generation(self, voice_cache):
        """Test cache key generation is deterministic."""
        settings_hash = voice_cache.generate_settings_hash()
        
        key1 = voice_cache.generate_cache_key("test text", "voice1", "mp3", settings_hash)
        key2 = voice_cache.generate_cache_key("test text", "voice1", "mp3", settings_hash)
        
        # Same inputs should produce same key
        assert key1 == key2
        assert key1.startswith("voice_cache:")
        
        # Different inputs should produce different keys
        key3 = voice_cache.generate_cache_key("different text", "voice1", "mp3", settings_hash)
        assert key1 != key3
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_cached_voice_miss(self, voice_cache):
        """Test cache miss returns None."""
        result = await voice_cache.get_cached_voice("test text", "voice1", "mp3")
        
        assert result is None
        assert voice_cache.stats["misses"] == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_voice_and_get(self, voice_cache):
        """Test caching and retrieving voice data."""
        # Cache voice data
        success = await voice_cache.cache_voice(
            text="test text",
            voice_id="voice1",
            format="mp3",
            file_id="file123",
            duration=5.5,
            version=1
        )
        
        assert success is True
        
        # Retrieve cached data
        cached = await voice_cache.get_cached_voice("test text", "voice1", "mp3")
        
        assert cached is not None
        assert cached["file_id"] == "file123"
        assert cached["voice_id"] == "voice1"
        assert cached["duration"] == 5.5
        assert cached["format"] == "mp3"
        assert voice_cache.stats["hits"] == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_with_audio_data(self, voice_cache):
        """Test caching includes audio data when provided."""
        audio_bytes = b"fake audio data"
        
        success = await voice_cache.cache_voice(
            text="test text",
            voice_id="voice1",
            format="mp3",
            file_id="file123",
            duration=5.5,
            audio_data=audio_bytes
        )
        
        assert success is True
        
        cached = await voice_cache.get_cached_voice("test text", "voice1", "mp3")
        assert cached is not None
        assert "audio_data" in cached
        assert cached["audio_data"] is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_singleflight_pattern(self, voice_cache):
        """Test singleflight pattern prevents duplicate synthesis."""
        call_count = 0
        
        async def mock_synthesize():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate synthesis time
            return {"audio_data": "encoded_audio", "provider": "test"}
        
        # Simulate 5 concurrent requests for same cache key
        cache_key = voice_cache.generate_cache_key(
            "test text", "voice1", "mp3", voice_cache.generate_settings_hash()
        )
        
        async def request():
            return await voice_cache.get_or_synthesize(cache_key, mock_synthesize)
        
        # Run 5 concurrent requests
        results = await asyncio.gather(*[request() for _ in range(5)])
        
        # Should only call synthesize once (singleflight)
        assert call_count == 1
        
        # All requests should get same result
        assert all(r == results[0] for r in results)
        
        # Should have 4 singleflight hits (4 requests waited for 1st)
        assert voice_cache.stats["singleflight_hits"] == 4
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_singleflight_error_propagation(self, voice_cache):
        """Test singleflight propagates errors to waiting requests."""
        async def failing_synthesize():
            raise ValueError("Synthesis failed")
        
        cache_key = voice_cache.generate_cache_key(
            "test text", "voice1", "mp3", voice_cache.generate_settings_hash()
        )
        
        async def request():
            return await voice_cache.get_or_synthesize(cache_key, failing_synthesize)
        
        # Run 3 concurrent requests
        with pytest.raises(ValueError, match="Synthesis failed"):
            await asyncio.gather(*[request() for _ in range(3)])
    
    @pytest.mark.unit
    def test_cache_statistics(self, voice_cache):
        """Test cache statistics tracking."""
        stats = voice_cache.get_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "errors" in stats
        assert "singleflight_hits" in stats
        assert "hit_rate" in stats
        assert "total_requests" in stats
        assert "in_flight_count" in stats
    
    @pytest.mark.unit
    def test_reset_stats(self, voice_cache):
        """Test statistics reset."""
        # Set some stats
        voice_cache.stats["hits"] = 10
        voice_cache.stats["misses"] = 5
        
        voice_cache.reset_stats()
        
        assert voice_cache.stats["hits"] == 0
        assert voice_cache.stats["misses"] == 0
        assert voice_cache.stats["errors"] == 0
        assert voice_cache.stats["singleflight_hits"] == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_disabled(self, voice_cache):
        """Test behavior when cache is disabled."""
        voice_cache.cache_enabled = False
        
        # Should return None even if we try to cache
        result = await voice_cache.get_cached_voice("test", "voice1", "mp3")
        assert result is None
        
        # Should not cache
        success = await voice_cache.cache_voice(
            text="test", voice_id="voice1", format="mp3",
            file_id="file1", duration=1.0
        )
        assert success is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_key_with_hash_helper(self, voice_cache):
        """Test _get_cache_key_with_hash helper method."""
        key1, hash1 = voice_cache._get_cache_key_with_hash("text", "voice", "mp3")
        key2, hash2 = voice_cache._get_cache_key_with_hash("text", "voice", "mp3")
        
        # Should be deterministic
        assert key1 == key2
        assert hash1 == hash2
        
        # Should generate hash if not provided
        key3, hash3 = voice_cache._get_cache_key_with_hash("text", "voice", "mp3", None)
        assert key3 == key1
        assert hash3 == hash1


class TestVoiceCacheServiceGlobal:
    """Tests for global voice cache service instance."""
    
    @pytest.mark.unit
    def test_get_voice_cache_service_singleton(self):
        """Test get_voice_cache_service returns singleton."""
        service1 = get_voice_cache_service()
        service2 = get_voice_cache_service()
        
        assert service1 is service2
        assert isinstance(service1, VoiceCacheService)

