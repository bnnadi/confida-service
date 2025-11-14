"""
Base TTS Provider Interface

This module defines the abstract base class that all TTS providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TTSProviderError(Exception):
    """Base exception for TTS provider errors."""
    pass


class TTSProviderTimeoutError(TTSProviderError):
    """Raised when TTS provider request times out."""
    pass


class TTSProviderRateLimitError(TTSProviderError):
    """Raised when TTS provider rate limit is exceeded."""
    pass


class BaseTTSProvider(ABC):
    """
    Abstract base class for all TTS providers.
    
    All TTS providers must implement the synthesize method to convert text to speech audio.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the TTS provider.
        
        Args:
            config: Configuration dictionary containing provider-specific settings
        """
        self.config = config
        self.provider_name = self.__class__.__name__
        logger.debug(f"Initialized {self.provider_name} TTS provider")
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
        **kwargs
    ) -> bytes:
        """
        Synthesize text to speech audio.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice identifier (uses default if not provided)
            format: Audio format (mp3, wav, ogg, m4a, aac)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            bytes: Audio data in the specified format
            
        Raises:
            TTSProviderError: If synthesis fails
            TTSProviderTimeoutError: If request times out
            TTSProviderRateLimitError: If rate limit is exceeded
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the TTS provider is healthy and available.
        
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        return self.provider_name
    
    def validate_text(self, text: str) -> bool:
        """
        Validate text input.
        
        Args:
            text: Text to validate
            
        Returns:
            bool: True if text is valid
        """
        if not text or not isinstance(text, str):
            return False
        if len(text.strip()) == 0:
            return False
        # Maximum text length (can be overridden by providers)
        max_length = self.config.get("max_text_length", 5000)
        if len(text) > max_length:
            logger.warning(f"Text length {len(text)} exceeds maximum {max_length}")
            return False
        return True
    
    def validate_format(self, format: str) -> bool:
        """
        Validate audio format.
        
        Args:
            format: Audio format to validate
            
        Returns:
            bool: True if format is supported
        """
        supported_formats = self.config.get("supported_formats", ["mp3", "wav", "ogg", "m4a", "aac"])
        return format.lower() in [f.lower() for f in supported_formats]

