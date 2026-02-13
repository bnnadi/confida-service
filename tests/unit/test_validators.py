"""
Unit tests for InputValidator.

Tests input validation utilities for API endpoints.
"""
import pytest
from fastapi import HTTPException

from app.utils.validators import (
    InputValidator,
    AIServiceType,
    LanguageCode,
    create_service_query_param,
    create_language_query_param,
)


class TestInputValidator:
    """Test cases for InputValidator."""

    @pytest.mark.unit
    def test_validate_service_valid(self):
        """Test validate_service with valid service names."""
        assert InputValidator.validate_service("openai") == "openai"
        assert InputValidator.validate_service("OLLAMA") == "ollama"
        assert InputValidator.validate_service("  anthropic  ") == "anthropic"

    @pytest.mark.unit
    def test_validate_service_none(self):
        """Test validate_service with None returns None."""
        assert InputValidator.validate_service(None) is None

    @pytest.mark.unit
    def test_validate_service_invalid(self):
        """Test validate_service with invalid service raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_service("invalid_service")
        assert exc_info.value.status_code == 400
        assert "Invalid service" in str(exc_info.value.detail)

    @pytest.mark.unit
    def test_validate_language_valid(self):
        """Test validate_language with valid language codes."""
        assert InputValidator.validate_language("en-US") == "en-US"
        assert InputValidator.validate_language("fr-FR") == "fr-FR"

    @pytest.mark.unit
    def test_validate_language_none_returns_default(self):
        """Test validate_language with None returns en-US."""
        assert InputValidator.validate_language(None) == "en-US"

    @pytest.mark.unit
    def test_validate_language_invalid(self):
        """Test validate_language with invalid code raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_language("invalid-lang")
        assert exc_info.value.status_code == 400
        assert "Invalid language" in str(exc_info.value.detail)

    @pytest.mark.unit
    def test_validate_text_length_valid(self):
        """Test validate_text_length with valid text."""
        text = "Valid role name"
        result = InputValidator.validate_text_length(
            text, "role", min_length=5, max_length=200
        )
        assert result == text

    @pytest.mark.unit
    def test_validate_text_length_too_short(self):
        """Test validate_text_length with too short text raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_text_length("ab", "role", min_length=5)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_text_length_too_long(self):
        """Test validate_text_length with too long text raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_text_length(
                "a" * 300, "role", max_length=200
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_text_length_non_string(self):
        """Test validate_text_length with non-string raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_text_length(123, "role")
        assert exc_info.value.status_code == 400
        assert "string" in str(exc_info.value.detail).lower()

    @pytest.mark.unit
    def test_validate_role(self):
        """Test validate_role with valid input."""
        result = InputValidator.validate_role("Software Engineer")
        assert result == "Software Engineer"

    @pytest.mark.unit
    def test_validate_job_description(self):
        """Test validate_job_description with valid input."""
        desc = "A" * 50  # At least 10 chars
        result = InputValidator.validate_job_description(desc)
        assert result == desc

    @pytest.mark.unit
    def test_validate_question(self):
        """Test validate_question with valid input."""
        result = InputValidator.validate_question("What is your experience?")
        assert "experience" in result

    @pytest.mark.unit
    def test_validate_answer(self):
        """Test validate_answer with valid input."""
        result = InputValidator.validate_answer("My answer")
        assert result == "My answer"

    @pytest.mark.unit
    def test_validate_question_id_valid(self):
        """Test validate_question_id with valid int."""
        assert InputValidator.validate_question_id(42) == 42

    @pytest.mark.unit
    def test_validate_question_id_invalid_type(self):
        """Test validate_question_id with non-int raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_question_id("not_an_int")
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_question_id_negative(self):
        """Test validate_question_id with negative raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_question_id(-1)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_question_id_zero(self):
        """Test validate_question_id with zero raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_question_id(0)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_session_id_valid(self):
        """Test validate_session_id with valid int."""
        assert InputValidator.validate_session_id(1) == 1

    @pytest.mark.unit
    def test_validate_session_id_invalid(self):
        """Test validate_session_id with invalid input raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_session_id("invalid")
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_session_id_zero_or_negative(self):
        """Test validate_session_id with zero or negative raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_session_id(0)
        assert exc_info.value.status_code == 400
        with pytest.raises(HTTPException):
            InputValidator.validate_session_id(-5)

    @pytest.mark.unit
    def test_validate_pagination_params_valid(self):
        """Test validate_pagination_params with valid values."""
        result = InputValidator.validate_pagination_params(limit=10, offset=0)
        assert result["limit"] == 10
        assert result["offset"] == 0

    @pytest.mark.unit
    def test_validate_pagination_params_defaults(self):
        """Test validate_pagination_params with None uses defaults."""
        result = InputValidator.validate_pagination_params()
        assert "limit" in result
        assert "offset" in result

    @pytest.mark.unit
    def test_validate_pagination_params_invalid_limit(self):
        """Test validate_pagination_params with invalid limit raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_pagination_params(limit=-1)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_pagination_params_limit_too_high(self):
        """Test validate_pagination_params with limit > 100 raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_pagination_params(limit=150)
        assert exc_info.value.status_code == 400
        assert "100" in str(exc_info.value.detail)

    @pytest.mark.unit
    def test_validate_pagination_params_invalid_offset(self):
        """Test validate_pagination_params with negative offset raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_pagination_params(offset=-5)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_audio_file_size_valid(self):
        """Test validate_audio_file_size with valid size does not raise."""
        InputValidator.validate_audio_file_size(1024 * 1024, max_size_mb=10)  # 1MB

    @pytest.mark.unit
    def test_validate_audio_file_size_too_large(self):
        """Test validate_audio_file_size with oversized file raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_audio_file_size(20 * 1024 * 1024, max_size_mb=10)
        assert exc_info.value.status_code == 400
        assert "large" in str(exc_info.value.detail).lower()

    @pytest.mark.unit
    def test_validate_audio_file_type_valid(self):
        """Test validate_audio_file_type with valid extension."""
        result = InputValidator.validate_audio_file_type("audio.mp3")
        assert result == "mp3"

    @pytest.mark.unit
    def test_validate_audio_file_type_invalid(self):
        """Test validate_audio_file_type with invalid extension raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_audio_file_type("file.exe")
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_audio_file_type_empty_filename(self):
        """Test validate_audio_file_type with empty filename raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_audio_file_type("")
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_audio_file_type_custom_extensions(self):
        """Test validate_audio_file_type with custom allowed_extensions."""
        result = InputValidator.validate_audio_file_type(
            "audio.wav", allowed_extensions=[".wav", ".ogg"]
        )
        assert result == "wav"

    @pytest.mark.unit
    def test_validate_audio_file_type_invalid_with_custom_extensions(self):
        """Test validate_audio_file_type rejects extension not in custom list."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_audio_file_type(
                "audio.mp3", allowed_extensions=[".wav", ".ogg"]
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_validate_audio_file_type_filename_without_extension(self):
        """Test validate_audio_file_type with filename missing extension raises."""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_audio_file_type("noextension")
        assert exc_info.value.status_code == 400


class TestValidatorQueryParams:
    """Test query param factory functions."""

    @pytest.mark.unit
    def test_create_service_query_param(self):
        """Test create_service_query_param returns Query with description."""
        param = create_service_query_param()
        assert param is not None
        assert "openai" in str(param.description).lower() or "ollama" in str(param.description).lower()

    @pytest.mark.unit
    def test_create_language_query_param(self):
        """Test create_language_query_param returns Query with default."""
        param = create_language_query_param()
        assert param is not None
        assert param.default == "en-US"
