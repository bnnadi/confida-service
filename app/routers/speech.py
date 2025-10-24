from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from typing import List
from app.models.schemas import TranscribeResponse, SupportedFormatsResponse
from app.services.file_service import FileService
from app.middleware.auth_middleware import get_current_user_required
from app.services.database_service import get_db
from app.models.schemas import FileType
from app.utils.validation import ValidationService
from app.utils.logger import get_logger
from app.dependencies import get_ai_client_dependency

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])

def get_file_service(db = Depends(get_db)) -> FileService:
    return FileService(db)

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
                # Fallback to direct speech service
                logger.warning("AI service returned unexpected format, falling back to direct speech service")
                transcript = speech_service.transcribe_audio(audio_data, language)
            
            # Save file if requested
            if save_file:
                saved_file = file_service.save_file(
                    filename=filename,
                    content=audio_data,
                    file_type=FileType.AUDIO,
                    user_id=current_user["id"]
                )
                file_id = saved_file.id
            else:
                file_id = None
            
            return TranscribeResponse(
                transcript=transcript,
                language=language,
                filename=filename,
                file_id=file_id,
                confidence=result.get("confidence", 0.0) if isinstance(result, dict) else 0.0
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
    # Note: speech_service removed - using AI service microservice
    file_service: FileService = Depends(get_file_service)
):
    """
    Transcribe a previously uploaded audio file.
    """
    try:
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
        with open(file_info["file_path"], "rb") as f:
            audio_data = f.read()
        
        # Transcribe audio
        transcription = speech_service.transcribe_audio(audio_data, language)
        
        return TranscribeResponse(
            transcription=transcription,
            language=language,
            confidence=0.95,  # Placeholder confidence score
            file_id=file_id,
            metadata={
                "filename": file_info["filename"],
                "mime_type": file_info["mime_type"],
                "file_size": file_info["file_size"],
                "saved": True
            }
        )
        
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
