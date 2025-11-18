"""
Tests for database models.
"""
import pytest
from sqlalchemy.orm import Session
from app.models.schemas import UserResponse
from app.database.models import User, InterviewSession, Question, Answer


def test_user_model_creation(db_session: Session):
    """Test creating a user model."""
    user = User(
        email="test@example.com",
        password_hash="hashed_password_here",
        name="Test User"
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.name == "Test User"


def test_interview_session_model_creation(db_session: Session):
    """Test creating an interview session model."""
    # First create a user
    user = User(
        email="test@example.com",
        password_hash="hashed_password_here",
        name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create interview session
    session = InterviewSession(
        user_id=user.id,
        role="Software Engineer",
        job_description="A great job opportunity"
    )
    
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    
    assert session.id is not None
    assert session.user_id == user.id
    assert session.role == "Software Engineer"
    assert session.job_description == "A great job opportunity"
    assert session.status == "active"  # default value


def test_question_model_creation(db_session: Session):
    """Test creating a question model."""
    # Create question (global question bank, not session-specific)
    question = Question(
        question_text="What is your experience with Python?",
        question_metadata={},
        category="technical",
        difficulty_level="medium"
    )
    
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    assert question.id is not None
    assert question.question_text == "What is your experience with Python?"
    assert question.category == "technical"
    assert question.difficulty_level == "medium"


def test_answer_model_creation(db_session: Session):
    """Test creating an answer model."""
    # Create question first (global question bank)
    question = Question(
        question_text="What is your experience with Python?",
        question_metadata={},
        category="technical",
        difficulty_level="medium"
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    # Create answer
    answer = Answer(
        question_id=question.id,
        answer_text="I have 5 years of experience with Python",
        analysis_result={"clarity": 8, "relevance": 9},
        score={"overall": 8.5},
        audio_file_id="test_audio_file_123"  # Test audio_file_id field
    )
    
    db_session.add(answer)
    db_session.commit()
    db_session.refresh(answer)
    
    assert answer.id is not None
    assert answer.question_id == question.id
    assert answer.answer_text == "I have 5 years of experience with Python"
    assert answer.analysis_result == {"clarity": 8, "relevance": 9}
    assert answer.score == {"overall": 8.5}
    assert answer.audio_file_id == "test_audio_file_123"
