from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database.connection import get_db
from app.services.file_service import FileService
from app.models.schemas import (
    FileType, FileUploadRequest, FileUploadResponse, FileInfoResponse, 
    FileListResponse, FileDeleteResponse, FileValidationError, FileValidationErrorResponse
)
from app.middleware.auth_middleware import get_current_user_required
from app.utils.unified_validation_service import UnifiedValidationService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["files"])

def get_file_service(db: Session = Depends(get_db)) -> FileService:
    """Dependency to get file service."""
    return FileService(db)

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="File to upload"),
    file_type: FileType = Query(..., description="Type of file being uploaded"),
    description: Optional[str] = Query(None, description="Optional description of the file"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """
    Upload a file to the server.
    
    Supports audio files (MP3, WAV, M4A, OGG, FLAC), documents (PDF, DOC, DOCX), 
    and images (JPG, PNG, GIF, WebP).
    """
    try:
        # Generate unique file ID
        file_id = file_service.generate_file_id()
        
        # Save file to storage
        file_info = file_service.save_file(file, file_type, file_id)
        
        # Create response
        response = FileUploadResponse(
            file_id=file_id,
            filename=file_info["filename"],
            file_type=file_type,
            file_size=file_info["file_size"],
            mime_type=file_info["mime_type"],
            status=file_info["status"],
            upload_url=f"/api/v1/files/{file_id}",
            created_at=file_info.get("created_at"),
            expires_at=None,
            metadata={
                "description": description,
                "uploaded_by": current_user["id"],
                "file_hash": file_info["file_hash"]
            }
        )
        
        logger.info(f"File uploaded successfully: {file_id} by user {current_user['id']}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )

@router.get("/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
    file_id: str,
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Get information about a specific file."""
    file_info = file_service.get_file_info(file_id)
    
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return FileInfoResponse(
        file_id=file_info["file_id"],
        filename=file_info["filename"],
        file_type=file_info["file_type"],
        file_size=file_info["file_size"],
        mime_type=file_info["mime_type"],
        status=file_info["status"],
        upload_url=f"/api/v1/files/{file_id}",
        created_at=file_info["created_at"],
        expires_at=None,
        metadata=file_info.get("metadata"),
        processing_result=file_info.get("processing_result")
    )

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Download a file."""
    file_info = file_service.get_file_info(file_id)
    
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_path = file_info["file_path"]
    filename = file_info["filename"]
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=file_info["mime_type"]
    )

@router.get("/", response_model=FileListResponse)
async def list_files(
    file_type: Optional[FileType] = Query(None, description="Filter by file type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of files per page"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """List files with pagination and optional filtering."""
    return file_service.list_files(file_type=file_type, page=page, page_size=page_size)

@router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Delete a file."""
    # Check if file exists
    file_info = file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Delete file
    success = file_service.delete_file(file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file"
        )
    
    logger.info(f"File deleted successfully: {file_id} by user {current_user['id']}")
    
    return FileDeleteResponse(
        file_id=file_id,
        message="File deleted successfully",
        deleted_at=file_info["created_at"]  # Using created_at as deleted_at for simplicity
    )

@router.post("/validate", response_model=List[FileValidationErrorResponse])
async def validate_file(
    file: UploadFile = File(..., description="File to validate"),
    file_type: FileType = Query(..., description="Type of file being validated"),
    current_user: dict = Depends(get_current_user_required)
):
    """Validate a file without uploading it."""
    try:
        # Validate file using unified validation service
        validation_service = UnifiedValidationService()
        is_valid, errors = validation_service.validate_file(file, file_type)
        
        if is_valid:
            return []
        else:
            return [FileValidationError(
                message=f"File validation failed: {', '.join(errors)}"
            )]
        
    except HTTPException as e:
        # Return validation error
        return [FileValidationError(
            message=e.detail
        )]

@router.get("/stats/storage")
async def get_storage_stats(
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Get storage statistics."""
    stats = file_service.get_storage_stats()
    return {
        "storage_stats": stats,
        "user_id": current_user["id"]
    }

@router.post("/cleanup")
async def cleanup_expired_files(
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Clean up expired files."""
    cleaned_count = file_service.cleanup_expired_files()
    
    logger.info(f"Cleaned up {cleaned_count} expired files by user {current_user['id']}")
    
    return {
        "message": f"Cleaned up {cleaned_count} expired files",
        "cleaned_count": cleaned_count
    }

# Audio-specific endpoints
@router.post("/audio/upload", response_model=FileUploadResponse)
async def upload_audio_file(
    file: UploadFile = File(..., description="Audio file to upload"),
    description: Optional[str] = Query(None, description="Optional description of the audio file"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Upload an audio file specifically for speech-to-text processing."""
    return await upload_file(
        file=file,
        file_type=FileType.AUDIO,
        description=description,
        current_user=current_user,
        file_service=file_service
    )

@router.get("/audio/", response_model=FileListResponse)
async def list_audio_files(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of files per page"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """List audio files."""
    return await list_files(
        file_type=FileType.AUDIO,
        page=page,
        page_size=page_size,
        current_user=current_user,
        file_service=file_service
    )

# Document-specific endpoints
@router.post("/documents/upload", response_model=FileUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="Document to upload"),
    description: Optional[str] = Query(None, description="Optional description of the document"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Upload a document file (PDF, DOC, DOCX, etc.)."""
    return await upload_file(
        file=file,
        file_type=FileType.DOCUMENT,
        description=description,
        current_user=current_user,
        file_service=file_service
    )

@router.get("/documents/", response_model=FileListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of files per page"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """List document files."""
    return await list_files(
        file_type=FileType.DOCUMENT,
        page=page,
        page_size=page_size,
        current_user=current_user,
        file_service=file_service
    )

# Image-specific endpoints
@router.post("/images/upload", response_model=FileUploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="Image to upload"),
    description: Optional[str] = Query(None, description="Optional description of the image"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """Upload an image file (JPG, PNG, GIF, WebP)."""
    return await upload_file(
        file=file,
        file_type=FileType.IMAGE,
        description=description,
        current_user=current_user,
        file_service=file_service
    )

@router.get("/images/", response_model=FileListResponse)
async def list_images(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of files per page"),
    current_user: dict = Depends(get_current_user_required),
    file_service: FileService = Depends(get_file_service)
):
    """List image files."""
    return await list_files(
        file_type=FileType.IMAGE,
        page=page,
        page_size=page_size,
        current_user=current_user,
        file_service=file_service
    )
