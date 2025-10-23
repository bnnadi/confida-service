# os import removed as it was unused
import uuid
import shutil
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from app.models.schemas import FileType, FileStatus, FileInfoResponse, FileListResponse
from app.utils.unified_validation_service import UnifiedValidationService
from app.config import get_settings
from app.utils.logger import get_logger
# lru_cache import removed as it was unused

logger = get_logger(__name__)
settings = get_settings()

class FileService:
    """Service for handling file uploads, storage, and management with modern pathlib operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.FILE_UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different file types using pathlib
        self._create_type_directories()
        
        # Initialize unified validation service
        self.validation_service = UnifiedValidationService()
    
    def _create_type_directories(self):
        """Create subdirectories for different file types using pathlib."""
        for file_type in [FileType.IMAGE, FileType.DOCUMENT, FileType.AUDIO]:
            type_dir = self.upload_dir / file_type.value
            type_dir.mkdir(exist_ok=True)
    
    def _generate_safe_filename(self, filename: str, file_id: str) -> str:
        """Generate a safe filename for storage."""
        if not filename:
            return f"{file_id}.bin"
        
        # Get file extension
        file_ext = Path(filename).suffix
        if not file_ext:
            file_ext = ".bin"
        
        # Create safe filename with file_id prefix
        safe_name = f"{file_id}_{filename.replace(' ', '_').replace('/', '_')}"
        return safe_name
    
    def _get_mime_type_from_filename(self, filename: str) -> str:
        """Get MIME type from filename."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
    
    @staticmethod
    def generate_file_id() -> str:
        """Generate a unique file ID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def calculate_file_hash(file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()
    
    def get_file_path(self, file_id: str, file_type: FileType, filename: str) -> Path:
        """Get the full file path for a given file using pathlib operations."""
        safe_filename = self._generate_safe_filename(filename, file_id)
        return self.upload_dir / file_type.value / safe_filename
    
    
    def save_file(self, file: UploadFile, file_type: FileType, file_id: str) -> Dict[str, Any]:
        """Save uploaded file to disk."""
        try:
            # Validate file
            is_valid, errors = self.validation_service.validate_file(file, file_type)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"File validation failed: {', '.join(errors)}")
            filename = file.filename
            mime_type = self._get_mime_type_from_filename(filename)
            
            # Get file path
            file_path = self.get_file_path(file_id, file_type, filename)
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save file to disk
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Calculate file hash
            with open(file_path, "rb") as f:
                file_hash = self.calculate_file_hash(f.read())
            
            # Get file size
            file_size = file_path.stat().st_size
            
            return {
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "file_hash": file_hash,
                "file_path": str(file_path),
                "status": FileStatus.COMPLETED
            }
            
        except Exception as e:
            logger.error(f"Error saving file {file_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )
    
    def _find_file_by_id(self, file_id: str) -> Optional[Path]:
        """Find file by ID across all type directories."""
        for file_type in [FileType.IMAGE, FileType.DOCUMENT, FileType.AUDIO]:
            type_dir = self.upload_dir / file_type.value
            if type_dir.exists():
                for file_path in type_dir.glob(f"{file_id}*"):
                    if file_path.is_file():
                        return file_path
        return None

    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from storage."""
        file_path = self._find_file_by_id(file_id)
        if not file_path:
            return None
        
        stat = file_path.stat()
        return {
            "file_id": file_id,
            "filename": file_path.name,
            "file_type": self._get_file_type_from_path(file_path),
            "file_size": stat.st_size,
            "mime_type": self._get_mime_type(file_path),
            "file_path": str(file_path),
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "status": FileStatus.COMPLETED
        }
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file path."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from storage."""
        try:
            file_path = self._find_file_by_id(file_id)
            if file_path:
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {e}")
            return False
    
    def list_files(self, file_type: Optional[FileType] = None, page: int = 1, page_size: int = 20) -> FileListResponse:
        """List files with pagination."""
        files = []
        total_count = 0
        
        # Determine which directories to scan
        dirs_to_scan = []
        if file_type:
            dirs_to_scan = [self.upload_dir / file_type.value]
        else:
            dirs_to_scan = [self.upload_dir / ft.value for ft in FileType]
        
        # Scan directories for files
        for dir_path in dirs_to_scan:
            if dir_path.exists():
                for file_path in dir_path.glob("*"):
                    if file_path.is_file():
                        total_count += 1
                        
                        # Get file info
                        stat = file_path.stat()
                        file_info = {
                            "file_id": file_path.stem,  # Assuming filename is file_id + extension
                            "filename": file_path.name,
                            "file_type": file_type or self._get_file_type_from_path(file_path),
                            "file_size": stat.st_size,
                            "mime_type": self._get_mime_type(file_path),
                            "file_path": str(file_path),
                            "created_at": datetime.fromtimestamp(stat.st_ctime),
                            "status": FileStatus.COMPLETED
                        }
                        files.append(file_info)
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_files = files[start_idx:end_idx]
        
        # Convert to response models
        file_responses = [
            FileInfoResponse(
                file_id=f["file_id"],
                filename=f["filename"],
                file_type=f["file_type"],
                file_size=f["file_size"],
                mime_type=f["mime_type"],
                status=f["status"],
                upload_url=f"/api/v1/files/{f['file_id']}",
                created_at=f["created_at"],
                expires_at=None,
                metadata=None,
                processing_result=None
            )
            for f in paginated_files
        ]
        
        return FileListResponse(
            files=file_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=end_idx < total_count
        )
    
    def _get_file_type_from_path(self, file_path: Path) -> FileType:
        """Determine file type from file path."""
        for file_type in FileType:
            if file_type.value in str(file_path):
                return file_type
        return FileType.DOCUMENT  # Default fallback
    
    def get_file_content(self, file_id: str) -> Optional[BinaryIO]:
        """Get file content as binary stream."""
        file_info = self.get_file_info(file_id)
        if not file_info:
            return None
        
        file_path = Path(file_info["file_path"])
        if not file_path.exists():
            return None
        
        return open(file_path, "rb")
    
    def cleanup_expired_files(self) -> int:
        """Clean up expired files. Returns number of files cleaned up."""
        cleaned_count = 0
        current_time = datetime.now()
        
        for file_type in FileType:
            type_dir = self.upload_dir / file_type.value
            if type_dir.exists():
                for file_path in type_dir.glob("*"):
                    if file_path.is_file():
                        # Check if file is older than expiration time
                        file_age = current_time - datetime.fromtimestamp(file_path.stat().st_ctime)
                        if file_age > timedelta(hours=settings.FILE_EXPIRATION_HOURS):
                            try:
                                file_path.unlink()
                                cleaned_count += 1
                                logger.info(f"Cleaned up expired file: {file_path}")
                            except Exception as e:
                                logger.error(f"Error cleaning up file {file_path}: {e}")
        
        return cleaned_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "total_files": 0,
            "total_size": 0,
            "files_by_type": {},
            "oldest_file": None,
            "newest_file": None
        }
        
        all_files = []
        
        for file_type in FileType:
            type_dir = self.upload_dir / file_type.value
            if type_dir.exists():
                type_files = []
                for file_path in type_dir.glob("*"):
                    if file_path.is_file():
                        stat = file_path.stat()
                        file_info = {
                            "file_type": file_type,
                            "size": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_ctime)
                        }
                        type_files.append(file_info)
                        all_files.append(file_info)
                
                stats["files_by_type"][file_type.value] = {
                    "count": len(type_files),
                    "total_size": sum(f["size"] for f in type_files)
                }
        
        stats["total_files"] = len(all_files)
        stats["total_size"] = sum(f["size"] for f in all_files)
        
        if all_files:
            all_files.sort(key=lambda x: x["created_at"])
            stats["oldest_file"] = all_files[0]["created_at"]
            stats["newest_file"] = all_files[-1]["created_at"]
        
        return stats


