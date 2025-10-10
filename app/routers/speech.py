from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from typing import Optional
from pydub import AudioSegment
import io
import time
from app.models.schemas import TranscribeResponse, SupportedFormatsResponse
from app.services.speech_service import SpeechToTextService
from app.utils.endpoint_helpers import handle_service_errors
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["speech"])

# Initialize speech service
speech_service = SpeechToTextService()

# Supported audio formats
SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "ogg", "flac"]
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SUPPORTED_LANGUAGES = [
    "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", "it-IT", 
    "pt-BR", "ru-RU", "ja-JP", "ko-KR", "zh-CN", "ar-SA"
]

@router.post("/transcribe", response_model=TranscribeResponse)
@handle_service_errors("transcribing audio")
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="en-US", description="Language code for transcription"),
    format: str = Form(default="wav", description="Audio format")
):
    """
    Transcribe audio file to text using speech recognition.
    Supports multiple audio formats and languages.
    """
    # Validate file format
    if format.lower() not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Validate language
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Supported languages: {', '.join(SUPPORTED_LANGUAGES)}"
        )
    
    # Check file size
    if audio_file.size and audio_file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    try:
        # Read audio file
        audio_data = await audio_file.read()
        
        # Get audio duration
        audio = AudioSegment.from_file(io.BytesIO(audio_data))
        duration = len(audio) / 1000.0  # Convert to seconds
        
        # Transcribe audio
        start_time = time.time()
        transcript = speech_service.transcribe_audio(audio_data, language)
        processing_time = time.time() - start_time
        
        # Calculate confidence (simplified - in real implementation, this would come from the service)
        confidence = min(0.95, max(0.1, 1.0 - (processing_time / duration) if duration > 0 else 0.8))
        
        logger.info(f"Successfully transcribed audio: {len(transcript)} characters, {processing_time:.2f}s")
        
        return TranscribeResponse(
            transcript=transcript,
            confidence=confidence,
            language=language,
            duration=duration
        )
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )

@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """
    Get list of supported audio formats and configuration.
    """
    return SupportedFormatsResponse(
        formats=SUPPORTED_FORMATS,
        max_file_size=MAX_FILE_SIZE,
        supported_languages=SUPPORTED_LANGUAGES
    )
