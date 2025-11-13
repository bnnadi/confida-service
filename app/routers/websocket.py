"""
WebSocket router for real-time feedback during interviews.
"""
import json
import base64
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.models.real_time_models import (
    RealTimeFeedback,
    FeedbackType,
    ConnectionStatus
)
from app.services.real_time_feedback import real_time_feedback_service
from app.middleware.auth_middleware import AuthMiddleware
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _create_error_feedback(session_id: str, message: str) -> RealTimeFeedback:
    """Create standardized error feedback."""
    return RealTimeFeedback(
        session_id=session_id,
        feedback_type=FeedbackType.ERROR,
        message=message,
        confidence=0.0
    )


def _get_session_metadata(session_id: str) -> tuple[Optional[str], Optional[str]]:
    """Get job description and question text from session metadata."""
    session_info = real_time_feedback_service.get_session_info(session_id)
    if not session_info:
        return None, None
    metadata = session_info.get("metadata", {})
    return metadata.get("job_description"), metadata.get("question_text")


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_personal_message(self, message: dict, session_id: str):
        """Send message to specific session."""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to session {session_id}: {e}")
                self.disconnect(session_id)
    
    async def send_feedback(self, feedback: RealTimeFeedback, session_id: str):
        """Send feedback message to session."""
        await self.send_personal_message(feedback.dict(), session_id)


# Global connection manager
manager = ConnectionManager()


async def authenticate_websocket(websocket: WebSocket) -> Optional[dict]:
    """
    Authenticate WebSocket connection using token from query params or headers.
    
    Args:
        websocket: WebSocket connection
        
    Returns:
        User dictionary if authenticated, None otherwise
    """
    try:
        # Try to get token from query params first
        token = websocket.query_params.get("token")
        
        # If not in query params, try to get from headers (subprotocol)
        if not token and websocket.headers.get("sec-websocket-protocol"):
            protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
            for protocol in protocols:
                if protocol.strip().startswith("token."):
                    token = protocol.strip().replace("token.", "")
                    break
        
        if not token:
            logger.warning("No token provided in WebSocket connection")
            return None
        
        # Verify token using auth middleware
        from app.services.database_service import database_service
        from types import SimpleNamespace
        
        db = database_service.get_sync_session()
        try:
            auth_middleware = AuthMiddleware(db)
            credentials = SimpleNamespace(credentials=token)
            user = auth_middleware.get_current_user(credentials)
            
            if not user:
                logger.warning("Invalid token for WebSocket connection")
                return None
            
            return user
        finally:
            # Close database session
            if hasattr(db, 'close'):
                db.close()
        
    except Exception as e:
        logger.error(f"Error authenticating WebSocket: {e}")
        return None


@router.websocket("/ws/feedback/{session_id}")
async def feedback_websocket(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for real-time feedback during interview.
    
    Accepts audio chunks and returns real-time feedback on speech patterns,
    content analysis, and suggestions.
    
    Message format (client -> server):
    - Audio chunks: {"type": "audio_chunk", "data": base64_encoded_audio, "chunk_index": int, "is_final": bool}
    - Transcript chunks: {"type": "transcript", "data": "transcript text"}
    - Control: {"type": "ping"} for keepalive
    
    Message format (server -> client):
    - Feedback: RealTimeFeedback model as JSON
    - Status: ConnectionStatus model as JSON
    """
    # Authenticate connection
    user = await authenticate_websocket(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    # Get question_id from query params if provided
    question_id = None
    if "question_id" in websocket.query_params:
        try:
            question_id = int(websocket.query_params["question_id"])
        except ValueError:
            pass
    
    # Register session
    real_time_feedback_service.register_session(
        session_id=session_id,
        user_id=str(user["id"]),
        metadata={"question_id": question_id}
    )
    
    # Connect WebSocket
    await manager.connect(websocket, session_id)
    
    # Send connection status
    connection_status = ConnectionStatus(
        status="connected",
        session_id=session_id,
        message="WebSocket connected successfully"
    )
    await websocket.send_json(connection_status.dict())
    
    try:
        # Get session metadata for context
        job_description, question_text = _get_session_metadata(session_id)
        
        while True:
            # Receive message
            try:
                data = await websocket.receive()
            except WebSocketDisconnect:
                break
            
            # Handle different message types
            if "text" in data:
                # JSON message
                try:
                    message = json.loads(data["text"])
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        # Keepalive
                        await websocket.send_json({"type": "pong", "timestamp": str(datetime.utcnow())})
                    
                    elif message_type == "transcript":
                        # Process transcript chunk
                        transcript = message.get("data", "")
                        if transcript:
                            feedback = await real_time_feedback_service.process_transcript_chunk(
                                session_id=session_id,
                                transcript=transcript,
                                question_id=question_id,
                                job_description=job_description,
                                question_text=question_text
                            )
                            await manager.send_feedback(feedback, session_id)
                    
                    elif message_type == "audio_chunk":
                        # Process audio chunk
                        audio_data_b64 = message.get("data", "")
                        chunk_index = message.get("chunk_index", 0)
                        is_final = message.get("is_final", False)
                        
                        try:
                            audio_data = base64.b64decode(audio_data_b64)
                            feedback = await real_time_feedback_service.process_audio_chunk(
                                session_id=session_id,
                                audio_data=audio_data,
                                question_id=question_id,
                                transcript=message.get("transcript")  # Optional transcript
                            )
                            await manager.send_feedback(feedback, session_id)
                        except Exception as e:
                            logger.error(f"Error processing audio chunk: {e}")
                            await manager.send_feedback(
                                _create_error_feedback(session_id, f"Error processing audio: {str(e)}"),
                                session_id
                            )
                    
                    elif message_type == "metadata":
                        # Update session metadata
                        metadata = message.get("data", {})
                        session_info = real_time_feedback_service.get_session_info(session_id)
                        if session_info:
                            session_info["metadata"].update(metadata)
                            if "job_description" in metadata:
                                job_description = metadata["job_description"]
                            if "question_text" in metadata:
                                question_text = metadata["question_text"]
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in WebSocket message: {e}")
                    await manager.send_feedback(
                        _create_error_feedback(session_id, "Invalid message format"),
                        session_id
                    )
            
            elif "bytes" in data:
                # Binary audio data
                audio_data = data["bytes"]
                feedback = await real_time_feedback_service.process_audio_chunk(
                    session_id=session_id,
                    audio_data=audio_data,
                    question_id=question_id
                )
                await manager.send_feedback(feedback, session_id)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler for session {session_id}: {e}")
        try:
            await manager.send_feedback(
                _create_error_feedback(session_id, f"Connection error: {str(e)}"),
                session_id
            )
        except:
            pass
    finally:
        # Cleanup
        manager.disconnect(session_id)
        real_time_feedback_service.cleanup_session(session_id)
        
        # Send disconnect status
        disconnect_status = ConnectionStatus(
            status="disconnected",
            session_id=session_id,
            message="WebSocket disconnected"
        )
        try:
            await websocket.send_json(disconnect_status.dict())
        except:
            pass


@router.get("/ws/health")
async def websocket_health():
    """Health check for WebSocket service."""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "active_sessions": len(real_time_feedback_service.active_sessions)
    }

