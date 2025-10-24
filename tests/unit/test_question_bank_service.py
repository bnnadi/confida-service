"""
Unit tests for QuestionService.

Tests the core functionality of the question bank service including
question retrieval, storage, and statistics.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid

from app.services.question_service import QuestionService
from app.database.models import Question, SessionQuestion


class TestQuestionService:
        """Test cases for QuestionService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        session.query.return_value.count.return_value = 0
        session.query.return_value.group_by.return_value.all.return_value = []
        session.query.return_value.filter.return_value.first.return_value = None
        session.add.return_value = None
        session.commit.return_value = None
        return session
    
    @pytest.fixture
    def question_bank_service(self, mock_db_session):
        """Create QuestionService instance with mocked database."""
        return QuestionService(mock_db_session)
    
    @pytest.mark.unit
    def test_get_questions_for_role_no_questions(self, question_bank_service, mock_db_session):
        """Test getting questions when no questions exist in bank."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        count = 5
        
        # Act
        questions = question_bank_service.get_questions_for_role(role, job_description, count)
        
        # Assert
        assert questions == []
        mock_db_session.query.assert_called_once()
    
    @pytest.mark.unit
    def test_get_questions_for_role_with_questions(self, question_bank_service, mock_db_session):
        """Test getting questions when questions exist in bank."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        count = 5
        
        # Create mock questions
        mock_questions = [
            Mock(
                id=str(uuid.uuid4()),
                question_text="What is your Python experience?",
                category="technical",
                difficulty_level="medium",
                usage_count=5,
                average_score=8.5
            ),
            Mock(
                id=str(uuid.uuid4()),
                question_text="How do you debug Python code?",
                category="technical",
                difficulty_level="easy",
                usage_count=3,
                average_score=7.8
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_questions
        
        # Act
        questions = question_bank_service.get_questions_for_role(role, job_description, count)
        
        # Assert
        assert len(questions) == 2
        assert questions[0].question_text == "What is your Python experience?"
        assert questions[1].question_text == "How do you debug Python code?"
    
    @pytest.mark.unit
    def test_store_generated_questions_new_questions(self, question_bank_service, mock_db_session):
        """Test storing new questions in the question bank."""
        # Arrange
        questions = [
            "What is your Python experience?",
            "How do you handle debugging?"
        ]
        role = "Python Developer"
        job_description = "Looking for Python developer"
        ai_service_used = "openai"
        prompt_hash = "hash_123"
        
        # Mock no existing questions
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        question_bank_service.store_generated_questions(
            questions, role, job_description, ai_service_used, prompt_hash
        )
        
        # Assert
        assert mock_db_session.add.call_count == 2
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.unit
    def test_store_generated_questions_existing_questions(self, question_bank_service, mock_db_session):
        """Test storing questions when some already exist."""
        # Arrange
        questions = [
            "What is your Python experience?",
            "How do you handle debugging?"
        ]
        role = "Python Developer"
        job_description = "Looking for Python developer"
        ai_service_used = "openai"
        prompt_hash = "hash_123"
        
        # Mock existing question
        existing_question = Mock()
        existing_question.usage_count = 5
        mock_db_session.query.return_value.filter.return_value.first.return_value = existing_question
        
        # Act
        question_bank_service.store_generated_questions(
            questions, role, job_description, ai_service_used, prompt_hash
        )
        
        # Assert
        assert existing_question.usage_count == 6  # Incremented
        mock_db_session.commit.assert_called_once()
    
    @pytest.mark.unit
    def test_get_question_bank_stats(self, question_bank_service, mock_db_session):
        """Test getting question bank statistics."""
        # Arrange
        mock_db_session.query.return_value.count.return_value = 100
        mock_db_session.query.return_value.group_by.return_value.all.return_value = [
            ("technical", 60),
            ("behavioral", 30),
            ("system_design", 10)
        ]
        
        # Mock difficulty stats
        def mock_group_by_side_effect(*args, **kwargs):
            if "difficulty_level" in str(args):
                return Mock(all=lambda: [("easy", 20), ("medium", 50), ("hard", 30)])
            return Mock(all=lambda: [("technical", 60), ("behavioral", 30), ("system_design", 10)])
        
        mock_db_session.query.return_value.group_by.side_effect = mock_group_by_side_effect
        
        # Act
        stats = question_bank_service.get_question_bank_stats()
        
        # Assert
        assert stats["total_questions"] == 100
        assert "questions_by_category" in stats
        assert "questions_by_difficulty" in stats
        assert "last_updated" in stats
    
    @pytest.mark.unit
    def test_extract_keywords_from_role_and_jd(self, question_bank_service):
        """Test keyword extraction from role and job description."""
        # Arrange
        role = "Senior Python Developer"
        job_description = "Looking for Python developer with Django experience"
        
        # Act
        keywords = question_bank_service._extract_keywords_from_role_and_jd(role, job_description)
        
        # Assert
        assert "python" in keywords
        assert "developer" in keywords
        assert "django" in keywords
        assert "experience" in keywords
        assert len(keywords) > 0
    
    @pytest.mark.unit
    def test_determine_category_technical(self, question_bank_service):
        """Test category determination for technical questions."""
        # Arrange
        question_text = "How do you optimize database queries in Python?"
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        category = question_bank_service._determine_category(question_text, role, job_description)
        
        # Assert
        assert category == "technical"
    
    @pytest.mark.unit
    def test_determine_category_behavioral(self, question_bank_service):
        """Test category determination for behavioral questions."""
        # Arrange
        question_text = "Tell me about a time when you faced a challenging situation"
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        category = question_bank_service._determine_category(question_text, role, job_description)
        
        # Assert
        assert category == "behavioral"
    
    @pytest.mark.unit
    def test_determine_category_system_design(self, question_bank_service):
        """Test category determination for system design questions."""
        # Arrange
        question_text = "How would you design a scalable web application architecture?"
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        category = question_bank_service._determine_category(question_text, role, job_description)
        
        # Assert
        assert category == "system_design"
    
    @pytest.mark.unit
    def test_determine_difficulty_easy(self, question_bank_service):
        """Test difficulty determination for easy questions."""
        # Arrange
        question_text = "What is Python?"
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        difficulty = question_bank_service._determine_difficulty(question_text, role, job_description)
        
        # Assert
        assert difficulty == "easy"
    
    @pytest.mark.unit
    def test_determine_difficulty_medium(self, question_bank_service):
        """Test difficulty determination for medium questions."""
        # Arrange
        question_text = "How do you handle exceptions in Python applications?"
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        difficulty = question_bank_service._determine_difficulty(question_text, role, job_description)
        
        # Assert
        assert difficulty == "medium"
    
    @pytest.mark.unit
    def test_determine_difficulty_hard(self, question_bank_service):
        """Test difficulty determination for hard questions."""
        # Arrange
        question_text = "How would you optimize a complex distributed system with multiple microservices and handle trade-offs between consistency and availability?"
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        difficulty = question_bank_service._determine_difficulty(question_text, role, job_description)
        
        # Assert
        assert difficulty == "hard"
    
    @pytest.mark.unit
    def test_store_generated_questions_with_exception(self, question_bank_service, mock_db_session):
        """Test storing questions when database exception occurs."""
        # Arrange
        questions = ["What is your Python experience?"]
        role = "Python Developer"
        job_description = "Looking for Python developer"
        ai_service_used = "openai"
        prompt_hash = "hash_123"
        
        # Mock database exception
        mock_db_session.commit.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception):
            question_bank_service.store_generated_questions(
                questions, role, job_description, ai_service_used, prompt_hash
            )
    
    @pytest.mark.unit
    def test_get_questions_for_role_with_exception(self, question_bank_service, mock_db_session):
        """Test getting questions when database exception occurs."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        count = 5
        
        # Mock database exception
        mock_db_session.query.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception):
            question_bank_service.get_questions_for_role(role, job_description, count)
    
    @pytest.mark.unit
    def test_get_question_bank_stats_with_exception(self, question_bank_service, mock_db_session):
        """Test getting stats when database exception occurs."""
        # Arrange
        mock_db_session.query.return_value.count.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(Exception):
            question_bank_service.get_question_bank_stats()
