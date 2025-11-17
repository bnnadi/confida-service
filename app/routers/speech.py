from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from typing import List, Optional
from io import BytesIO
import wave
from datetime import datetime

from app.models.schemas import (
    TranscribeResponse,
    SupportedFormatsResponse,
    SynthesizeRequest,
    SynthesizeResponse,
)
from app.services.file_service import FileService
from app.middleware.auth_middleware import get_current_user_required, get_current_admin
from app.services.database_service import get_db
from app.models.schemas import FileType
from app.utils.validation import ValidationService
from app.utils.logger import get_logger
from app.dependencies import get_ai_client_dependency
from app.services.tts.service import TTSService
from app.services.tts.base import TTSProviderError, TTSProviderRateLimitError
from app.services.voice_cache import VoiceCacheService
from app.middleware.rate_limiter import RateLimiter
from app.exceptions import RateLimitExceededError
from app.utils.tts_helper import cache_voice_result
from app.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

def get_file_service(db = Depends(get_db)) -> FileService:
    return FileService(db)

admin_tts_rate_limiter = RateLimiter(max_requests=10, window_seconds=3600)

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio_endpoint(
    audio_file: UploadFile = File(..., description="Audio file to transcribe (MP3, WAV, M4A, OGG, FLAC)"),
    language: str = Query("en-US", description="Language code for transcription (e.g., en-US, es-ES)"),
    save_file: bool = Query(False, description="Whether to save the uploaded file for future reference"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service),
    ai_client = Depends(get_ai_client_dependency)
):
    """
    Transcribe audio file to text using AI service microservice.
    
    Supports multiple audio formats and can optionally save the file for future reference.
    """
    try:
        # Validate audio file using validation service
        validation_service = ValidationService()
        is_valid, errors = validation_service.validate_file(audio_file, FileType.AUDIO)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {', '.join(errors)}"
            )
        
        if not ai_client:
            raise HTTPException(status_code=503, detail="AI service unavailable")
        
        filename = audio_file.filename
        mime_type = "audio/wav"  # Default for speech recognition
        
        # Read audio data
        audio_data = await audio_file.read()
        
        # Save file temporarily for AI service
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Use AI service microservice for transcription
            session_id = f"transcription_{current_user['id']}_{filename}"
            result = await ai_client.transcribe_audio(
                audio_file_path=temp_file_path,
                session_id=session_id,
                language=language
            )
            
            # Extract transcription from result
            if isinstance(result, dict) and "transcript" in result:
                transcript = result["transcript"]
            elif isinstance(result, dict) and "text" in result:
                transcript = result["text"]
            else:
                # Fallback - return error if AI service format is unexpected
                logger.error("AI service returned unexpected format")
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response format from AI service"
                )
            
            # Save file if requested
            if save_file:
                file_id = file_service.generate_file_id()
                saved_file_info = file_service.save_file_from_bytes(
                    audio_data=audio_data,
                    file_type=FileType.AUDIO,
                    file_id=file_id,
                    filename=filename,
                    mime_type=mime_type,
                    metadata={
                        "uploaded_by": current_user["id"],
                        "description": f"Transcribed audio: {filename}"
                    }
                )
            else:
                file_id = None
            
            return TranscribeResponse(
                transcription=transcript,
                language=language,
                confidence=result.get("confidence", 0.0) if isinstance(result, dict) else 0.0,
                file_id=file_id,
                metadata={
                    "filename": filename
                }
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio: {str(e)}"
        )

