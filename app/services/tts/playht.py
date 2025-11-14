"""
PlayHT TTS Provider

Cloud-based TTS service with enterprise features and multiple voice options.
Requires API key and User ID for authentication.
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
from app.services.tts.base import (
    BaseTTSProvider,
    TTSProviderError,
    TTSProviderTimeoutError,
    TTSProviderRateLimitError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlayHTTTSProvider(BaseTTSProvider):
    """
    PlayHT TTS provider implementation.
    
    This provider uses the PlayHT API for cloud-based text-to-speech synthesis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PlayHT TTS provider.
        
        Args:
            config: Configuration dictionary with:
                - api_key: PlayHT API key (required)
                - user_id: PlayHT User ID (required)
                - base_url: PlayHT API base URL (default: https://api.play.ht/api/v1)
                - timeout: Request timeout in seconds (default: 30)
                - voice_id: Default voice ID (default: confida-default-en)
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.user_id = config.get("user_id")
        
        if not self.api_key:
            raise TTSProviderError("PlayHT API key is required")
        if not self.user_id:
            raise TTSProviderError("PlayHT User ID is required")
        
        self.base_url = config.get("base_url", "https://api.play.ht/api/v1")
        self.timeout = config.get("timeout", 30)
        self.default_voice_id = config.get("voice_id", "confida-default-en")
        self.supported_formats = ["mp3", "wav", "ogg", "m4a", "aac"]
        
        # Update config with supported formats
        self.config["supported_formats"] = self.supported_formats
        
        logger.info("PlayHT TTS provider initialized")
    
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
        **kwargs
    ) -> bytes:
        """
        Synthesize text to speech using PlayHT API.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice identifier (uses default if not provided)
            format: Audio format (mp3, wav, ogg, m4a, aac)
            **kwargs: Additional parameters:
                - output_format: Output format override
                - sample_rate: Sample rate (22050, 24000, 44100)
                - speed: Speech speed (0.5-2.0)
                
        Returns:
            bytes: Audio data in the specified format
            
        Raises:
            TTSProviderError: If synthesis fails
            TTSProviderTimeoutError: If request times out
            TTSProviderRateLimitError: If rate limit is exceeded
        """
        if not self.validate_text(text):
            raise TTSProviderError("Invalid text input")
        
        if not self.validate_format(format):
            raise TTSProviderError(f"Unsupported audio format: {format}")
        
        voice = voice_id or self.default_voice_id
        
        try:
            logger.debug(f"Synthesizing text with PlayHT (voice: {voice}, format: {format})")
            
            # Prepare request payload
            payload = {
                "text": text,
                "voice": voice,
                "output_format": format,
                "sample_rate": kwargs.get("sample_rate", 24000),
                "speed": kwargs.get("speed", 1.0)
            }
            
            # Make request to PlayHT API
            headers = {
                "AUTHORIZATION": f"Bearer {self.api_key}",
                "X-USER-ID": self.user_id,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/tts",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    audio_data = response.content
                    logger.info(f"Successfully synthesized {len(audio_data)} bytes of audio")
                    return audio_data
                elif response.status_code == 401:
                    raise TTSProviderError("PlayHT API key or User ID is invalid")
                elif response.status_code == 429:
                    raise TTSProviderRateLimitError("PlayHT rate limit exceeded")
                elif response.status_code == 408 or response.status_code == 504:
                    raise TTSProviderTimeoutError(
                        f"PlayHT request timed out: {response.status_code}"
                    )
                else:
                    error_msg = f"PlayHT synthesis failed: {response.status_code}"
                    try:
                        error_detail = response.json().get("error_message", "")
                        if error_detail:
                            error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    raise TTSProviderError(error_msg)
                    
        except httpx.TimeoutException:
            raise TTSProviderTimeoutError("PlayHT request timed out")
        except TTSProviderRateLimitError:
            raise
        except httpx.RequestError as e:
            raise TTSProviderError(f"PlayHT request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in PlayHT synthesis: {e}")
            raise TTSProviderError(f"PlayHT synthesis failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if PlayHT API is accessible.
        
        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:
            headers = {
                "AUTHORIZATION": f"Bearer {self.api_key}",
                "X-USER-ID": self.user_id
            }
            async with httpx.AsyncClient(timeout=5) as client:
                # Check voices endpoint as health check
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers=headers
                )
                if response.status_code == 200:
                    logger.debug("PlayHT API is accessible")
                    return True
                else:
                    logger.warning(f"PlayHT health check failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"PlayHT health check error: {e}")
            return False

