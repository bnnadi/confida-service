"""
TTS Provider Factory

Factory for creating and managing TTS provider instances.
"""

from typing import Dict, Any, Optional
from app.services.tts.base import BaseTTSProvider, TTSProviderError
from app.services.tts.coqui import CoquiTTSProvider
from app.services.tts.elevenlabs import ElevenLabsTTSProvider
from app.services.tts.playht import PlayHTTTSProvider
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Provider registry
PROVIDER_REGISTRY = {
    "coqui": CoquiTTSProvider,
    "elevenlabs": ElevenLabsTTSProvider,
    "playht": PlayHTTTSProvider
}


class TTSProviderFactory:
    """
    Factory for creating TTS provider instances.
    """
    PROVIDER_REGISTRY = PROVIDER_REGISTRY  # Class attribute for test access
    
    @staticmethod
    def create_provider(
        provider_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseTTSProvider:
        """
        Create a TTS provider instance.
        
        Args:
            provider_name: Name of the provider (coqui, elevenlabs, playht)
            config: Optional configuration dictionary. If not provided, uses settings from config
            
        Returns:
            BaseTTSProvider: Provider instance
            
        Raises:
            TTSProviderError: If provider name is invalid or creation fails
        """
        provider_name = provider_name.lower()
        
        if provider_name not in PROVIDER_REGISTRY:
            raise TTSProviderError(
                f"Unknown TTS provider: {provider_name}. "
                f"Valid providers: {', '.join(PROVIDER_REGISTRY.keys())}"
            )
        
        # Use provided config or build from settings
        if config is None:
            config = TTSProviderFactory._build_config_from_settings(provider_name)
        
        try:
            provider_class = PROVIDER_REGISTRY[provider_name]
            provider = provider_class(config)
            logger.info(f"Created {provider_name} TTS provider")
            return provider
        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {e}")
            raise TTSProviderError(f"Failed to create {provider_name} provider: {str(e)}")
    
    @staticmethod
    def _build_config_from_settings(provider_name: str) -> Dict[str, Any]:
        """
        Build provider configuration from application settings.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        settings = get_settings()
        
        base_config = {
            "timeout": settings.TTS_TIMEOUT,
            "voice_id": settings.TTS_DEFAULT_VOICE_ID,
            "voice_version": settings.TTS_VOICE_VERSION,
            "max_text_length": 5000,  # Default max text length
        }
        
        if provider_name == "coqui":
            # Coqui-specific config
            base_config.update({
                "base_url": "http://localhost:5002",  # Default Coqui service URL
            })
        elif provider_name == "elevenlabs":
            # ElevenLabs-specific config
            if not settings.ELEVENLABS_API_KEY:
                raise TTSProviderError("ELEVENLABS_API_KEY is required for ElevenLabs provider")
            base_config.update({
                "api_key": settings.ELEVENLABS_API_KEY,
                "base_url": "https://api.elevenlabs.io/v1",
            })
        elif provider_name == "playht":
            # PlayHT-specific config
            if not settings.PLAYHT_API_KEY:
                raise TTSProviderError("PLAYHT_API_KEY is required for PlayHT provider")
            if not settings.PLAYHT_USER_ID:
                raise TTSProviderError("PLAYHT_USER_ID is required for PlayHT provider")
            base_config.update({
                "api_key": settings.PLAYHT_API_KEY,
                "user_id": settings.PLAYHT_USER_ID,
                "base_url": "https://api.play.ht/api/v1",
            })
        
        return base_config
    
    @staticmethod
    def get_available_providers() -> list:
        """
        Get list of available provider names.
        
        Returns:
            list: List of provider names
        """
        return list(PROVIDER_REGISTRY.keys())
    
    @staticmethod
    def is_provider_available(provider_name: str) -> bool:
        """
        Check if a provider is available.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            bool: True if provider is available, False otherwise
        """
        return provider_name.lower() in PROVIDER_REGISTRY


def create_tts_provider(
    provider_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> BaseTTSProvider:
    """
    Convenience function to create a TTS provider.
    
    Args:
        provider_name: Name of the provider (uses default from settings if not provided)
        config: Optional configuration dictionary
        
    Returns:
        BaseTTSProvider: Provider instance
    """
    if provider_name is None:
        settings = get_settings()
        provider_name = settings.TTS_PROVIDER
    
    return TTSProviderFactory.create_provider(provider_name, config)

