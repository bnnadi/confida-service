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
        hashed_password="hashed_password_here",
        first_name="Test",
        last_name="User"
    )
    
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.full_name == "Test User"


def test_interview_session_model_creation(db_session: Session):
    """Test creating an interview session model."""
    # First create a user
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_here"
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
    # Create user and session first
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_here"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    session = InterviewSession(
        user_id=user.id,
        role="Software Engineer",
        job_description="A great job opportunity"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    
    # Create question
    question = Question(
        session_id=session.id,
        question_text="What is your experience with Python?",
        question_order=1
    )
    
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    assert question.id is not None
    assert question.session_id == session.id
    assert question.question_text == "What is your experience with Python?"
    assert question.question_order == 1


def test_answer_model_creation(db_session: Session):
    """Test creating an answer model."""
    # Create user, session, and question first
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_here"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    session = InterviewSession(
        user_id=user.id,
        role="Software Engineer",
        job_description="A great job opportunity"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    
    question = Question(
        session_id=session.id,
        question_text="What is your experience with Python?",
        question_order=1
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    
    # Create answer
    answer = Answer(
        question_id=question.id,
        answer_text="I have 5 years of experience with Python",
        analysis_result={"clarity": 8, "relevance": 9},
        score={"overall": 8.5}
    )
    
    db_session.add(answer)
    db_session.commit()
    db_session.refresh(answer)
    
    assert answer.id is not None
    assert answer.question_id == question.id
    assert answer.answer_text == "I have 5 years of experience with Python"
    assert answer.analysis_result == {"clarity": 8, "relevance": 9}
    assert answer.score == {"overall": 8.5}
