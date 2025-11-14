"""
TTS (Text-to-Speech) Provider Abstraction

This module provides a unified interface for multiple TTS providers with:
- Provider abstraction layer
- Automatic fallback support
- Circuit breaker pattern
- Caching support
"""

from app.services.tts.base import (
    BaseTTSProvider,
    TTSProviderError,
    TTSProviderTimeoutError,
    TTSProviderRateLimitError
)
from app.services.tts.factory import (
    TTSProviderFactory,
    create_tts_provider
)
from app.services.tts.service import (
    TTSService,
    get_tts_service
)
from app.services.tts.coqui import CoquiTTSProvider
from app.services.tts.elevenlabs import ElevenLabsTTSProvider
from app.services.tts.playht import PlayHTTTSProvider

__all__ = [
    # Base classes
    "BaseTTSProvider",
    "TTSProviderError",
    "TTSProviderTimeoutError",
    "TTSProviderRateLimitError",
    
    # Factory
    "TTSProviderFactory",
    "create_tts_provider",
    
    # Service
    "TTSService",
    "get_tts_service",
    
    # Provider implementations
    "CoquiTTSProvider",
    "ElevenLabsTTSProvider",
    "PlayHTTTSProvider",
]

