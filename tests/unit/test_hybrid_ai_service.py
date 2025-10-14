"""
Unit tests for HybridAIService.

Tests the core functionality of the hybrid AI service including
question generation, answer analysis, and service management.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import uuid

from app.services.hybrid_ai_service import HybridAIService
from app.services.question_bank_service import QuestionBankService


class TestHybridAIService:
    """Test cases for HybridAIService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        session.query.return_value.count.return_value = 0
        session.add.return_value = None
        session.commit.return_value = None
        return session
    
    @pytest.fixture
    def mock_question_bank_service(self):
        """Mock question bank service."""
        service = Mock(spec=QuestionBankService)
        service.get_questions_for_role.return_value = []
        service.store_generated_questions.return_value = None
        service.get_question_bank_stats.return_value = {
            "total_questions": 100,
            "questions_by_category": {"technical": 60, "behavioral": 30},
            "questions_by_difficulty": {"easy": 20, "medium": 50, "hard": 30}
        }
        return service
    
    @pytest.fixture
    def hybrid_ai_service(self, mock_db_session, mock_question_bank_service):
        """Create HybridAIService instance with mocked dependencies."""
        service = HybridAIService()
        service.db_session = mock_db_session
        service.question_bank_service = mock_question_bank_service
        return service
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_interview_questions_from_bank(self, hybrid_ai_service, mock_question_bank_service):
        """Test generating questions from question bank."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        preferred_service = "openai"
        
        # Mock questions from bank
        mock_questions = [
            Mock(
                id=str(uuid.uuid4()),
                question_text="What is your Python experience?",
                category="technical",
                difficulty_level="medium"
            ),
            Mock(
                id=str(uuid.uuid4()),
                question_text="How do you debug Python code?",
                category="technical",
                difficulty_level="easy"
            )
        ]
        mock_question_bank_service.get_questions_for_role.return_value = mock_questions
        
        # Act
        result = await hybrid_ai_service.generate_interview_questions(role, job_description, preferred_service)
        
        # Assert
        assert "questions" in result
        assert len(result["questions"]) == 2
        assert result["questions"][0] == "What is your Python experience?"
        assert result["questions"][1] == "How do you debug Python code?"
        assert result["service_used"] == "question_bank"
        assert "timestamp" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_interview_questions_ai_fallback(self, hybrid_ai_service, mock_question_bank_service):
        """Test generating questions with AI fallback when bank is empty."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        preferred_service = "openai"
        
        # Mock empty question bank
        mock_question_bank_service.get_questions_for_role.return_value = []
        
        # Mock AI service calls
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.return_value = {
                "questions": ["AI Generated Question 1", "AI Generated Question 2"],
                "service_used": "openai"
            }
            
            # Act
            result = await hybrid_ai_service.generate_interview_questions(role, job_description, preferred_service)
            
            # Assert
            assert "questions" in result
            assert len(result["questions"]) == 2
            assert result["questions"][0] == "AI Generated Question 1"
            assert result["questions"][1] == "AI Generated Question 2"
            assert result["service_used"] == "openai"
            assert "timestamp" in result
            
            # Verify AI service was called
            mock_ai_call.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_interview_questions_ai_fallback_with_storage(self, hybrid_ai_service, mock_question_bank_service):
        """Test generating questions with AI fallback and storing in question bank."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        preferred_service = "openai"
        
        # Mock empty question bank
        mock_question_bank_service.get_questions_for_role.return_value = []
        
        # Mock AI service calls
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.return_value = {
                "questions": ["AI Generated Question 1", "AI Generated Question 2"],
                "service_used": "openai"
            }
            
            # Act
            result = await hybrid_ai_service.generate_interview_questions(role, job_description, preferred_service)
            
            # Assert
            assert "questions" in result
            assert result["service_used"] == "openai"
            
            # Verify questions were stored in question bank
            mock_question_bank_service.store_generated_questions.assert_called_once()
            call_args = mock_question_bank_service.store_generated_questions.call_args
            assert call_args[0][0] == ["AI Generated Question 1", "AI Generated Question 2"]
            assert call_args[0][1] == role
            assert call_args[0][2] == job_description
            assert call_args[0][3] == "openai"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_answer(self, hybrid_ai_service):
        """Test analyzing an answer."""
        # Arrange
        job_description = "Looking for Python developer"
        question = "What is your Python experience?"
        answer = "I have 5 years of Python experience"
        preferred_service = "openai"
        
        # Mock AI service call
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.return_value = {
                "score": {"clarity": 8.5, "confidence": 7.8, "relevance": 9.0, "overall": 8.4},
                "missingKeywords": ["Django", "Flask"],
                "improvements": ["Provide more specific examples"],
                "service_used": "openai"
            }
            
            # Act
            result = await hybrid_ai_service.analyze_answer(job_description, question, answer, preferred_service)
            
            # Assert
            assert "score" in result
            assert result["score"]["overall"] == 8.4
            assert "missingKeywords" in result
            assert "improvements" in result
            assert result["service_used"] == "openai"
            assert "timestamp" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_available_services(self, hybrid_ai_service, mock_question_bank_service):
        """Test getting available AI services."""
        # Arrange
        with patch.object(hybrid_ai_service, '_check_service_availability') as mock_check:
            mock_check.return_value = {
                "openai": True,
                "anthropic": True,
                "ollama": False
            }
            
            # Act
            result = await hybrid_ai_service.get_available_services()
            
            # Assert
            assert "available_services" in result
            assert "openai" in result["available_services"]
            assert "anthropic" in result["available_services"]
            assert "ollama" not in result["available_services"]
            assert "question_bank_stats" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_models(self, hybrid_ai_service):
        """Test listing available models."""
        # Arrange
        service = "openai"
        
        # Mock AI service call
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.return_value = {
                "models": {
                    "openai": ["gpt-4", "gpt-3.5-turbo"],
                    "anthropic": ["claude-3-sonnet", "claude-3-haiku"]
                }
            }
            
            # Act
            result = await hybrid_ai_service.list_models(service)
            
            # Assert
            assert "models" in result
            assert "openai" in result["models"]
            assert "gpt-4" in result["models"]["openai"]
            assert "gpt-3.5-turbo" in result["models"]["openai"]
    
    @pytest.mark.unit
    def test_generate_prompt_hash(self, hybrid_ai_service):
        """Test generating prompt hash."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        
        # Act
        hash1 = hybrid_ai_service._generate_prompt_hash(role, job_description)
        hash2 = hybrid_ai_service._generate_prompt_hash(role, job_description)
        
        # Assert
        assert hash1 == hash2  # Same inputs should produce same hash
        assert len(hash1) > 0  # Hash should not be empty
    
    @pytest.mark.unit
    def test_generate_prompt_hash_different_inputs(self, hybrid_ai_service):
        """Test generating different hashes for different inputs."""
        # Arrange
        role1 = "Python Developer"
        job_description1 = "Looking for Python developer"
        role2 = "Java Developer"
        job_description2 = "Looking for Java developer"
        
        # Act
        hash1 = hybrid_ai_service._generate_prompt_hash(role1, job_description1)
        hash2 = hybrid_ai_service._generate_prompt_hash(role2, job_description2)
        
        # Assert
        assert hash1 != hash2  # Different inputs should produce different hashes
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_interview_questions_exception_handling(self, hybrid_ai_service, mock_question_bank_service):
        """Test exception handling in question generation."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        preferred_service = "openai"
        
        # Mock question bank service to raise exception
        mock_question_bank_service.get_questions_for_role.side_effect = Exception("Database error")
        
        # Mock AI service call
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.return_value = {
                "questions": ["AI Generated Question 1"],
                "service_used": "openai"
            }
            
            # Act
            result = await hybrid_ai_service.generate_interview_questions(role, job_description, preferred_service)
            
            # Assert
            assert "questions" in result
            assert result["questions"][0] == "AI Generated Question 1"
            assert result["service_used"] == "openai"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_answer_exception_handling(self, hybrid_ai_service):
        """Test exception handling in answer analysis."""
        # Arrange
        job_description = "Looking for Python developer"
        question = "What is your Python experience?"
        answer = "I have 5 years of Python experience"
        preferred_service = "openai"
        
        # Mock AI service call to raise exception
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.side_effect = Exception("AI service error")
            
            # Act & Assert
            with pytest.raises(Exception):
                await hybrid_ai_service.analyze_answer(job_description, question, answer, preferred_service)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_question_bank_stats(self, hybrid_ai_service, mock_question_bank_service):
        """Test getting question bank statistics."""
        # Arrange
        expected_stats = {
            "total_questions": 100,
            "questions_by_category": {"technical": 60, "behavioral": 30},
            "questions_by_difficulty": {"easy": 20, "medium": 50, "hard": 30}
        }
        mock_question_bank_service.get_question_bank_stats.return_value = expected_stats
        
        # Act
        result = hybrid_ai_service.get_question_bank_stats()
        
        # Assert
        assert result == expected_stats
        mock_question_bank_service.get_question_bank_stats.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_interview_questions_mixed_sources(self, hybrid_ai_service, mock_question_bank_service):
        """Test generating questions from both bank and AI."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        preferred_service = "openai"
        
        # Mock some questions from bank
        mock_questions = [
            Mock(
                id=str(uuid.uuid4()),
                question_text="What is your Python experience?",
                category="technical",
                difficulty_level="medium"
            )
        ]
        mock_question_bank_service.get_questions_for_role.return_value = mock_questions
        
        # Mock AI service call for additional questions
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            mock_ai_call.return_value = {
                "questions": ["AI Generated Question 1", "AI Generated Question 2"],
                "service_used": "openai"
            }
            
            # Act
            result = await hybrid_ai_service.generate_interview_questions(role, job_description, preferred_service)
            
            # Assert
            assert "questions" in result
            assert len(result["questions"]) == 3  # 1 from bank + 2 from AI
            assert result["questions"][0] == "What is your Python experience?"
            assert result["questions"][1] == "AI Generated Question 1"
            assert result["questions"][2] == "AI Generated Question 2"
            assert result["service_used"] == "openai"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_priority_fallback(self, hybrid_ai_service):
        """Test service priority and fallback mechanism."""
        # Arrange
        role = "Python Developer"
        job_description = "Looking for Python developer"
        preferred_service = "ollama"  # Unavailable service
        
        # Mock question bank service to return empty
        hybrid_ai_service.question_bank_service.get_questions_for_role.return_value = []
        
        # Mock AI service calls with fallback
        with patch.object(hybrid_ai_service, '_call_ai_service') as mock_ai_call:
            # First call fails (ollama unavailable)
            mock_ai_call.side_effect = [
                Exception("Service unavailable"),
                {"questions": ["Fallback Question"], "service_used": "openai"}
            ]
            
            # Act
            result = await hybrid_ai_service.generate_interview_questions(role, job_description, preferred_service)
            
            # Assert
            assert "questions" in result
            assert result["questions"][0] == "Fallback Question"
            assert result["service_used"] == "openai"
            assert mock_ai_call.call_count == 2  # Should try twice