@router.post("/transcribe/{file_id}", response_model=TranscribeResponse)
async def transcribe_saved_audio(
    file_id: str,
    language: str = Query("en-US", description="Language code for transcription"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service),
    ai_client = Depends(get_ai_client_dependency)
):
    """
    Transcribe a previously uploaded audio file.
    """
    try:
        if not ai_client:
            raise HTTPException(status_code=503, detail="AI service unavailable")
        
        # Get file info
        file_info = file_service.get_file_info(file_id)
        if not file_info:
            raise HTTPException(
                status_code=404,
                detail="Audio file not found"
            )
        
        # Check if it's an audio file
        if file_info["file_type"] != FileType.AUDIO:
            raise HTTPException(
                status_code=400,
                detail="File is not an audio file"
            )
        
        # Read audio data from saved file
        import tempfile
        import os
        with open(file_info["file_path"], "rb") as f:
            audio_data = f.read()
        
        # Save file temporarily for AI service
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Use AI service microservice for transcription
            session_id = f"transcription_{current_user['id']}_{file_id}"
            result = await ai_client.transcribe_audio(
                audio_file_path=temp_file_path,
                session_id=session_id,
                language=language
            )
            
            # Extract transcription from result
            if isinstance(result, dict) and "transcript" in result:
                transcript = result["transcript"]
            elif isinstance(result, dict) and "text" in result:
                transcript = result["text"]
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Unexpected response format from AI service"
                )
            
            return TranscribeResponse(
                transcription=transcript,
                language=language,
                confidence=result.get("confidence", 0.95) if isinstance(result, dict) else 0.95,
                file_id=file_id,
                metadata={
                    "filename": file_info["filename"],
                    "mime_type": file_info.get("mime_type"),
                    "file_size": file_info["file_size"],
                    "saved": True
                }
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing saved audio file {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio file: {str(e)}"
        )

@router.get("/supported-formats", response_model=SupportedFormatsResponse)
async def get_supported_formats():
    """
    Get list of supported audio formats for transcription.
    """
    return SupportedFormatsResponse(
        formats=[
            {
                "format": "MP3",
                "mime_type": "audio/mpeg",
                "extension": ".mp3",
                "max_size": "50MB"
            },
            {
                "format": "WAV",
                "mime_type": "audio/wav",
                "extension": ".wav",
                "max_size": "50MB"
            },
            {
                "format": "M4A",
                "mime_type": "audio/mp4",
                "extension": ".m4a",
                "max_size": "50MB"
            },
            {
                "format": "OGG",
                "mime_type": "audio/ogg",
                "extension": ".ogg",
                "max_size": "50MB"
            },
            {
                "format": "FLAC",
                "mime_type": "audio/flac",
                "extension": ".flac",
                "max_size": "50MB"
            }
        ],
        supported_languages=[
            "en-US", "en-GB", "es-ES", "fr-FR", "de-DE", 
            "it-IT", "pt-BR", "ru-RU", "ja-JP", "ko-KR"
        ]
    )

@router.get("/audio-files", response_model=List[dict])
async def list_audio_files(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of files per page"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """
    List uploaded audio files for transcription.
    """
    file_list = file_service.list_files(
        file_type=FileType.AUDIO,
        page=page,
        page_size=page_size
    )
    
    # Convert to simplified format for speech interface
    audio_files = []
    for file_info in file_list.files:
        audio_files.append({
            "file_id": file_info.file_id,
            "filename": file_info.filename,
            "file_size": file_info.file_size,
            "created_at": file_info.created_at,
            "status": file_info.status.value
        })
    
    return audio_files

def _calculate_audio_duration(audio_bytes: Optional[bytes], audio_format: str) -> float:
    """Best-effort duration estimate for synthesized audio."""
    if not audio_bytes:
        return 0.0
    audio_format = audio_format.lower()
    if audio_format == "wav":
        try:
            with wave.open(BytesIO(audio_bytes)) as wav_file:
                frames = wav_file.getnframes()
                framerate = wav_file.getframerate()
                if framerate:
                    return round(frames / float(framerate), 2)
        except Exception:
            return 0.0
    return 0.0


@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(
    request: SynthesizeRequest,
    current_user: dict = Depends(get_current_admin),
    file_service: FileService = Depends(get_file_service)
):
    """
    Synthesize text to speech (Admin Tooling Endpoint).
    
    This endpoint allows administrators to synthesize text to speech using the TTS service.
    Requires admin authentication.
    """
    voice_id_used = request.voice_id or settings.TTS_DEFAULT_VOICE_ID
    audio_format_used = (request.audio_format or settings.TTS_DEFAULT_FORMAT).lower()
    if audio_format_used not in {"mp3", "wav"}:
        raise HTTPException(status_code=422, detail="audio_format must be 'mp3' or 'wav'")
    
    client_id = f"admin-tts:{current_user.get('id', 'unknown')}"
    try:
        admin_tts_rate_limiter.check_rate_limit(client_id)
    except RateLimitExceededError:
        raise HTTPException(
            status_code=429,
            detail="Admin TTS endpoint is limited to 10 requests per hour."
        )
    
    mime_type = "audio/mpeg" if audio_format_used == "mp3" else "audio/wav"
    file_id: Optional[str] = None
    cached = False
    duration = 0.0
    file_size = None
    
    voice_cache = VoiceCacheService()
    settings_hash = voice_cache.generate_settings_hash()
    
    cached_voice = await voice_cache.get_cached_voice(
        text=request.text,
        voice_id=voice_id_used,
        format=audio_format_used,
        settings_hash=settings_hash
    )
    
    if cached_voice and cached_voice.get("file_id"):
        cached = True
        file_id = cached_voice["file_id"]
        duration = cached_voice.get("duration", 0.0)
        file_info = file_service.get_file_info(file_id)
        if file_info:
            mime_type = file_info.get("mime_type", mime_type)
            file_size = file_info.get("file_size")
        else:
            # Cached metadata exists but file missing - treat as cache miss
            cached = False
            file_id = None
    
    audio_bytes: Optional[bytes] = None
    if not file_id:
        try:
            tts_service = TTSService()
            audio_bytes = await tts_service.synthesize(
                text=request.text,
                voice_id=voice_id_used,
                audio_format=audio_format_used,
                use_cache=request.use_cache
            )
        except TTSProviderRateLimitError as e:
            logger.warning(f"TTS rate limit exceeded: {e}")
            raise HTTPException(
                status_code=429,
                detail=f"TTS service rate limit exceeded: {str(e)}"
            )
        except TTSProviderError as e:
            logger.error(f"TTS provider error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"TTS service error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to synthesize speech: {str(e)}"
            )
        
        file_id = FileService.generate_file_id()
        filename = f"admin_tts_{file_id}.{audio_format_used}"
        metadata = {
            "voice_id": voice_id_used,
            "format": audio_format_used,
            "version": settings.TTS_VOICE_VERSION,
            "usage": "admin_synthesize",
            "generated_by": current_user.get("id"),
            "generated_at": datetime.utcnow().isoformat()
        }
        saved_file = file_service.save_file_from_bytes(
            content=audio_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename=filename,
            metadata=metadata
        )
        mime_type = saved_file.get("mime_type", mime_type)
        file_size = saved_file.get("file_size")
        duration = _calculate_audio_duration(audio_bytes, audio_format_used)
        
        await cache_voice_result(
            text=request.text,
            voice_id=voice_id_used,
            format=audio_format_used,
            file_id=file_id,
            duration=duration,
            question_id=None,
            version=settings.TTS_VOICE_VERSION
        )
    
    download_url = f"/api/v1/files/{file_id}/download"
    
    response_metadata = {
        "audio_size_bytes": file_size,
        "synthesized_by": current_user.get("id"),
        "synthesized_by_email": current_user.get("email"),
    }
    
    return SynthesizeResponse(
        file_id=file_id,
        voice_id=voice_id_used,
        audio_format=audio_format_used,
        mime_type=mime_type,
        duration=duration,
        download_url=download_url,
        text_length=len(request.text),
        cached=cached,
        metadata=response_metadata
    )
