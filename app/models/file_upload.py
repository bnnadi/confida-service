from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class FileType(str, Enum):
    """Supported file types for upload."""
    AUDIO = "audio"
    DOCUMENT = "document"
    IMAGE = "image"

class FileStatus(str, Enum):
    """File processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"

class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    file_type: FileType = Field(..., description="Type of file being uploaded")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the file")
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty if provided')
        return v.strip() if v else None

class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: str = Field(..., description="Unique identifier for the uploaded file")
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    status: FileStatus = Field(..., description="Current processing status")
    upload_url: str = Field(..., description="URL to access the uploaded file")
    created_at: datetime = Field(..., description="Upload timestamp")
    expires_at: Optional[datetime] = Field(None, description="File expiration timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional file metadata")

class FileInfoResponse(BaseModel):
    """Response model for file information."""
    file_id: str = Field(..., description="Unique identifier for the file")
    filename: str = Field(..., description="Original filename")
    file_type: FileType = Field(..., description="Type of file")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of the file")
    status: FileStatus = Field(..., description="Current processing status")
    upload_url: str = Field(..., description="URL to access the file")
    created_at: datetime = Field(..., description="Upload timestamp")
    expires_at: Optional[datetime] = Field(None, description="File expiration timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional file metadata")
    processing_result: Optional[Dict[str, Any]] = Field(None, description="Result of file processing")

class FileListResponse(BaseModel):
    """Response model for file list."""
    files: List[FileInfoResponse] = Field(..., description="List of files")
    total_count: int = Field(..., description="Total number of files")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of files per page")
    has_next: bool = Field(..., description="Whether there are more files")

class FileDeleteResponse(BaseModel):
    """Response model for file deletion."""
    file_id: str = Field(..., description="ID of the deleted file")
    message: str = Field(..., description="Deletion confirmation message")
    deleted_at: datetime = Field(..., description="Deletion timestamp")

class FileValidationError(BaseModel):
    """Model for file validation errors."""
    field: str = Field(..., description="Field that failed validation")
    error: str = Field(..., description="Error message")
    value: Optional[str] = Field(None, description="Value that caused the error")

class FileUploadError(BaseModel):
    """Model for file upload errors."""
    file_id: Optional[str] = Field(None, description="File ID if available")
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")
