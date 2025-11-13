"""
Integration tests for WebSocket endpoints.

Tests WebSocket connection, message handling, and real-time feedback.
"""
import pytest
import json
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app


class TestWebSocketEndpoints:
    """Test cases for WebSocket endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication."""
        return {
            "id": 1,
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True
        }
    
    @pytest.fixture
    def mock_auth(self, mock_user):
        """Mock authentication."""
        with patch('app.routers.websocket.authenticate_websocket', new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = mock_user
            yield mock_auth
    
    @pytest.mark.integration
    def test_websocket_health_endpoint(self, client):
        """Test WebSocket health check endpoint."""
        response = client.get("/ws/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "active_connections" in data
        assert "active_sessions" in data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_connection_establishment(self, mock_auth):
        """Test WebSocket connection establishment (Testing Step 1)."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session-123?token=test-token") as websocket:
            # Should receive connection status
            data = websocket.receive_json()
            assert data["status"] == "connected"
            assert data["session_id"] == "test-session-123"
            assert "message" in data
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_authentication_required(self):
        """Test WebSocket requires authentication."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with patch('app.routers.websocket.authenticate_websocket', new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = None  # Authentication fails
            
            with pytest.raises(Exception):  # WebSocket should close
                with client.websocket_connect("/ws/feedback/test-session?token=invalid") as websocket:
                    pass
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, mock_auth):
        """Test WebSocket ping/pong keepalive."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"
            assert "timestamp" in response
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_transcript_message(self, mock_auth):
        """Test WebSocket transcript message handling (Testing Step 2)."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send transcript
            websocket.send_json({
                "type": "transcript",
                "data": "This is a test transcript for real-time feedback."
            })
            
            # Receive feedback
            feedback = websocket.receive_json()
            assert feedback["session_id"] == "test-session"
            assert feedback["feedback_type"] == "content_analysis"
            assert "metrics" in feedback
            assert "suggestions" in feedback
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_audio_chunk_message(self, mock_auth):
        """Test WebSocket audio chunk message handling (Testing Step 3)."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send audio chunk
            audio_data = base64.b64encode(b"fake_audio_data").decode('utf-8')
            websocket.send_json({
                "type": "audio_chunk",
                "data": audio_data,
                "chunk_index": 0,
                "is_final": False
            })
            
            # Receive feedback
            feedback = websocket.receive_json()
            assert feedback["session_id"] == "test-session"
            assert feedback["feedback_type"] == "speech_analysis"
            assert "metrics" in feedback
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_binary_audio_data(self, mock_auth):
        """Test WebSocket binary audio data handling."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send binary data
            websocket.send_bytes(b"fake_audio_binary_data")
            
            # Receive feedback
            feedback = websocket.receive_json()
            assert feedback["session_id"] == "test-session"
            assert feedback["feedback_type"] == "speech_analysis"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_metadata_update(self, mock_auth):
        """Test WebSocket metadata update."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Update metadata
            websocket.send_json({
                "type": "metadata",
                "data": {
                    "job_description": "Test job description",
                    "question_text": "Test question"
                }
            })
            
            # Should not error
            # Next message should use updated metadata
            websocket.send_json({
                "type": "transcript",
                "data": "Test answer"
            })
            
            feedback = websocket.receive_json()
            assert feedback["session_id"] == "test-session"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self, mock_auth):
        """Test WebSocket invalid JSON handling (Testing Step 6)."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send invalid JSON
            websocket.send_text("invalid json {")
            
            # Receive error feedback
            feedback = websocket.receive_json()
            assert feedback["feedback_type"] == "error"
            assert "invalid" in feedback["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_connection_management(self, mock_auth):
        """Test WebSocket connection management (Testing Step 5)."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.routers.websocket import manager
        
        client = TestClient(app)
        
        initial_connections = len(manager.active_connections)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Connection should be registered
            assert len(manager.active_connections) == initial_connections + 1
            assert "test-session" in manager.active_connections
            
            # Receive connection status
            websocket.receive_json()
        
        # Connection should be cleaned up
        assert "test-session" not in manager.active_connections
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, mock_auth):
        """Test WebSocket error handling (Testing Step 6)."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send message that causes error
            with patch('app.services.real_time_feedback.real_time_feedback_service.process_audio_chunk', 
                      side_effect=Exception("Test error")):
                websocket.send_json({
                    "type": "audio_chunk",
                    "data": base64.b64encode(b"data").decode('utf-8')
                })
                
                # Should receive error feedback
                feedback = websocket.receive_json()
                assert feedback["feedback_type"] == "error"
                assert "error" in feedback["message"].lower()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_multiple_messages(self, mock_auth):
        """Test WebSocket handling multiple messages (Testing Step 4)."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send multiple transcript messages
            for i in range(3):
                websocket.send_json({
                    "type": "transcript",
                    "data": f"Transcript message {i+1}"
                })
                
                feedback = websocket.receive_json()
                assert feedback["session_id"] == "test-session"
                assert feedback["feedback_type"] == "content_analysis"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_question_id_parameter(self, mock_auth):
        """Test WebSocket with question_id query parameter."""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/feedback/test-session?token=test-token&question_id=42") as websocket:
            # Receive connection status
            websocket.receive_json()
            
            # Send transcript
            websocket.send_json({
                "type": "transcript",
                "data": "Test answer"
            })
            
            # Feedback should include question_id in data
            feedback = websocket.receive_json()
            assert feedback["data"]["question_id"] == 42

