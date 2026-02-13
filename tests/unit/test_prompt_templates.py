"""
Unit tests for PromptTemplates.

Tests the centralized prompt templates used by AI services.
"""
import pytest

from app.utils.prompt_templates import PromptTemplates


class TestPromptTemplates:
    """Test cases for PromptTemplates."""

    @pytest.mark.unit
    def test_question_generation_system_constant_exists(self):
        """Verify QUESTION_GENERATION_SYSTEM constant is defined."""
        assert PromptTemplates.QUESTION_GENERATION_SYSTEM
        assert "interview" in PromptTemplates.QUESTION_GENERATION_SYSTEM.lower()

    @pytest.mark.unit
    def test_analysis_system_constant_exists(self):
        """Verify ANALYSIS_SYSTEM constant is defined."""
        assert PromptTemplates.ANALYSIS_SYSTEM
        assert "analyze" in PromptTemplates.ANALYSIS_SYSTEM.lower()

    @pytest.mark.unit
    def test_get_question_generation_prompt_includes_role_and_jd(self):
        """Verify prompt includes role and job description."""
        prompt = PromptTemplates.get_question_generation_prompt(
            role="Python Developer",
            job_description="We need a senior Python developer with FastAPI experience."
        )

        assert "Python Developer" in prompt
        assert "We need a senior Python developer with FastAPI experience." in prompt
        assert "10 relevant interview questions" in prompt

    @pytest.mark.unit
    def test_get_analysis_prompt_includes_all_inputs(self):
        """Verify analysis prompt includes job description, question, and answer."""
        prompt = PromptTemplates.get_analysis_prompt(
            job_description="Senior engineer role",
            question="Tell me about your experience",
            answer="I have 5 years of experience."
        )

        assert "Senior engineer role" in prompt
        assert "Tell me about your experience" in prompt
        assert "I have 5 years of experience." in prompt
        assert "clarity" in prompt.lower()
        assert "confidence" in prompt.lower()