class FileOperationFactory:
    """Factory for file operations with type-specific handling."""
    
    def __init__(self):
        self.operations = {
            FileType.AUDIO: self._handle_audio_file,
            FileType.VIDEO: self._handle_video_file,
            FileType.DOCUMENT: self._handle_document_file,
            FileType.IMAGE: self._handle_image_file
        }
    
    def process_file(self, file_type: FileType, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Process file based on type using factory pattern."""
        handler = self.operations.get(file_type, self._handle_generic_file)
        return handler(file_path, **kwargs)
    
    def _handle_audio_file(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Handle audio file operations."""
        return {
            "type": "audio",
            "operations": ["transcribe", "analyze_quality", "extract_metadata"],
            "path": str(file_path)
        }
    
    def _handle_video_file(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Handle video file operations."""
        return {
            "type": "video",
            "operations": ["extract_audio", "analyze_frames", "compress"],
            "path": str(file_path)
        }
    
    def _handle_document_file(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Handle document file operations."""
        return {
            "type": "document",
            "operations": ["extract_text", "convert_format", "validate"],
            "path": str(file_path)
        }
    
    def _handle_image_file(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Handle image file operations."""
        return {
            "type": "image",
            "operations": ["resize", "optimize", "extract_metadata"],
            "path": str(file_path)
        }
    
    def _handle_generic_file(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Handle generic file operations."""
        return {
            "type": "generic",
            "operations": ["validate", "store", "hash"],
            "path": str(file_path)
        }
