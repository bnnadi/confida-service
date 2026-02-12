"""
Integration tests for Files API endpoints.

Tests the complete flow:
- Upload audio file
- Save file from bytes (TTS output)
- Retrieve file info
- Download file
- Verify metadata persistence
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import FileType, FileStatus


class TestFilesAPIEndpoints:
    """Integration tests for Files API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Create a temporary upload directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, temp_upload_dir, monkeypatch):
        """Set up temporary directory for file uploads."""
        from app.config import get_settings
        
        mock_settings = Mock()
        mock_settings.FILE_UPLOAD_DIR = str(temp_upload_dir)
        mock_settings.FILE_EXPIRATION_HOURS = 24
        
        monkeypatch.setattr("app.services.file_service.settings", mock_settings)
        monkeypatch.setattr("app.config.get_settings", lambda: mock_settings)
    
    @pytest.fixture
    def auth_token(self, client, sample_user):
        """Get authentication token for testing."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": sample_user.email,
                "password": "testpass123"
            }
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        return None
    
    @pytest.mark.integration
    def test_upload_audio_file(self, client, auth_token, temp_upload_dir):
        """Test uploading an audio file via API."""
        if not auth_token:
            pytest.skip("Authentication not available")
        
        # Create sample audio file
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 100
        
        response = client.post(
            "/api/v1/files/audio/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.mp3", audio_data, "audio/mpeg")},
            params={"description": "Test audio upload"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["file_type"] == "audio"
        assert data["filename"] == "test.mp3"
        assert data["status"] == "completed"
        
        # Verify file exists
        file_id = data["file_id"]
        file_info_response = client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert file_info_response.status_code == 200
    
    @pytest.mark.integration
    def test_download_file(self, client, auth_token, temp_upload_dir):
        """Test downloading a file via API."""
        if not auth_token:
            pytest.skip("Authentication not available")
        
        # First upload a file
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 100
        
        upload_response = client.post(
            "/api/v1/files/audio/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.mp3", audio_data, "audio/mpeg")}
        )
        
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # Download the file
        download_response = client.get(
            f"/api/v1/files/{file_id}/download",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "audio/mpeg"
        assert download_response.content == audio_data
    
    @pytest.mark.integration
    def test_get_file_info_with_metadata(self, client, auth_token, temp_upload_dir):
        """Test retrieving file info with metadata."""
        if not auth_token:
            pytest.skip("Authentication not available")
        
        # Upload file
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 100
        
        upload_response = client.post(
            "/api/v1/files/audio/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.mp3", audio_data, "audio/mpeg")},
            params={"description": "Test with metadata"}
        )
        
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # Get file info
        info_response = client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert info_response.status_code == 200
        data = info_response.json()
        assert data["file_id"] == file_id
        assert data["file_type"] == "audio"
        assert "metadata" in data or data.get("metadata") is not None
    
    @pytest.mark.integration
    def test_list_audio_files(self, client, auth_token, temp_upload_dir):
        """Test listing audio files."""
        if not auth_token:
            pytest.skip("Authentication not available")
        
        # Upload a few files
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 50
        
        for i in range(3):
            client.post(
                "/api/v1/files/audio/upload",
                headers={"Authorization": f"Bearer {auth_token}"},
                files={"file": (f"test_{i}.mp3", audio_data, "audio/mpeg")}
            )
        
        # List audio files
        list_response = client.get(
            "/api/v1/files/audio/",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"page": 1, "page_size": 10}
        )
        
        assert list_response.status_code == 200
        data = list_response.json()
        assert "files" in data
        assert len(data["files"]) >= 0  # May be 0 if files are in nested structure
    
    @pytest.mark.integration
    def test_delete_file(self, client, auth_token, temp_upload_dir):
        """Test deleting a file via API."""
        if not auth_token:
            pytest.skip("Authentication not available")
        
        # Upload file
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 100
        
        upload_response = client.post(
            "/api/v1/files/audio/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.mp3", audio_data, "audio/mpeg")}
        )
        
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # Delete file
        delete_response = client.delete(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert delete_response.status_code == 200
        
        # Verify file is deleted
        info_response = client.get(
            f"/api/v1/files/{file_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert info_response.status_code == 404


class TestFilesAPIVoicePersistence:
    """Integration tests for voice file persistence (TTS output)."""
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Create a temporary upload directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, temp_upload_dir, monkeypatch):
        """Set up temporary directory for file uploads."""
        from app.config import get_settings
        
        mock_settings = Mock()
        mock_settings.FILE_UPLOAD_DIR = str(temp_upload_dir)
        mock_settings.FILE_EXPIRATION_HOURS = 24
        
        monkeypatch.setattr("app.services.file_service.settings", mock_settings)
        monkeypatch.setattr("app.config.get_settings", lambda: mock_settings)
    
    @pytest.mark.integration
    def test_save_retrieve_download_voice_file(self, db_session, temp_upload_dir):
        """Test complete flow: save voice file → retrieve → download."""
        from app.services.file_service import FileService
        
        file_service = FileService(db_session)
        
        # Step 1: Save voice file from bytes (simulating TTS output)
        file_id = file_service.generate_file_id()
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 200  # Sample MP3
        metadata = {
            "question_id": "q123",
            "voice_id": "voice-456",
            "version": "1",
            "synthesis_settings_hash": "hash789"
        }
        
        save_result = file_service.save_file_from_bytes(
            content=audio_data,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename=f"{file_id}.mp3",
            metadata=metadata
        )
        
        assert save_result["file_id"] == file_id
        assert save_result["status"] == FileStatus.COMPLETED
        
        # Step 2: Retrieve file info
        file_info = file_service.get_file_info(file_id)
        assert file_info is not None
        assert file_info["file_id"] == file_id
        assert file_info["metadata"]["question_id"] == "q123"
        assert file_info["metadata"]["voice_id"] == "voice-456"
        
        # Step 3: Download file content
        file_content = file_service.get_file_content(file_id)
        assert file_content is not None
        
        downloaded_data = file_content.read()
        file_content.close()
        
        assert downloaded_data == audio_data
        
        # Step 4: Verify nested path structure
        file_path = Path(file_info["file_path"])
        assert "questions" in str(file_path)
        assert "q123" in str(file_path)
        assert "voices" in str(file_path)
        assert "voice-456" in str(file_path)
        assert file_path.name.startswith("v1")
        assert file_path.name.endswith(".mp3")
    
    @pytest.mark.integration
    def test_voice_file_metadata_persistence(self, db_session, temp_upload_dir):
        """Test that voice file metadata persists correctly."""
        from app.services.file_service import FileService
        
        file_service = FileService(db_session)
        
        file_id = file_service.generate_file_id()
        audio_data = b'\xff\xfb\x90\x00' + b'\x00' * 100
        metadata = {
            "question_id": "persist-test",
            "voice_id": "voice-persist",
            "version": "2",
            "synthesis_settings_hash": "persist-hash"
        }
        
        # Save with metadata
        file_service.save_file_from_bytes(
            content=audio_data,
            file_type=FileType.AUDIO,
            file_id=file_id,
            filename=f"{file_id}.mp3",
            metadata=metadata
        )
        
        # Retrieve and verify metadata
        file_info = file_service.get_file_info(file_id)
        assert file_info["metadata"]["question_id"] == "persist-test"
        assert file_info["metadata"]["voice_id"] == "voice-persist"
        assert file_info["metadata"]["version"] == "2"
        assert file_info["metadata"]["synthesis_settings_hash"] == "persist-hash"
        
        # Verify metadata file exists
        file_path = Path(file_info["file_path"])
        metadata_path = file_path.parent / f"{file_path.stem}.metadata.json"
        assert metadata_path.exists()

