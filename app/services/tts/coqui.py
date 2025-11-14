"""
Coqui TTS Provider

Local, open-source TTS solution that runs on the server.
No API keys required - completely free and privacy-friendly.
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
from app.services.tts.base import (
    BaseTTSProvider,
    TTSProviderError,
    TTSProviderTimeoutError
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CoquiTTSProvider(BaseTTSProvider):
    """
    Coqui TTS provider implementation.
    
    This provider uses the Coqui TTS library for local text-to-speech synthesis.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Coqui TTS provider.
        
        Args:
            config: Configuration dictionary with:
                - base_url: Coqui TTS service URL (default: http://localhost:5002)
                - timeout: Request timeout in seconds (default: 30)
                - voice_id: Default voice ID (default: confida-default-en)
                - voice_version: Voice model version (default: 1)
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:5002")
        self.timeout = config.get("timeout", 30)
        self.default_voice_id = config.get("voice_id", "confida-default-en")
        self.voice_version = config.get("voice_version", 1)
        self.supported_formats = ["mp3", "wav", "ogg"]
        
        # Update config with supported formats
        self.config["supported_formats"] = self.supported_formats
        
        logger.info(f"Coqui TTS provider initialized: {self.base_url}")
    
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        format: str = "mp3",
        **kwargs
    ) -> bytes:
        """
        Synthesize text to speech using Coqui TTS.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice identifier (uses default if not provided)
            format: Audio format (mp3, wav, ogg)
            **kwargs: Additional parameters (ignored for Coqui)
            
        Returns:
            bytes: Audio data in the specified format
            
        Raises:
            TTSProviderError: If synthesis fails
            TTSProviderTimeoutError: If request times out
        """
        if not self.validate_text(text):
            raise TTSProviderError("Invalid text input")
        
        if not self.validate_format(format):
            raise TTSProviderError(f"Unsupported audio format: {format}")
        
        voice = voice_id or self.default_voice_id
        
        try:
            logger.debug(f"Synthesizing text with Coqui TTS (voice: {voice}, format: {format})")
            
            # Prepare request payload
            payload = {
                "text": text,
                "voice_id": voice,
                "voice_version": self.voice_version,
                "format": format
            }
            
            # Make request to Coqui TTS service
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/synthesize",
                    json=payload
                )
                
                if response.status_code == 200:
                    audio_data = response.content
                    logger.info(f"Successfully synthesized {len(audio_data)} bytes of audio")
                    return audio_data
                elif response.status_code == 408 or response.status_code == 504:
                    raise TTSProviderTimeoutError(
                        f"Coqui TTS request timed out: {response.status_code}"
                    )
                else:
                    error_msg = f"Coqui TTS synthesis failed: {response.status_code}"
                    try:
                        error_detail = response.json().get("detail", "")
                        if error_detail:
                            error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                    raise TTSProviderError(error_msg)
                    
        except httpx.TimeoutException:
            raise TTSProviderTimeoutError("Coqui TTS request timed out")
        except httpx.RequestError as e:
            raise TTSProviderError(f"Coqui TTS request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in Coqui TTS synthesis: {e}")
            raise TTSProviderError(f"Coqui TTS synthesis failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Coqui TTS service is healthy.
        
        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    logger.debug("Coqui TTS service is healthy")
                    return True
                else:
                    logger.warning(f"Coqui TTS health check failed: {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"Coqui TTS health check error: {e}")
            return False

