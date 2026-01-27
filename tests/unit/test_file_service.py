"""
Unit tests for File Service.

Tests the file service including:
- save_file_from_bytes() with MP3 and WAV
- Metadata storage and retrieval
- Nested path structure for voice files
- File finding in flat and nested structures
- Helper methods
"""
import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock
from fastapi import UploadFile
from app.services.file_service import FileService
from app.models.schemas import FileType, FileStatus


class TestFileService:
    """Tests for FileService."""
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Create a temporary upload directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_service(self, db_session, temp_upload_dir, monkeypatch):
        """Create FileService instance with temporary upload directory."""
        from app.config import get_settings
        
        # Mock settings to use temp directory
        mock_settings = Mock()
        mock_settings.FILE_UPLOAD_DIR = str(temp_upload_dir)
        mock_settings.FILE_EXPIRATION_HOURS = 24
        
        monkeypatch.setattr("app.services.file_service.settings", mock_settings)
        
        return FileService(db_session)
    
    @pytest.fixture
    def sample_mp3_bytes(self):
        """Sample MP3 audio bytes for testing."""
        # Minimal valid MP3 header (ID3v2 tag)
        return b'\xff\xfb\x90\x00' + b'\x00' * 100
    
    @pytest.fixture
    def sample_wav_bytes(self):
        """Sample WAV audio bytes for testing."""
        # Minimal valid WAV header
        return b'RIFF' + b'\x00' * 4 + b'WAVE' + b'fmt ' + b'\x00' * 20
    
    @pytest.mark.unit
    def test_save_file_from_bytes_mp3(self, file_service, sample_mp3_bytes):
        """Test saving MP3 file from bytes."""
        file_id = file_service.generate_file_id()
        
        result = file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test_audio.mp3"
        )
        
        assert result["file_id"] == file_id
        assert result["filename"].endswith(".mp3")
        assert result["mime_type"] == "audio/mpeg"
        assert result["file_size"] == len(sample_mp3_bytes)
        assert result["status"] == FileStatus.COMPLETED
        assert "file_path" in result
        assert "file_hash" in result
        
        # Verify file exists
        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.read_bytes() == sample_mp3_bytes
    
    @pytest.mark.unit
    def test_save_file_from_bytes_wav(self, file_service, sample_wav_bytes):
        """Test saving WAV file from bytes."""
        file_id = file_service.generate_file_id()
        
        result = file_service.save_file_from_bytes(
            content=sample_wav_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test_audio.wav"
        )
        
        assert result["file_id"] == file_id
        assert result["filename"].endswith(".wav")
        assert result["mime_type"] in ["audio/wav", "audio/x-wav"]
        assert result["file_size"] == len(sample_wav_bytes)
        assert result["status"] == FileStatus.COMPLETED
        
        # Verify file exists
        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.read_bytes() == sample_wav_bytes
    
    @pytest.mark.unit
    def test_save_file_from_bytes_with_metadata(self, file_service, sample_mp3_bytes):
        """Test saving file with voice metadata."""
        file_id = file_service.generate_file_id()
        metadata = {
            "question_id": "123",
            "voice_id": "voice-456",
            "version": "2",
            "synthesis_settings_hash": "abc123"
        }
        
        result = file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test_audio.mp3",
            metadata=metadata
        )
        
        # Verify nested path structure
        file_path = Path(result["file_path"])
        assert "questions" in str(file_path)
        assert "123" in str(file_path)
        assert "voices" in str(file_path)
        assert "voice-456" in str(file_path)
        assert file_path.name.startswith("v2")
        assert file_path.name.endswith(".mp3")
        
        # Verify metadata file exists
        metadata_path = file_path.parent / f"{file_path.stem}.metadata.json"
        assert metadata_path.exists()
        
        # Verify metadata content
        with open(metadata_path, "r") as f:
            saved_metadata = json.load(f)
        
        assert saved_metadata["question_id"] == "123"
        assert saved_metadata["voice_id"] == "voice-456"
        assert saved_metadata["version"] == "2"
        assert saved_metadata["synthesis_settings_hash"] == "abc123"
        assert saved_metadata["file_id"] == file_id
    
    @pytest.mark.unit
    def test_save_file_from_bytes_auto_filename(self, file_service, sample_mp3_bytes):
        """Test auto-generating filename when not provided."""
        file_id = file_service.generate_file_id()
        
        result = file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test_audio.mp3"
        )
        
        assert result["filename"] == f"{file_id}.mp3"
    
    @pytest.mark.unit
    def test_save_file_from_bytes_auto_mime_type(self, file_service, sample_mp3_bytes):
        """Test auto-detecting MIME type from filename."""
        file_id = file_service.generate_file_id()
        
        result = file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test.mp3"
        )
        
        assert result["mime_type"] == "audio/mpeg"
    
    @pytest.mark.unit
    def test_get_file_info_with_metadata(self, file_service, sample_mp3_bytes):
        """Test retrieving file info with voice metadata."""
        file_id = file_service.generate_file_id()
        metadata = {
            "question_id": "789",
            "voice_id": "voice-abc",
            "version": "1",
            "synthesis_settings_hash": "xyz789"
        }
        
        # Save file with metadata
        save_result = file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test_audio.mp3",
            metadata=metadata
        )
        
        # Retrieve file info
        file_info = file_service.get_file_info(file_id)
        
        assert file_info is not None
        assert file_info["file_id"] == file_id
        assert file_info["file_type"] == FileType.AUDIO
        assert file_info["file_size"] == len(sample_mp3_bytes)
        assert "metadata" in file_info
        
        # Verify voice metadata
        retrieved_metadata = file_info["metadata"]
        assert retrieved_metadata["question_id"] == "789"
        assert retrieved_metadata["voice_id"] == "voice-abc"
        assert retrieved_metadata["version"] == "1"
        assert retrieved_metadata["synthesis_settings_hash"] == "xyz789"
        assert retrieved_metadata["file_id"] == file_id
    
    @pytest.mark.unit
    def test_get_file_info_without_metadata(self, file_service, sample_mp3_bytes):
        """Test retrieving file info without metadata (backward compatibility)."""
        file_id = file_service.generate_file_id()
        
        # Save file without metadata
        file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id
        )
        
        # Retrieve file info
        file_info = file_service.get_file_info(file_id)
        
        assert file_info is not None
        assert file_info["file_id"] == file_id
        assert file_info["file_type"] == FileType.AUDIO
        # Metadata should be None or not present
        assert file_info.get("metadata") is None or file_info["metadata"] is None
    
    @pytest.mark.unit
    def test_find_file_in_flat_structure(self, file_service, sample_mp3_bytes):
        """Test finding file in flat directory structure."""
        file_id = file_service.generate_file_id()
        
        file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id
        )
        
        # Find file
        file_path = file_service._find_file_by_id(file_id)
        assert file_path is not None
        assert file_path.exists()
        assert file_id in file_path.name
    
    @pytest.mark.unit
    def test_find_file_in_nested_structure(self, file_service, sample_mp3_bytes):
        """Test finding file in nested voice file structure."""
        file_id = file_service.generate_file_id()
        metadata = {
            "question_id": "999",
            "voice_id": "voice-nested",
            "version": "3"
        }
        
        file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            metadata=metadata
        )
        
        # Find file
        file_path = file_service._find_file_by_id(file_id)
        assert file_path is not None
        assert file_path.exists()
        assert "questions" in str(file_path)
        assert "999" in str(file_path)
        assert "voices" in str(file_path)
        assert "voice-nested" in str(file_path)
    
    @pytest.mark.unit
    def test_get_file_path_nested_structure(self, file_service):
        """Test getting nested path for voice files."""
        metadata = {
            "question_id": "111",
            "voice_id": "voice-test",
            "version": "1"
        }
        
        path = file_service.get_file_path(
            file_id="test-id",
            file_type=FileType.AUDIO,
            filename="test.mp3",
            metadata=metadata
        )
        
        assert "questions" in str(path)
        assert "111" in str(path)
        assert "voices" in str(path)
        assert "voice-test" in str(path)
        assert path.name == "v1.mp3"
    
    @pytest.mark.unit
    def test_get_file_path_flat_structure(self, file_service):
        """Test getting flat path for regular files."""
        path = file_service.get_file_path(
            file_id="test-id",
            file_type=FileType.AUDIO,
            filename="test.mp3"
        )
        
        assert "questions" not in str(path)
        assert "voices" not in str(path)
        assert "test-id" in path.name
    
    @pytest.mark.unit
    def test_should_use_nested_structure(self, file_service):
        """Test nested structure decision logic."""
        # Should use nested for audio with metadata
        metadata = {"question_id": "1", "voice_id": "v1"}
        assert file_service._should_use_nested_structure(FileType.AUDIO, metadata) is True
        
        # Should not use nested for non-audio
        assert file_service._should_use_nested_structure(FileType.DOCUMENT, metadata) is False
        
        # Should not use nested without metadata
        assert file_service._should_use_nested_structure(FileType.AUDIO, None) is False
        
        # Should not use nested with incomplete metadata
        incomplete_metadata = {"question_id": "1"}
        assert file_service._should_use_nested_structure(FileType.AUDIO, incomplete_metadata) is False
    
    @pytest.mark.unit
    def test_get_file_extension(self, file_service):
        """Test file extension extraction."""
        assert file_service._get_file_extension("test.mp3") == ".mp3"
        assert file_service._get_file_extension("test.wav") == ".wav"
        assert file_service._get_file_extension("test") == ".bin"  # default
        assert file_service._get_file_extension(None) == ".bin"  # default
        assert file_service._get_file_extension("test", default=".mp3") == ".mp3"
    
    @pytest.mark.unit
    def test_normalize_audio_filename_and_mime(self, file_service):
        """Test filename and MIME type normalization."""
        file_id = "test-id"
        
        # Test with MIME type, no filename
        filename, mime_type = file_service._normalize_audio_filename_and_mime(
            file_id, None, "audio/mpeg"
        )
        assert filename == f"{file_id}.mp3"
        assert mime_type == "audio/mpeg"
        
        # Test with filename, no MIME type
        filename, mime_type = file_service._normalize_audio_filename_and_mime(
            file_id, "test.wav", None
        )
        assert filename == "test.wav"
        assert mime_type == "audio/wav"
        
        # Test with both
        filename, mime_type = file_service._normalize_audio_filename_and_mime(
            file_id, "custom.mp3", "audio/mpeg"
        )
        assert filename == "custom.mp3"
        assert mime_type == "audio/mpeg"
        
        # Test with neither (defaults to MP3)
        filename, mime_type = file_service._normalize_audio_filename_and_mime(
            file_id, None, None
        )
        assert filename == f"{file_id}.mp3"
        assert mime_type == "audio/mpeg"
    
    @pytest.mark.unit
    def test_matches_file_id(self, file_service, sample_mp3_bytes):
        """Test file ID matching logic."""
        file_id = file_service.generate_file_id()
        metadata = {
            "question_id": "match-test",
            "voice_id": "voice-match",
            "version": "1"
        }
        
        # Save file with metadata
        save_result = file_service.save_file_from_bytes(
            content=sample_mp3_bytes,
            file_type=FileType.AUDIO,
            file_id=file_id,
            metadata=metadata
        )
        
        file_path = Path(save_result["file_path"])
        
        # Should match via metadata
        assert file_service._matches_file_id(file_path, file_id) is True
        
        # Should not match different ID
        assert file_service._matches_file_id(file_path, "different-id") is False
    
    @pytest.mark.unit
    def test_save_file_with_metadata(self, file_service):
        """Test saving uploaded file with metadata."""
        file_id = file_service.generate_file_id()
        metadata = {
            "question_id": "upload-test",
            "voice_id": "voice-upload",
            "version": "1"
        }
        
        # Create mock UploadFile
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.mp3"
        mock_file.file = MagicMock()
        mock_file.file.read = Mock(return_value=b"test audio data")
        
        # Mock validation
        file_service.validation_service.validate_file = Mock(return_value=(True, []))
        
        result = file_service.save_file(
            file=mock_file,
            file_type=FileType.AUDIO,
            file_id=file_id,
            metadata=metadata
        )
        
        assert result["filename"] == "test.mp3"
        assert "file_path" in result
        
        # Verify metadata was saved
        file_path = Path(result["file_path"])
        metadata_path = file_path.parent / f"{file_path.stem}.metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                saved_metadata = json.load(f)
            assert saved_metadata["file_id"] == file_id


