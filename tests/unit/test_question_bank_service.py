"""
Unit tests for Question Bank Service.

Tests the service layer logic for question bank operations.
"""
import pytest
from app.services.question_bank_service import QuestionBankService
from app.models.question_requests import QuestionCreateRequest, QuestionUpdateRequest, QuestionFilters
from app.database.models import Question
import uuid


class TestQuestionBankService:
    """Test cases for QuestionBankService."""
    
    @pytest.mark.unit
    def test_create_question(self, db_session):
        """Test creating a question."""
        service = QuestionBankService(db_session)
        unique_text = f"What is Python? {uuid.uuid4().hex[:8]}"
        question_data = QuestionCreateRequest(
            question_text=unique_text,
            category="technical",
            difficulty_level="medium",
            compatible_roles=["Python Developer"],
            required_skills=["Python"]
        )
        
        question = service.create_question(question_data)
        
        assert question is not None
        assert question.question_text == question_data.question_text
        assert question.category == question_data.category
        assert question.difficulty_level == question_data.difficulty_level
        assert str(question.id)  # Should have an ID
    
    @pytest.mark.unit
    def test_create_question_duplicate(self, db_session):
        """Test creating duplicate question raises error."""
        service = QuestionBankService(db_session)
        unique_text = f"What is Python? {uuid.uuid4().hex[:8]}"
        question_data = QuestionCreateRequest(
            question_text=unique_text,
            category="technical"
        )
        
        # Create first question
        service.create_question(question_data)
        db_session.commit()
        
        # Try to create duplicate (same text)
        with pytest.raises(ValueError, match="already exists"):
            service.create_question(question_data)
    
    @pytest.mark.unit
    def test_get_question_by_id(self, db_session, sample_question):
        """Test getting question by ID."""
        service = QuestionBankService(db_session)
        question_id = str(sample_question.id)
        
        result = service.get_question_by_id(question_id)
        
        assert result is not None
        assert result.id == sample_question.id
        assert result.question_text == sample_question.question_text
    
    @pytest.mark.unit
    def test_get_question_by_id_not_found(self, db_session):
        """Test getting non-existent question."""
        service = QuestionBankService(db_session)
        fake_id = str(uuid.uuid4())
        
        result = service.get_question_by_id(fake_id)
        
        assert result is None
    
    @pytest.mark.unit
    def test_get_question_by_id_invalid_format(self, db_session):
        """Test getting question with invalid ID format."""
        service = QuestionBankService(db_session)
        
        result = service.get_question_by_id("invalid-id")
        
        assert result is None
    
    @pytest.mark.unit
    def test_get_questions(self, db_session, sample_question):
        """Test getting list of questions."""
        service = QuestionBankService(db_session)
        
        questions = service.get_questions(limit=10)
        
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert any(q.id == sample_question.id for q in questions)
    
    @pytest.mark.unit
    def test_get_questions_with_category_filter(self, db_session):
        """Test getting questions filtered by category."""
        service = QuestionBankService(db_session)
        
        # Create questions in different categories
        q1 = Question(
            question_text="Tech question",
            category="technical",
            difficulty_level="medium"
        )
        q2 = Question(
            question_text="Behavioral question",
            category="behavioral",
            difficulty_level="easy"
        )
        db_session.add_all([q1, q2])
        db_session.commit()
        
        questions = service.get_questions(category="technical")
        
        assert all(q.category == "technical" for q in questions)
    
    @pytest.mark.unit
    def test_get_questions_with_pagination(self, db_session):
        """Test getting questions with pagination."""
        service = QuestionBankService(db_session)
        
        # Create multiple questions with unique category to isolate from other tests
        unique_cat = f"paginate-{uuid.uuid4().hex[:8]}"
        for i in range(5):
            question = Question(
                question_text=f"Pagination question {i}",
                category=unique_cat,
                difficulty_level="easy"
            )
            db_session.add(question)
        db_session.commit()
        
        # Get first page (filter by category for deterministic order)
        page1 = service.get_questions(category=unique_cat, limit=2, offset=0)
        assert len(page1) == 2
        
        # Get second page
        page2 = service.get_questions(category=unique_cat, limit=2, offset=2)
        assert len(page2) == 2
        assert page1[0].id != page2[0].id
    
    @pytest.mark.unit
    def test_search_questions(self, db_session):
        """Test searching questions."""
        service = QuestionBankService(db_session)
        
        # Create a question with specific text
        question = Question(
            question_text="Python programming language",
            category="technical",
            difficulty_level="medium"
        )
        db_session.add(question)
        db_session.commit()
        
        results = service.search_questions("Python")
        
        assert len(results) > 0
        assert any("Python" in q.question_text for q in results)
    
    @pytest.mark.unit
    def test_update_question(self, db_session, sample_question):
        """Test updating a question."""
        service = QuestionBankService(db_session)
        question_id = str(sample_question.id)
        
        update_data = QuestionUpdateRequest(
            category="updated_category",
            difficulty_level="hard"
        )
        
        updated = service.update_question(question_id, update_data)
        
        assert updated is not None
        assert updated.category == "updated_category"
        assert updated.difficulty_level == "hard"
        assert updated.question_text == sample_question.question_text  # Unchanged
    
    @pytest.mark.unit
    def test_update_question_not_found(self, db_session):
        """Test updating non-existent question."""
        service = QuestionBankService(db_session)
        fake_id = str(uuid.uuid4())
        
        update_data = QuestionUpdateRequest(category="new_category")
        result = service.update_question(fake_id, update_data)
        
        assert result is None
    
    @pytest.mark.unit
    def test_delete_question(self, db_session):
        """Test deleting a question."""
        service = QuestionBankService(db_session)
        
        # Create a question
        question = Question(
            question_text="Question to delete",
            category="test",
            difficulty_level="easy"
        )
        db_session.add(question)
        db_session.commit()
        
        question_id = str(question.id)
        result = service.delete_question(question_id)
        
        assert result is True
        
        # Verify it's deleted
        deleted = service.get_question_by_id(question_id)
        assert deleted is None
    
    @pytest.mark.unit
    def test_delete_question_not_found(self, db_session):
        """Test deleting non-existent question."""
        service = QuestionBankService(db_session)
        fake_id = str(uuid.uuid4())
        
        result = service.delete_question(fake_id)
        
        assert result is False
    
    @pytest.mark.unit
    def test_get_question_suggestions(self, db_session):
        """Test getting question suggestions."""
        service = QuestionBankService(db_session)
        
        # Create questions with compatible roles
        question = Question(
            question_text="Python question",
            category="python",
            difficulty_level="medium",
            compatible_roles=["Python Developer"]
        )
        db_session.add(question)
        db_session.commit()
        
        suggestions = service.get_question_suggestions(
            role="Python Developer",
            job_description="Looking for Python developer",
            limit=5
        )
        
        assert isinstance(suggestions, list)
    
    @pytest.mark.unit
    def test_bulk_import_questions(self, db_session):
        """Test bulk importing questions."""
        service = QuestionBankService(db_session)
        
        # Use unique text to avoid collisions with other tests
        unique_prefix = uuid.uuid4().hex[:8]
        questions_data = [
            QuestionCreateRequest(
                question_text=f"Bulk question {i} {unique_prefix}",
                category="test",
                difficulty_level="easy"
            )
            for i in range(3)
        ]
        
        result = service.bulk_import_questions(questions_data)
        
        assert result["imported"] == 3
        assert result["failed"] == 0
        assert len(result["errors"]) == 0
    
    @pytest.mark.unit
    def test_bulk_import_with_duplicates(self, db_session):
        """Test bulk import with duplicate questions."""
        service = QuestionBankService(db_session)
        
        # Create existing question
        existing = Question(
            question_text="Existing question",
            category="test",
            difficulty_level="easy"
        )
        db_session.add(existing)
        db_session.commit()
        
        questions_data = [
            QuestionCreateRequest(
                question_text="Existing question",  # Duplicate
                category="test",
                difficulty_level="easy"
            ),
            QuestionCreateRequest(
                question_text="New question",
                category="test",
                difficulty_level="easy"
            )
        ]
        
        result = service.bulk_import_questions(questions_data)
        
        assert result["imported"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

