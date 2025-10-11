import os
import mimetypes
from typing import List, Tuple, Optional, Dict, Any
from fastapi import HTTPException, UploadFile
from app.models.file_upload import FileType, FileValidationError
import logging

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

logger = logging.getLogger(__name__)

class FileValidator:
    """Utility class for validating uploaded files."""
    
    # File size limits (in bytes)
    MAX_FILE_SIZES = {
        FileType.AUDIO: 50 * 1024 * 1024,  # 50MB
        FileType.DOCUMENT: 10 * 1024 * 1024,  # 10MB
        FileType.IMAGE: 5 * 1024 * 1024,  # 5MB
    }
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        FileType.AUDIO: [
            "audio/mpeg",  # MP3
            "audio/wav",   # WAV
            "audio/mp4",   # M4A
            "audio/ogg",   # OGG
            "audio/flac",  # FLAC
            "audio/x-wav", # WAV variant
            "audio/wave",  # WAV variant
        ],
        FileType.DOCUMENT: [
            "application/pdf",  # PDF
            "application/msword",  # DOC
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
            "text/plain",  # TXT
            "application/rtf",  # RTF
        ],
        FileType.IMAGE: [
            "image/jpeg",  # JPG
            "image/jpg",   # JPG variant
            "image/png",   # PNG
            "image/gif",   # GIF
            "image/webp",  # WebP
        ],
    }
    
    # File extensions mapping
    ALLOWED_EXTENSIONS = {
        FileType.AUDIO: [".mp3", ".wav", ".m4a", ".ogg", ".flac"],
        FileType.DOCUMENT: [".pdf", ".doc", ".docx", ".txt", ".rtf"],
        FileType.IMAGE: [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    }
    
    @classmethod
    def validate_file_size(cls, file: UploadFile, file_type: FileType) -> None:
        """Validate file size against limits."""
        if not file.size:
            raise HTTPException(
                status_code=400,
                detail="File size could not be determined"
            )
        
        max_size = cls.MAX_FILE_SIZES.get(file_type)
        if not max_size:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown file type: {file_type}"
            )
        
        if file.size > max_size:
            size_mb = file.size / (1024 * 1024)
            max_size_mb = max_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size for {file_type.value} files is {max_size_mb:.1f}MB, got {size_mb:.1f}MB"
            )
    
    @classmethod
    def validate_file_type(cls, file: UploadFile, file_type: FileType) -> str:
        """Validate file type and return MIME type."""
        # Get MIME type from file
        mime_type = file.content_type
        
        # If content_type is not available, try to detect it
        if not mime_type:
            if MAGIC_AVAILABLE:
                try:
                    # Read first 1024 bytes for MIME type detection
                    file.file.seek(0)
                    header = file.file.read(1024)
                    file.file.seek(0)  # Reset file pointer
                    
                    mime_type = magic.from_buffer(header, mime=True)
                    logger.info(f"Detected MIME type: {mime_type}")
                except Exception as e:
                    logger.warning(f"Could not detect MIME type: {e}")
                    mime_type = "application/octet-stream"
            else:
                # Fallback to mimetypes module
                mime_type, _ = mimetypes.guess_type(file.filename or "")
                mime_type = mime_type or "application/octet-stream"
        
        # Validate MIME type
        allowed_types = cls.ALLOWED_MIME_TYPES.get(file_type, [])
        if mime_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Expected {file_type.value} file, got {mime_type}. Allowed types: {', '.join(allowed_types)}"
            )
        
        return mime_type
    
    @classmethod
    def validate_file_extension(cls, filename: str, file_type: FileType) -> None:
        """Validate file extension."""
        if not filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        # Get file extension
        _, ext = os.path.splitext(filename.lower())
        
        allowed_extensions = cls.ALLOWED_EXTENSIONS.get(file_type, [])
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension. Expected one of {', '.join(allowed_extensions)}, got {ext}"
            )
    
    @classmethod
    def validate_filename(cls, filename: str) -> str:
        """Validate and sanitize filename."""
        if not filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        # Remove path components
        filename = os.path.basename(filename)
        
        # Check for dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                raise HTTPException(
                    status_code=400,
                    detail=f"Filename contains invalid character: {char}"
                )
        
        # Check filename length
        if len(filename) > 255:
            raise HTTPException(
                status_code=400,
                detail="Filename too long. Maximum length is 255 characters"
            )
        
        # Check for empty filename after sanitization
        if not filename.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid filename"
            )
        
        return filename.strip()
    
    @classmethod
    def validate_file(cls, file: UploadFile, file_type: FileType) -> Tuple[str, str]:
        """
        Comprehensive file validation.
        Returns (filename, mime_type) if valid.
        """
        # Validate filename
        filename = cls.validate_filename(file.filename)
        
        # Validate file extension
        cls.validate_file_extension(filename, file_type)
        
        # Validate file size
        cls.validate_file_size(file, file_type)
        
        # Validate file type
        mime_type = cls.validate_file_type(file, file_type)
        
        return filename, mime_type
    
    @classmethod
    def get_file_type_from_mime(cls, mime_type: str) -> Optional[FileType]:
        """Determine file type from MIME type."""
        for file_type, allowed_mimes in cls.ALLOWED_MIME_TYPES.items():
            if mime_type in allowed_mimes:
                return file_type
        return None
    
    @classmethod
    def get_file_type_from_extension(cls, filename: str) -> Optional[FileType]:
        """Determine file type from file extension."""
        _, ext = os.path.splitext(filename.lower())
        
        for file_type, allowed_extensions in cls.ALLOWED_EXTENSIONS.items():
            if ext in allowed_extensions:
                return file_type
        return None
    
    @classmethod
    def is_safe_filename(cls, filename: str) -> bool:
        """Check if filename is safe (no path traversal, etc.)."""
        try:
            # Normalize path
            normalized = os.path.normpath(filename)
            
            # Check for path traversal
            if '..' in normalized or normalized.startswith('/'):
                return False
            
            # Check for dangerous characters
            dangerous_chars = ['\\', ':', '*', '?', '"', '<', '>', '|']
            for char in dangerous_chars:
                if char in filename:
                    return False
            
            return True
        except Exception:
            return False
    
    @classmethod
    def generate_safe_filename(cls, original_filename: str, file_id: str) -> str:
        """Generate a safe filename using file ID."""
        _, ext = os.path.splitext(original_filename)
        return f"{file_id}{ext}"
    
    @classmethod
    def get_file_validation_errors(cls, file: UploadFile, file_type: FileType) -> List[FileValidationError]:
        """Get detailed validation errors for a file."""
        errors = []
        
        try:
            cls.validate_file(file, file_type)
        except HTTPException as e:
            errors.append(FileValidationError(
                field="file",
                error=e.detail,
                value=file.filename
            ))
        
        return errors