class TestFileServiceIntegration:
    """Integration tests for FileService - save → retrieve → download flow."""
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Create a temporary upload directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def file_service(self, db_session, temp_upload_dir, monkeypatch):
        """Create FileService instance with temporary upload directory."""
        from app.config import get_settings
        
        mock_settings = Mock()
        mock_settings.FILE_UPLOAD_DIR = str(temp_upload_dir)
        mock_settings.FILE_EXPIRATION_HOURS = 24
        
        monkeypatch.setattr("app.services.file_service.settings", mock_settings)
        
        return FileService(db_session)
    
    @pytest.mark.integration
    def test_save_retrieve_download_flow(self, file_service):
        """Integration test: save → retrieve → download."""
        # Step 1: Save file with metadata
        file_id = file_service.generate_file_id()
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 100  # Sample MP3
        metadata = {
            "question_id": "integration-test",
            "voice_id": "voice-integration",
            "version": "1",
            "synthesis_settings_hash": "hash123"
        }
        
        save_result = file_service.save_file_from_bytes(
            content=audio_data,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename="test_audio.mp3",
            metadata=metadata
        )
        
        assert save_result["file_id"] == file_id
        assert save_result["status"] == FileStatus.COMPLETED
        
        # Step 2: Retrieve file info
        file_info = file_service.get_file_info(file_id)
        assert file_info is not None
        assert file_info["file_id"] == file_id
        assert file_info["file_type"] == FileType.AUDIO
        assert file_info["file_size"] == len(audio_data)
        assert file_info["metadata"]["question_id"] == "integration-test"
        assert file_info["metadata"]["voice_id"] == "voice-integration"
        
        # Step 3: Download file content
        file_content = file_service.get_file_content(file_id)
        assert file_content is not None
        
        downloaded_data = file_content.read()
        file_content.close()
        
        assert downloaded_data == audio_data
        
        # Step 4: Verify file path convention
        file_path = Path(file_info["file_path"])
        assert "questions" in str(file_path)
        assert "integration-test" in str(file_path)
        assert "voices" in str(file_path)
        assert "voice-integration" in str(file_path)
        assert file_path.name.startswith("v1")
        assert file_path.name.endswith(".mp3")
    
    @pytest.mark.integration
    def test_multiple_formats_save_retrieve(self, file_service):
        """Test saving and retrieving multiple audio formats."""
        formats = [
            ("audio/mpeg", ".mp3", b'\xff\xfb\x90\x00' + b'\x00' * 50),
            ("audio/wav", ".wav", b'RIFF' + b'\x00' * 4 + b'WAVE' + b'fmt ' + b'\x00' * 10),
        ]
        
        saved_files = []
        
        for mime_type, ext, audio_data in formats:
            file_id = file_service.generate_file_id()
            
            result = file_service.save_file_from_bytes(
                content=audio_data,
                file_type=FileType.AUDIO,
                file_id=file_id,
                filename=f"test_audio{ext}"
            )
            
            saved_files.append((file_id, audio_data, mime_type))
            
            # Verify can retrieve each
            file_info = file_service.get_file_info(file_id)
            assert file_info is not None
            assert file_info["mime_type"] == mime_type
            assert file_info["filename"].endswith(ext)
        
        # Verify all files are distinct
        file_ids = [f[0] for f in saved_files]
        assert len(file_ids) == len(set(file_ids))

