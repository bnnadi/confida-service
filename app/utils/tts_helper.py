"""
TTS Helper Utility for Voice Synthesis Integration

This module provides a helper interface for TTS services, with graceful
degradation when TTS services are not available.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from app.utils.logger import get_logger
from app.config import get_settings

# Conditional imports (only if services exist)
try:
    from app.services.tts.service import TTSService
    from app.services.voice_cache import VoiceCacheService
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

logger = get_logger(__name__)
settings = get_settings()


def _generate_settings_hash(voice_id: str, format: str, version: int) -> str:
    """Generate deterministic settings hash for cache key."""
    settings_dict = {"voice_id": voice_id, "format": format, "version": version}
    return hashlib.sha256(
        json.dumps(settings_dict, sort_keys=True).encode()
    ).hexdigest()


def _read_cached_audio_file(file_id: str) -> Optional[bytes]:
    """Read audio file from storage by file_id. Returns None if not found."""
    from app.services.file_service import FileService
    from app.services.database_service import get_db
    
    db = next(get_db())
    try:
        file_service = FileService(db)
        file_info = file_service.get_file_info(file_id)
        if not file_info:
            return None
        
        file_path = Path(file_info.get("file_path", ""))
        if not file_path.exists():
            return None
        
        with open(file_path, "rb") as f:
            return f.read()
    finally:
        db.close()


async def synthesize_voice(
    text: str,
    voice_id: str,
    format: str = "mp3",
    question_id: Optional[str] = None
) -> Optional[Tuple[bytes, float, Dict[str, Any]]]:
    """
    Synthesize voice audio for given text.
    
    Returns:
        Tuple of (audio_bytes, duration_seconds, metadata) or None if synthesis fails
    """
    if not TTS_AVAILABLE:
        logger.warning("TTS services not available. Voice synthesis disabled.")
        return None
    
    try:
        tts_service = TTSService()
        voice_cache = VoiceCacheService()
        
        # Check cache first
        settings_hash = _generate_settings_hash(
            voice_id, format, settings.TTS_VOICE_VERSION
        )
        cached_result = await voice_cache.get_cached_voice(
            text=text, voice_id=voice_id, format=format, settings_hash=settings_hash
        )
        
        if cached_result and cached_result.get("file_id"):
            logger.info(f"Voice cache hit for question {question_id}")
            audio_bytes = _read_cached_audio_file(cached_result["file_id"])
            if audio_bytes:
                return (
                    audio_bytes,
                    cached_result.get("duration", 0.0),
                    {
                        "file_id": cached_result["file_id"],
                        "cached": True,
                        "voice_id": voice_id,
                        "version": cached_result.get("version", 1)
                    }
                )
        
        # Cache miss - synthesize
        logger.info(f"Synthesizing voice for question {question_id} (cache miss)")
        audio_bytes, duration, metadata = await tts_service.synthesize(
            text=text, voice_id=voice_id, format=format
        )
        
        return (audio_bytes, duration, {
            **metadata,
            "cached": False,
            "voice_id": voice_id,
            "version": settings.TTS_VOICE_VERSION
        })
        
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return None


async def cache_voice_result(
    text: str,
    voice_id: str,
    format: str,
    file_id: str,
    duration: float,
    question_id: Optional[str] = None,
    version: int = 1
) -> bool:
    """Cache voice synthesis result."""
    if not TTS_AVAILABLE:
        logger.warning("Voice cache service not available")
        return False
    
    try:
        voice_cache = VoiceCacheService()
        settings_hash = _generate_settings_hash(voice_id, format, version)
        
        await voice_cache.cache_voice(
            text=text, voice_id=voice_id, format=format,
            settings_hash=settings_hash, file_id=file_id,
            duration=duration, question_id=question_id, version=version
        )
        return True
    except Exception as e:
        logger.error(f"Failed to cache voice result: {e}")
        return False


async def synthesize_and_save_voice(
    question_text: str,
    question_id: str,
    voice_id: str,
    audio_format: str,
    file_service: Any,
    settings: Any
) -> Optional[Any]:
    """
    Synthesize voice, save file, cache result, and return payload.
    Returns None on failure (graceful degradation).
    """
    from app.models.schemas import VoicePayload, VoiceFile
    from app.models.schemas import FileType
    
    try:
        # Synthesize voice
        synthesis_result = await synthesize_voice(
            text=question_text,
            voice_id=voice_id,
            format=audio_format,
            question_id=question_id
        )
        
        if not synthesis_result:
            return None
        
        audio_bytes, duration, metadata = synthesis_result
        version = metadata.get("version", settings.TTS_VOICE_VERSION)
        
        # Save file
        from app.services.file_service import FileService
        file_id = FileService.generate_file_id()
        filename = f"question_{question_id}_voice.{audio_format}"
        
        file_service.save_file_from_bytes(
            content=audio_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename=filename,
            metadata={
                "question_id": question_id,
                "voice_id": voice_id,
                "version": version,
                "format": audio_format
            }
        )
        
        # Cache if not already cached
        if not metadata.get("cached", False):
            await cache_voice_result(
                text=question_text,
                voice_id=voice_id,
                format=audio_format,
                file_id=file_id,
                duration=duration,
                question_id=question_id,
                version=version
            )
        
        # Build and return payload
        mime_type = "audio/mpeg" if audio_format == "mp3" else "audio/wav"
        return VoicePayload(
            voice_id=voice_id,
            version=version,
            duration=duration,
            files=[VoiceFile(
                file_id=file_id,
                mime_type=mime_type,
                download_url=f"/api/v1/files/{file_id}/download"
            )]
        )
        
    except Exception as e:
        logger.error(f"Error synthesizing voice for question {question_id}: {e}")
        return None

