"""
ElevenLabs TTS Provider

Premium cloud-based TTS service with high-quality, natural-sounding voices.
Requires API key for authentication.
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


class ElevenLabsTTSProvider(BaseTTSProvider):
    """
    ElevenLabs TTS provider implementation.
    
    This provider uses the ElevenLabs API for cloud-based text-to-speech synthesis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ElevenLabs TTS provider.
        
        Args:
            config: Configuration dictionary with:
                - api_key: ElevenLabs API key (required)
                - base_url: ElevenLabs API base URL (default: https://api.elevenlabs.io/v1)
                - timeout: Request timeout in seconds (default: 30)
                - voice_id: Default voice ID (default: confida-default-en)
                - model_id: Model identifier (optional)
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise TTSProviderError("ElevenLabs API key is required")
        
        self.base_url = config.get("base_url", "https://api.elevenlabs.io/v1")
        self.timeout = config.get("timeout", 30)
        self.default_voice_id = config.get("voice_id", "confida-default-en")
        self.model_id = config.get("model_id", "eleven_monolingual_v1")
        self.supported_formats = ["mp3", "wav", "m4a", "aac"]
        
        # Update config with supported formats
        self.config["supported_formats"] = self.supported_formats
        
        logger.info("ElevenLabs TTS provider initialized")
    
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
        **kwargs
    ) -> bytes:
        """
        Synthesize text to speech using ElevenLabs API.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice identifier (uses default if not provided)
            format: Audio format (mp3, wav, m4a, aac)
            **kwargs: Additional parameters:
                - stability: Voice stability (0.0-1.0)
                - similarity_boost: Similarity boost (0.0-1.0)
                - style: Style setting (0.0-1.0)
                - use_speaker_boost: Enable speaker boost (bool)
                
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
            logger.debug(f"Synthesizing text with ElevenLabs (voice: {voice}, format: {format})")
            
            # Prepare request payload
            payload = {
                "text": text,
                "model_id": kwargs.get("model_id", self.model_id),
                "voice_settings": {
                    "stability": kwargs.get("stability", 0.5),
                    "similarity_boost": kwargs.get("similarity_boost", 0.75),
                    "style": kwargs.get("style", 0.0),
                    "use_speaker_boost": kwargs.get("use_speaker_boost", True)
                }
            }
            
            # Map format to ElevenLabs output format
            output_format_map = {
                "mp3": "mp3_44100_128",
                "wav": "pcm_44100",
                "m4a": "mp3_44100_192",
                "aac": "mp3_44100_128"
            }
            output_format = output_format_map.get(format.lower(), "mp3_44100_128")
            
            # Make request to ElevenLabs API
            headers = {
                "Accept": "audio/mpeg",
                "xi-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice}",
                    json=payload,
                    headers=headers,
                    params={"output_format": output_format}
                )
                
                if response.status_code == 200:
                    audio_data = response.content
                    logger.info(f"Successfully synthesized {len(audio_data)} bytes of audio")
                    return audio_data
                elif response.status_code == 401:
                    raise TTSProviderError("ElevenLabs API key is invalid")
                elif response.status_code == 429:
                    raise TTSProviderRateLimitError("ElevenLabs rate limit exceeded")
                elif response.status_code == 408 or response.status_code == 504:
                    raise TTSProviderTimeoutError(
                        f"ElevenLabs request timed out: {response.status_code}"
                    )
                else:
                    error_msg = f"ElevenLabs synthesis failed: {response.status_code}"
                    try:
                        error_detail = response.json().get("detail", {}).get("message", "")
                        if error_detail:
                            error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    raise TTSProviderError(error_msg)
                    
        except httpx.TimeoutException:
            raise TTSProviderTimeoutError("ElevenLabs request timed out")
        except TTSProviderRateLimitError:
            raise
        except httpx.RequestError as e:
            raise TTSProviderError(f"ElevenLabs request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in ElevenLabs synthesis: {e}")
            raise TTSProviderError(f"ElevenLabs synthesis failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if ElevenLabs API is accessible.
        
        Returns:
            bool: True if API is accessible, False otherwise
        """
        try:
            headers = {
                "xi-api-key": self.api_key
            }
            async with httpx.AsyncClient(timeout=5) as client:
                # Check user info endpoint as health check
                response = await client.get(
                    f"{self.base_url}/user",
                    headers=headers
                )
                if response.status_code == 200:
                    logger.debug("ElevenLabs API is accessible")
                    return True
                else:
                    logger.warning(f"ElevenLabs health check failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"ElevenLabs health check error: {e}")
            return False

