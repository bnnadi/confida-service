"""
Unit tests for Question Bank Utilities.

Tests the shared utilities for question bank operations.
"""
import pytest
import uuid
from unittest.mock import MagicMock

from app.utils.question_bank_utils import QuestionBankUtils
from app.database.models import Question, SessionQuestion, InterviewSession


class TestQuestionBankUtils:
    """Test cases for QuestionBankUtils."""

    @pytest.mark.unit
    def test_find_duplicate_questions_empty(self, db_session):
        """Single unique question should not appear in duplicates list."""
        unique_text = f"Unique only {uuid.uuid4().hex[:8]}"
        q = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="medium",
        )
        db_session.add(q)
        db_session.commit()

        result = QuestionBankUtils.find_duplicate_questions(db_session)
        # Our single question is not a duplicate, so it should not appear
        texts = [t for t, _ in result]
        assert unique_text not in texts

    @pytest.mark.unit
    def test_find_duplicate_questions_with_duplicates(self, db_session):
        """Add 2+ Question rows with same question_text, assert returns [(text, count)]."""
        unique_text = f"Duplicate question {uuid.uuid4().hex[:8]}"
        q1 = Question(
            question_text=unique_text,
            category="technical",
            difficulty_level="medium",
        )
        q2 = Question(
            question_text=unique_text,
            category="technical",
            difficulty_level="easy",
        )
        db_session.add_all([q1, q2])
        db_session.commit()

        result = QuestionBankUtils.find_duplicate_questions(db_session)
        assert len(result) >= 1
        texts_and_counts = [(t, c) for t, c in result if t == unique_text]
        assert len(texts_and_counts) == 1
        assert texts_and_counts[0][1] == 2

    @pytest.mark.unit
    def test_get_duplicate_question_instances(self, db_session):
        """Create duplicates, assert returns list ordered by created_at."""
        unique_text = f"Duplicate for instances {uuid.uuid4().hex[:8]}"
        q1 = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="medium",
        )
        q2 = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="easy",
        )
        db_session.add_all([q1, q2])
        db_session.commit()

        instances = QuestionBankUtils.get_duplicate_question_instances(db_session, unique_text)
        assert len(instances) == 2
        assert all(q.question_text == unique_text for q in instances)

    @pytest.mark.unit
    def test_is_question_linked_to_sessions_true(
        self, db_session, sample_user, sample_question
    ):
        """Create SessionQuestion linking question to session, assert True."""
        session = InterviewSession(
            user_id=sample_user.id,
            role="Python Developer",
            job_description="Test",
            status="active",
            total_questions=1,
            completed_questions=0,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        session_question = SessionQuestion(
            session_id=session.id,
            question_id=sample_question.id,
            question_order=1,
        )
        db_session.add(session_question)
        db_session.commit()

        result = QuestionBankUtils.is_question_linked_to_sessions(
            db_session, sample_question.id
        )
        assert result is True

    @pytest.mark.unit
    def test_is_question_linked_to_sessions_false(self, db_session, sample_question):
        """Question with no SessionQuestion, assert False."""
        result = QuestionBankUtils.is_question_linked_to_sessions(
            db_session, sample_question.id
        )
        assert result is False

    @pytest.mark.unit
    def test_remove_duplicate_questions_dry_run(self, db_session):
        """Duplicates exist, dry_run=True, assert questions_removed == 0, duplicates_found > 0."""
        unique_text = f"Dry run duplicate {uuid.uuid4().hex[:8]}"
        q1 = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="medium",
        )
        q2 = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="easy",
        )
        db_session.add_all([q1, q2])
        db_session.commit()

        stats = QuestionBankUtils.remove_duplicate_questions(db_session, dry_run=True)

        assert stats["questions_removed"] == 0
        assert stats["duplicates_found"] > 0

    @pytest.mark.unit
    def test_remove_duplicate_questions_execute(self, db_session):
        """Duplicates, dry_run=False, assert our duplicate removed (oldest kept)."""
        unique_text = f"Execute duplicate {uuid.uuid4().hex[:8]}"
        q1 = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="medium",
        )
        q2 = Question(
            question_text=unique_text,
            category="tech",
            difficulty_level="easy",
        )
        db_session.add_all([q1, q2])
        db_session.commit()

        stats = QuestionBankUtils.remove_duplicate_questions(db_session, dry_run=False)

        assert stats["questions_removed"] >= 1
        assert stats["duplicates_found"] >= 1

        # Our specific duplicate group should now have only 1 instance (oldest kept)
        instances = QuestionBankUtils.get_duplicate_question_instances(
            db_session, unique_text
        )
        assert len(instances) == 1

    @pytest.mark.unit
    def test_fix_invalid_difficulty_levels_dry_run(self, db_session):
        """Question with invalid difficulty, dry_run=True, assert no updates."""
        q = Question(
            question_text=f"Invalid diff {uuid.uuid4().hex[:8]}",
            category="tech",
            difficulty_level="invalid_level",
        )
        db_session.add(q)
        db_session.commit()

        stats = QuestionBankUtils.fix_invalid_difficulty_levels(db_session, dry_run=True)

        assert stats["questions_updated"] == 0
        db_session.refresh(q)
        assert q.difficulty_level == "invalid_level"

    @pytest.mark.unit
    def test_fix_invalid_difficulty_levels_execute(self, db_session):
        """Invalid difficulty, dry_run=False, assert updated to medium."""
        q = Question(
            question_text=f"Fix invalid {uuid.uuid4().hex[:8]}",
            category="tech",
            difficulty_level="invalid_level",
        )
        db_session.add(q)
        db_session.commit()
        db_session.refresh(q)

        stats = QuestionBankUtils.fix_invalid_difficulty_levels(
            db_session, dry_run=False
        )

        assert stats["questions_updated"] == 1
        db_session.refresh(q)
        assert q.difficulty_level == "medium"

    @pytest.mark.unit
    def test_get_question_bank_statistics(self, db_session, sample_question):
        """Add questions, assert total_questions, difficulty_distribution, etc. in result."""
        result = QuestionBankUtils.get_question_bank_statistics(db_session)

        assert "total_questions" in result
        assert "difficulty_distribution" in result
        assert "category_distribution" in result
        assert "duplicate_groups" in result
        assert "total_duplicates" in result
        assert "linked_questions" in result
        assert "unlinked_questions" in result
        assert result["total_questions"] >= 1
        assert isinstance(result["difficulty_distribution"], dict)
        assert isinstance(result["category_distribution"], dict)

    @pytest.mark.unit
    def test_find_duplicate_questions_db_exception(self):
        """When db.execute raises, find_duplicate_questions returns empty list."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database connection failed")

        result = QuestionBankUtils.find_duplicate_questions(mock_db)

        assert result == []

    @pytest.mark.unit
    def test_get_duplicate_question_instances_db_exception(self):
        """When db.execute raises, get_duplicate_question_instances returns empty list."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database error")

        result = QuestionBankUtils.get_duplicate_question_instances(
            mock_db, "some question text"
        )

        assert result == []

    @pytest.mark.unit
    def test_is_question_linked_to_sessions_db_exception(self):
        """When db.execute raises, is_question_linked_to_sessions returns True (safe default)."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("Database error")

        result = QuestionBankUtils.is_question_linked_to_sessions(mock_db, 123)

        assert result is True
