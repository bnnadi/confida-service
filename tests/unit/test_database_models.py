"""
Unit tests for database models.

Tests the database models including User, InterviewSession, Question,
SessionQuestion, and Answer models.
"""
import pytest
from datetime import datetime
import uuid
from sqlalchemy.exc import IntegrityError

from app.database.models import User, InterviewSession, Question, SessionQuestion, Answer


class TestUserModel:
    """Test cases for User model."""
    
    @pytest.mark.unit
    def test_create_user(self, test_db_session):
        """Test creating a user."""
        # Arrange
        user_data = {
            "id": str(uuid.uuid4()),
            "email": "test@example.com",
            "name": "Test User",
            "password_hash": "hashed_password_123",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        user = User(**user_data)
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        
        # Assert
        assert user.id == user_data["id"]
        assert user.email == user_data["email"]
        assert user.name == user_data["name"]
        assert user.password_hash == user_data["password_hash"]
        assert user.is_active == user_data["is_active"]
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.unit
    def test_user_email_unique(self, test_db_session):
        """Test that user email must be unique."""
        # Arrange
        email = "test@example.com"
        user1_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": "Test User 1",
            "password_hash": "hashed_password_123",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        user2_data = {
            "id": str(uuid.uuid4()),
            "email": email,  # Same email
            "name": "Test User 2",
            "password_hash": "hashed_password_456",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        user1 = User(**user1_data)
        test_db_session.add(user1)
        test_db_session.commit()
        
        user2 = User(**user2_data)
        test_db_session.add(user2)
        
        # Assert
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    @pytest.mark.unit
    def test_user_relationships(self, test_db_session, sample_user):
        """Test user relationships with interview sessions."""
        # Arrange
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": sample_user.id,
            "role": "Python Developer",
            "job_description": "Looking for Python developer",
            "status": "active",
            "total_questions": 5,
            "completed_questions": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        session = InterviewSession(**session_data)
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)
        
        # Assert
        assert len(sample_user.interview_sessions) == 1
        assert sample_user.interview_sessions[0].id == session.id


class TestInterviewSessionModel:
    """Test cases for InterviewSession model."""
    
    @pytest.mark.unit
    def test_create_interview_session(self, test_db_session, sample_user):
        """Test creating an interview session."""
        # Arrange
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": sample_user.id,
            "role": "Python Developer",
            "job_description": "Looking for Python developer with Django experience",
            "status": "active",
            "total_questions": 5,
            "completed_questions": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        session = InterviewSession(**session_data)
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)
        
        # Assert
        assert session.id == session_data["id"]
        assert session.user_id == session_data["user_id"]
        assert session.role == session_data["role"]
        assert session.job_description == session_data["job_description"]
        assert session.status == session_data["status"]
        assert session.total_questions == session_data["total_questions"]
        assert session.completed_questions == session_data["completed_questions"]
        assert session.created_at is not None
        assert session.updated_at is not None
    
    @pytest.mark.unit
    def test_interview_session_user_relationship(self, test_db_session, sample_user):
        """Test interview session relationship with user."""
        # Arrange
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": sample_user.id,
            "role": "Python Developer",
            "job_description": "Looking for Python developer",
            "status": "active",
            "total_questions": 5,
            "completed_questions": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        session = InterviewSession(**session_data)
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)
        
        # Assert
        assert session.user.id == sample_user.id
        assert session.user.email == sample_user.email
    
    @pytest.mark.unit
    def test_interview_session_status_enum(self, test_db_session, sample_user):
        """Test interview session status values."""
        # Arrange
        valid_statuses = ["active", "completed", "cancelled", "paused"]
        
        for status in valid_statuses:
            session_data = {
                "id": str(uuid.uuid4()),
                "user_id": sample_user.id,
                "role": "Python Developer",
                "job_description": "Looking for Python developer",
                "status": status,
                "total_questions": 5,
                "completed_questions": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Act
            session = InterviewSession(**session_data)
            test_db_session.add(session)
            test_db_session.commit()
            test_db_session.refresh(session)
            
            # Assert
            assert session.status == status


class TestQuestionModel:
    """Test cases for Question model."""
    
    @pytest.mark.unit
    def test_create_question(self, test_db_session):
        """Test creating a question."""
        # Arrange
        question_data = {
            "id": str(uuid.uuid4()),
            "question_text": "What is your Python experience?",
            "question_metadata": {"role": "python_developer", "context": "web_development"},
            "difficulty_level": "medium",
            "category": "technical",
            "subcategory": "web_frameworks",
            "compatible_roles": ["python_developer", "backend_developer"],
            "required_skills": ["python", "django", "flask"],
            "industry_tags": ["technology", "web_development"],
            "usage_count": 5,
            "average_score": 8.5,
            "success_rate": 0.85,
            "ai_service_used": "openai",
            "generation_prompt_hash": "hash_123",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        question = Question(**question_data)
        test_db_session.add(question)
        test_db_session.commit()
        test_db_session.refresh(question)
        
        # Assert
        assert question.id == question_data["id"]
        assert question.question_text == question_data["question_text"]
        assert question.question_metadata == question_data["question_metadata"]
        assert question.difficulty_level == question_data["difficulty_level"]
        assert question.category == question_data["category"]
        assert question.subcategory == question_data["subcategory"]
        assert question.compatible_roles == question_data["compatible_roles"]
        assert question.required_skills == question_data["required_skills"]
        assert question.industry_tags == question_data["industry_tags"]
        assert question.usage_count == question_data["usage_count"]
        assert question.average_score == question_data["average_score"]
        assert question.success_rate == question_data["success_rate"]
        assert question.ai_service_used == question_data["ai_service_used"]
        assert question.generation_prompt_hash == question_data["generation_prompt_hash"]
        assert question.created_at is not None
        assert question.updated_at is not None
    
    @pytest.mark.unit
    def test_question_category_required(self, test_db_session):
        """Test that question category is required."""
        # Arrange
        question_data = {
            "id": str(uuid.uuid4()),
            "question_text": "What is your Python experience?",
            "question_metadata": {"role": "python_developer"},
            "difficulty_level": "medium",
            # category is missing
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Act
        question = Question(**question_data)
        test_db_session.add(question)
        
        # Assert
        with pytest.raises(IntegrityError):
            test_db_session.commit()
    
    @pytest.mark.unit
    def test_question_difficulty_levels(self, test_db_session):
        """Test question difficulty levels."""
        # Arrange
        difficulty_levels = ["easy", "medium", "hard"]
        
        for difficulty in difficulty_levels:
            question_data = {
                "id": str(uuid.uuid4()),
                "question_text": f"Test question with {difficulty} difficulty",
                "question_metadata": {"role": "python_developer"},
                "difficulty_level": difficulty,
                "category": "technical",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Act
            question = Question(**question_data)
            test_db_session.add(question)
            test_db_session.commit()
            test_db_session.refresh(question)
            
            # Assert
            assert question.difficulty_level == difficulty


class TestSessionQuestionModel:
    """Test cases for SessionQuestion model."""
    
    @pytest.mark.unit
    def test_create_session_question(self, test_db_session, sample_interview_session, sample_question):
        """Test creating a session question."""
        # Arrange
        session_question_data = {
            "id": str(uuid.uuid4()),
            "session_id": sample_interview_session.id,
            "question_id": sample_question.id,
            "question_order": 1,
            "session_specific_context": {"role": "senior_developer", "focus": "technical_skills"},
            "created_at": datetime.utcnow()
        }
        
        # Act
        session_question = SessionQuestion(**session_question_data)
        test_db_session.add(session_question)
        test_db_session.commit()
        test_db_session.refresh(session_question)
        
        # Assert
        assert session_question.id == session_question_data["id"]
        assert session_question.session_id == session_question_data["session_id"]
        assert session_question.question_id == session_question_data["question_id"]
        assert session_question.question_order == session_question_data["question_order"]
        assert session_question.session_specific_context == session_question_data["session_specific_context"]
        assert session_question.created_at is not None
    
    @pytest.mark.unit
    def test_session_question_relationships(self, test_db_session, sample_interview_session, sample_question):
        """Test session question relationships."""
        # Arrange
        session_question_data = {
            "id": str(uuid.uuid4()),
            "session_id": sample_interview_session.id,
            "question_id": sample_question.id,
            "question_order": 1,
            "session_specific_context": {"role": "senior_developer"},
            "created_at": datetime.utcnow()
        }
        
        # Act
        session_question = SessionQuestion(**session_question_data)
        test_db_session.add(session_question)
        test_db_session.commit()
        test_db_session.refresh(session_question)
        
        # Assert
        assert session_question.session.id == sample_interview_session.id
        assert session_question.question.id == sample_question.id
        assert session_question.session.role == sample_interview_session.role
        assert session_question.question.question_text == sample_question.question_text
    
    @pytest.mark.unit
    def test_session_question_cascade_delete(self, test_db_session, sample_interview_session, sample_question):
        """Test cascade delete when session is deleted."""
        # Arrange
        session_question_data = {
            "id": str(uuid.uuid4()),
            "session_id": sample_interview_session.id,
            "question_id": sample_question.id,
            "question_order": 1,
            "session_specific_context": {"role": "senior_developer"},
            "created_at": datetime.utcnow()
        }
        
        session_question = SessionQuestion(**session_question_data)
        test_db_session.add(session_question)
        test_db_session.commit()
        
        # Act
        test_db_session.delete(sample_interview_session)
        test_db_session.commit()
        
        # Assert
        remaining_session_questions = test_db_session.query(SessionQuestion).filter_by(
            session_id=sample_interview_session.id
        ).all()
        assert len(remaining_session_questions) == 0


class TestAnswerModel:
    """Test cases for Answer model."""
    
    @pytest.mark.unit
    def test_create_answer(self, test_db_session, sample_question):
        """Test creating an answer."""
        # Arrange
        answer_data = {
            "id": str(uuid.uuid4()),
            "question_id": sample_question.id,
            "answer_text": "I have 5 years of Python experience with Django and Flask frameworks.",
            "analysis_result": {
                "score": {"clarity": 8.5, "confidence": 7.8, "relevance": 9.0, "overall": 8.4},
                "missingKeywords": ["Django", "Flask"],
                "improvements": ["Provide more specific examples"],
                "idealAnswer": "I have extensive experience with Python web frameworks..."
            },
            "created_at": datetime.utcnow()
        }
        
        # Act
        answer = Answer(**answer_data)
        test_db_session.add(answer)
        test_db_session.commit()
        test_db_session.refresh(answer)
        
        # Assert
        assert answer.id == answer_data["id"]
        assert answer.question_id == answer_data["question_id"]
        assert answer.answer_text == answer_data["answer_text"]
        assert answer.analysis_result == answer_data["analysis_result"]
        assert answer.created_at is not None
    
    @pytest.mark.unit
    def test_answer_question_relationship(self, test_db_session, sample_question):
        """Test answer relationship with question."""
        # Arrange
        answer_data = {
            "id": str(uuid.uuid4()),
            "question_id": sample_question.id,
            "answer_text": "I have 5 years of Python experience.",
            "analysis_result": {"score": {"overall": 8.5}},
            "created_at": datetime.utcnow()
        }
        
        # Act
        answer = Answer(**answer_data)
        test_db_session.add(answer)
        test_db_session.commit()
        test_db_session.refresh(answer)
        
        # Assert
        assert answer.question.id == sample_question.id
        assert answer.question.question_text == sample_question.question_text
    
    @pytest.mark.unit
    def test_answer_cascade_delete(self, test_db_session, sample_question):
        """Test cascade delete when question is deleted."""
        # Arrange
        answer_data = {
            "id": str(uuid.uuid4()),
            "question_id": sample_question.id,
            "answer_text": "I have 5 years of Python experience.",
            "analysis_result": {"score": {"overall": 8.5}},
            "created_at": datetime.utcnow()
        }
        
        answer = Answer(**answer_data)
        test_db_session.add(answer)
        test_db_session.commit()
        
        # Act
        test_db_session.delete(sample_question)
        test_db_session.commit()
        
        # Assert
        remaining_answers = test_db_session.query(Answer).filter_by(
            question_id=sample_question.id
        ).all()
        assert len(remaining_answers) == 0


class TestModelRelationships:
    """Test cases for model relationships."""
    
    @pytest.mark.unit
    def test_complete_interview_flow(self, test_db_session, sample_user):
        """Test complete interview flow with all models."""
        # Arrange
        # Create interview session
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": sample_user.id,
            "role": "Python Developer",
            "job_description": "Looking for Python developer",
            "status": "active",
            "total_questions": 2,
            "completed_questions": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        session = InterviewSession(**session_data)
        test_db_session.add(session)
        test_db_session.commit()
        test_db_session.refresh(session)
        
        # Create questions
        question1_data = {
            "id": str(uuid.uuid4()),
            "question_text": "What is your Python experience?",
            "question_metadata": {"role": "python_developer"},
            "difficulty_level": "medium",
            "category": "technical",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        question1 = Question(**question1_data)
        test_db_session.add(question1)
        
        question2_data = {
            "id": str(uuid.uuid4()),
            "question_text": "How do you debug Python code?",
            "question_metadata": {"role": "python_developer"},
            "difficulty_level": "easy",
            "category": "technical",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        question2 = Question(**question2_data)
        test_db_session.add(question2)
        test_db_session.commit()
        test_db_session.refresh(question1)
        test_db_session.refresh(question2)
        
        # Create session questions
        session_question1_data = {
            "id": str(uuid.uuid4()),
            "session_id": session.id,
            "question_id": question1.id,
            "question_order": 1,
            "session_specific_context": {"role": "senior_developer"},
            "created_at": datetime.utcnow()
        }
        session_question1 = SessionQuestion(**session_question1_data)
        test_db_session.add(session_question1)
        
        session_question2_data = {
            "id": str(uuid.uuid4()),
            "session_id": session.id,
            "question_id": question2.id,
            "question_order": 2,
            "session_specific_context": {"role": "senior_developer"},
            "created_at": datetime.utcnow()
        }
        session_question2 = SessionQuestion(**session_question2_data)
        test_db_session.add(session_question2)
        test_db_session.commit()
        test_db_session.refresh(session_question1)
        test_db_session.refresh(session_question2)
        
        # Create answers
        answer1_data = {
            "id": str(uuid.uuid4()),
            "question_id": question1.id,
            "answer_text": "I have 5 years of Python experience.",
            "analysis_result": {"score": {"overall": 8.5}},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        answer1 = Answer(**answer1_data)
        test_db_session.add(answer1)
        
        answer2_data = {
            "id": str(uuid.uuid4()),
            "question_id": question2.id,
            "answer_text": "I use pdb and logging for debugging.",
            "analysis_result": {"score": {"overall": 7.8}},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        answer2 = Answer(**answer2_data)
        test_db_session.add(answer2)
        test_db_session.commit()
        test_db_session.refresh(answer1)
        test_db_session.refresh(answer2)
        
        # Act & Assert
        # Test user -> sessions relationship
        assert len(sample_user.interview_sessions) == 1
        assert sample_user.interview_sessions[0].id == session.id
        
        # Test session -> session_questions relationship
        assert len(session.session_questions) == 2
        assert session.session_questions[0].id == session_question1.id
        assert session.session_questions[1].id == session_question2.id
        
        # Test session_questions -> questions relationship
        assert session_question1.question.id == question1.id
        assert session_question2.question.id == question2.id
        
        # Test questions -> answers relationship
        assert len(question1.answers) == 1
        assert len(question2.answers) == 1
        assert question1.answers[0].id == answer1.id
        assert question2.answers[0].id == answer2.id
