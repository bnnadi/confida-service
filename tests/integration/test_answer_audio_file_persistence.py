"""
Integration tests for answer audio file ID persistence (Ticket #082).

Tests the complete flow of storing and retrieving answer audio file IDs
through the API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from sqlalchemy.orm import Session

from app.database.models import Answer, SessionQuestion, InterviewSession


class TestAnswerAudioFilePersistenceIntegration:
    """Integration tests for answer audio file ID persistence."""
    
    @pytest.fixture
    def mock_current_user(self, sample_user):
        """Mock current user for authentication."""
        return {
            "id": str(sample_user.id),
            "email": sample_user.email
        }
    
    @pytest.fixture
    def sample_question_with_session(self, db_session, sample_user, sample_question):
        """Create a question linked to a session for testing."""
        # Create interview session
        session = InterviewSession(
            user_id=sample_user.id,
            role="Software Engineer",
            job_description="Test job description"
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Create session question
        session_question = SessionQuestion(
            session_id=session.id,
            question_id=sample_question.id,
            question_order=1
        )
        db_session.add(session_question)
        db_session.commit()
        
        return sample_question, session
    
    @pytest.mark.integration
    def test_analyze_answer_with_audio_file_id(
        self, client: TestClient, db_session: Session,
        sample_user, mock_current_user, sample_question_with_session, mock_ai_client,
        override_auth, override_ai_client
    ):
        """Test analyze_answer endpoint stores audio_file_id."""
        sample_question, session = sample_question_with_session
        
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)
        
        # Arrange
        audio_file_id = "test_audio_file_123"
        request_data = {
            "jobDescription": "Software Engineer position",
            "question": "What is your experience?",
            "answer": "I have 5 years of experience",
            "audio_file_id": audio_file_id
        }
        
        # Mock AI client response
        mock_ai_client.analyze_answer = AsyncMock(return_value={
            "analysis": "Good answer",
            "score": {"clarity": 8, "confidence": 7},
            "suggestions": []
        })
        
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verify answer was stored with audio_file_id
        answer = db_session.query(Answer).filter(
            Answer.question_id == sample_question.id
        ).first()
        
        assert answer is not None
        assert answer.audio_file_id == audio_file_id
        assert answer.answer_text == request_data["answer"]
        
        # Verify SessionQuestion was updated
        session_question = db_session.query(SessionQuestion).filter(
            SessionQuestion.question_id == sample_question.id
        ).first()
        
        if session_question:
            assert session_question.session_specific_context is not None
            assert session_question.session_specific_context.get("answer_audio_file_id") == audio_file_id
    
    @pytest.mark.integration
    def test_analyze_answer_without_audio_file_id(
        self, client: TestClient, db_session: Session,
        sample_user, mock_current_user, sample_question_with_session, mock_ai_client,
        override_auth, override_ai_client
    ):
        """Test analyze_answer endpoint works without audio_file_id (backward compatibility)."""
        sample_question, session = sample_question_with_session
        
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)
        
        # Arrange
        request_data = {
            "jobDescription": "Software Engineer position",
            "question": "What is your experience?",
            "answer": "I have 5 years of experience"
            # No audio_file_id
        }
        
        # Mock AI client response
        mock_ai_client.analyze_answer = AsyncMock(return_value={
            "analysis": "Good answer",
            "score": {"clarity": 8, "confidence": 7},
            "suggestions": []
        })
        
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verify answer was stored without audio_file_id
        answer = db_session.query(Answer).filter(
            Answer.question_id == sample_question.id
        ).first()
        
        assert answer is not None
        assert answer.audio_file_id is None  # Should be None, not error
    
    @pytest.mark.integration
    def test_add_answer_to_question_with_audio_file_id(
        self, client: TestClient, db_session: Session,
        sample_user, mock_current_user, sample_question, sample_interview_session,
        override_auth
    ):
        """Test add_answer_to_question endpoint stores audio_file_id."""
        override_auth(mock_current_user)
        
        # Arrange
        audio_file_id = "test_audio_file_456"
        
        # Create session question first
        from app.database.models import SessionQuestion
        session_question = SessionQuestion(
            session_id=sample_interview_session.id,
            question_id=sample_question.id,
            question_order=1
        )
        db_session.add(session_question)
        db_session.commit()
        
        request_data = {
            "answer_text": "I have extensive Python experience",
            "audio_file_id": audio_file_id
        }
        
        # Act
        response = client.post(
            f"/api/v1/sessions/questions/{sample_question.id}/answers",
            json=request_data
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["audio_file_id"] == audio_file_id
        
        # Verify in database
        answer = db_session.query(Answer).filter(
            Answer.question_id == sample_question.id
        ).first()
        assert answer.audio_file_id == audio_file_id
        
        # Verify SessionQuestion was updated
        db_session.refresh(session_question)
        assert session_question.session_specific_context is not None
        assert session_question.session_specific_context.get("answer_audio_file_id") == audio_file_id
    
    @pytest.mark.integration
    def test_get_question_answers_includes_audio_file_id(
        self, client: TestClient, db_session: Session,
        sample_user, mock_current_user, sample_question, sample_interview_session,
        override_auth
    ):
        """Test get_question_answers endpoint returns audio_file_id."""
        override_auth(mock_current_user)
        
        # Arrange
        audio_file_id = "test_audio_file_789"
        
        # Create answer with audio_file_id
        answer = Answer(
            question_id=sample_question.id,
            answer_text="Test answer",
            audio_file_id=audio_file_id
        )
        db_session.add(answer)
        db_session.commit()
        
        # Act
        response = client.get(
            f"/api/v1/sessions/questions/{sample_question.id}/answers"
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["audio_file_id"] == audio_file_id
    
    @pytest.mark.integration
    def test_deterministic_audio_file_id_persistence(
        self, client: TestClient, db_session: Session,
        sample_user, mock_current_user, sample_question, sample_interview_session, mock_ai_client,
        override_auth, override_ai_client
    ):
        """Test that same question uses same audio file ID (deterministic)."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)
        
        # Arrange
        audio_file_id = "deterministic_audio_123"
        
        # Create session question
        from app.database.models import SessionQuestion
        session_question = SessionQuestion(
            session_id=sample_interview_session.id,
            question_id=sample_question.id,
            question_order=1
        )
        db_session.add(session_question)
        db_session.commit()
        
        # First answer with audio_file_id
        request_data = {
            "jobDescription": "Software Engineer",
            "question": "Test question",
            "answer": "First answer",
            "audio_file_id": audio_file_id
        }
        
        mock_ai_client.analyze_answer = AsyncMock(return_value={
            "analysis": "Good",
            "score": {"clarity": 8},
            "suggestions": []
        })
        
        # Act - Submit first answer
        response1 = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=request_data
        )
        
        assert response1.status_code == 200
        
        # Submit second answer with same audio_file_id
        request_data2 = {
            "jobDescription": "Software Engineer",
            "question": "Test question",
            "answer": "Second answer",
            "audio_file_id": audio_file_id
        }
        
        response2 = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=request_data2
        )
        
        assert response2.status_code == 200
        
        # Assert - Both answers should have same audio_file_id
        answers = db_session.query(Answer).filter(
            Answer.question_id == sample_question.id
        ).all()
        
        assert len(answers) >= 2
        # All answers for this question should reference the same audio file
        audio_file_ids = {a.audio_file_id for a in answers if a.audio_file_id}
        assert audio_file_id in audio_file_ids
        
        # SessionQuestion should still have the audio_file_id
        db_session.refresh(session_question)
        assert session_question.session_specific_context.get("answer_audio_file_id") == audio_file_id

