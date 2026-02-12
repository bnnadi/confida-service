"""
Unit tests for answer audio file ID persistence (Ticket #082).

Tests that answer audio file IDs are properly stored and persisted
in both Answer model and SessionQuestion.session_specific_context.
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.models import User, InterviewSession, Question, Answer, SessionQuestion


class TestAnswerAudioFilePersistence:
    """Test cases for answer audio file ID persistence."""
    
    @pytest.mark.unit
    def test_answer_with_audio_file_id(self, test_db_session: Session, sample_question):
        """Test creating an answer with audio_file_id."""
        # Arrange
        audio_file_id = "audio_file_123"
        answer_data = {
            "question_id": sample_question.id,
            "answer_text": "I have 5 years of Python experience.",
            "audio_file_id": audio_file_id,
            "analysis_result": {"score": {"overall": 8.5}},
        }
        
        # Act
        answer = Answer(**answer_data)
        test_db_session.add(answer)
        test_db_session.commit()
        test_db_session.refresh(answer)
        
        # Assert
        assert answer.id is not None
        assert answer.audio_file_id == audio_file_id
        assert answer.answer_text == answer_data["answer_text"]
    
    @pytest.mark.unit
    def test_answer_without_audio_file_id(self, test_db_session: Session, sample_question):
        """Test creating an answer without audio_file_id (backward compatibility)."""
        # Arrange
        answer_data = {
            "question_id": sample_question.id,
            "answer_text": "I have 5 years of Python experience.",
            "analysis_result": {"score": {"overall": 8.5}},
        }
        
        # Act
        answer = Answer(**answer_data)
        test_db_session.add(answer)
        test_db_session.commit()
        test_db_session.refresh(answer)
        
        # Assert
        assert answer.id is not None
        assert answer.audio_file_id is None  # Should be nullable
        assert answer.answer_text == answer_data["answer_text"]
    
    @pytest.mark.unit
    def test_session_question_context_with_audio_file_id(
        self, test_db_session: Session, sample_interview_session, sample_question
    ):
        """Test that SessionQuestion.session_specific_context stores answer_audio_file_id."""
        # Arrange
        audio_file_id = "audio_file_456"
        session_question = SessionQuestion(
            session_id=sample_interview_session.id,
            question_id=sample_question.id,
            question_order=1,
            session_specific_context={"answer_audio_file_id": audio_file_id}
        )
        
        # Act
        test_db_session.add(session_question)
        test_db_session.commit()
        test_db_session.refresh(session_question)
        
        # Assert
        assert session_question.id is not None
        assert session_question.session_specific_context is not None
        assert session_question.session_specific_context["answer_audio_file_id"] == audio_file_id
    
    @pytest.mark.unit
    def test_session_question_context_update_audio_file_id(
        self, test_db_session: Session, sample_interview_session, sample_question
    ):
        """Test updating SessionQuestion.session_specific_context with answer_audio_file_id."""
        # Arrange - Create session question without audio file ID
        session_question = SessionQuestion(
            session_id=sample_interview_session.id,
            question_id=sample_question.id,
            question_order=1,
            session_specific_context={"role": "senior_developer"}
        )
        test_db_session.add(session_question)
        test_db_session.commit()
        test_db_session.refresh(session_question)
        
        # Act - Update with audio file ID (assign new dict so SQLAlchemy detects change)
        audio_file_id = "audio_file_789"
        from sqlalchemy.orm.attributes import flag_modified
        context = dict(session_question.session_specific_context or {})
        context["answer_audio_file_id"] = audio_file_id
        session_question.session_specific_context = context
        flag_modified(session_question, "session_specific_context")
        test_db_session.commit()
        test_db_session.refresh(session_question)
        
        # Assert
        assert session_question.session_specific_context["answer_audio_file_id"] == audio_file_id
        assert session_question.session_specific_context["role"] == "senior_developer"  # Preserve existing context
    
    @pytest.mark.unit
    def test_answer_and_session_question_linked_audio_file_id(
        self, test_db_session: Session, sample_interview_session, sample_question
    ):
        """Test that answer audio_file_id is stored in both Answer and SessionQuestion."""
        # Arrange
        audio_file_id = "audio_file_linked_123"
        
        # Create session question
        session_question = SessionQuestion(
            session_id=sample_interview_session.id,
            question_id=sample_question.id,
            question_order=1
        )
        test_db_session.add(session_question)
        test_db_session.commit()
        
        # Create answer with audio file ID
        answer = Answer(
            question_id=sample_question.id,
            answer_text="Test answer",
            audio_file_id=audio_file_id
        )
        test_db_session.add(answer)
        
        # Update session question context
        context = session_question.session_specific_context or {}
        context["answer_audio_file_id"] = audio_file_id
        session_question.session_specific_context = context
        
        test_db_session.commit()
        test_db_session.refresh(answer)
        test_db_session.refresh(session_question)
        
        # Assert
        assert answer.audio_file_id == audio_file_id
        assert session_question.session_specific_context["answer_audio_file_id"] == audio_file_id
        assert answer.audio_file_id == session_question.session_specific_context["answer_audio_file_id"]

