"""
Unit tests for ValidationService.

Tests the unified validation service including text, security, URL,
quality, file, and API key validation methods.
"""
import pytest
from io import BytesIO
from unittest.mock import MagicMock

from app.utils.validation import ValidationService
from app.models.schemas import FileType


class TestValidationService:
    """Test cases for ValidationService."""

    @pytest.fixture
    def validator(self):
        return ValidationService()

    @pytest.mark.unit
    def test_validate_text_length_valid(self, validator):
        """Test text length validation with valid length."""
        text = "a" * 50  # 50 chars, within 20-500
        assert validator.validate_text_length(text) is True
        assert validator.validate_text_length(text, min_length=10, max_length=100) is True

    @pytest.mark.unit
    def test_validate_text_length_too_short(self, validator):
        """Test text length validation with too short text."""
        assert validator.validate_text_length("short") is False

    @pytest.mark.unit
    def test_validate_text_length_too_long(self, validator):
        """Test text length validation with too long text."""
        assert validator.validate_text_length("a" * 600) is False

    @pytest.mark.unit
    def test_validate_word_count_valid(self, validator):
        """Test word count validation with valid count."""
        text = "one two three four five six"  # 6 words
        assert validator.validate_word_count(text, min_words=5, max_words=10) is True

    @pytest.mark.unit
    def test_validate_word_count_too_few(self, validator):
        """Test word count validation with too few words."""
        assert validator.validate_word_count("one two", min_words=5) is False

    @pytest.mark.unit
    def test_validate_word_count_too_many(self, validator):
        """Test word count validation with too many words."""
        text = " ".join(["word"] * 150)
        assert validator.validate_word_count(text, max_words=100) is False

    @pytest.mark.unit
    def test_validate_quality_valid(self, validator):
        """Test quality validation with valid text."""
        text = "This is a valid text with enough words and length for validation."
        is_valid, issues = validator.validate_quality(text)
        assert is_valid is True
        assert len(issues) == 0

    @pytest.mark.unit
    def test_validate_quality_invalid_length(self, validator):
        """Test quality validation with invalid length."""
        text = "short"
        is_valid, issues = validator.validate_quality(text)
        assert is_valid is False
        assert any("length" in i.lower() for i in issues)

    @pytest.mark.unit
    def test_validate_quality_invalid_word_count(self, validator):
        """Test quality validation with invalid word count."""
        text = "a" * 100  # 100 chars but only 1 word
        is_valid, issues = validator.validate_quality(text)
        assert is_valid is False
        assert any("word" in i.lower() for i in issues)

    @pytest.mark.unit
    def test_contains_patterns(self, validator):
        """Test contains_patterns finds substring matches."""
        assert validator.contains_patterns("Hello WORLD", ["world"]) is True
        assert validator.contains_patterns("Hello WORLD", ["foo"]) is False

    @pytest.mark.unit
    def test_contains_regex_patterns(self, validator):
        """Test contains_regex_patterns finds regex matches."""
        assert validator.contains_regex_patterns("select * from users", [r"\bselect\b"]) is True
        assert validator.contains_regex_patterns("normal text", [r"\bselect\b"]) is False

    @pytest.mark.unit
    def test_validate_security_safe_text(self, validator):
        """Test security validation with safe text."""
        is_safe, threats = validator.validate_security("This is normal safe text.")
        assert is_safe is True
        assert len(threats) == 0

    @pytest.mark.unit
    def test_validate_security_sql_injection(self, validator):
        """Test security validation detects SQL injection patterns."""
        is_safe, threats = validator.validate_security("union select * from users")
        assert is_safe is False
        assert any("sql" in t.lower() for t in threats)

    @pytest.mark.unit
    def test_validate_security_xss(self, validator):
        """Test security validation detects XSS patterns."""
        is_safe, threats = validator.validate_security("<script>alert('xss')</script>")
        assert is_safe is False
        assert any("xss" in t.lower() for t in threats)

    @pytest.mark.unit
    def test_validate_url_valid(self, validator):
        """Test URL validation with valid URLs."""
        assert validator.validate_url("https://example.com") is True
        assert validator.validate_url("http://sub.domain.co.uk/path") is True

    @pytest.mark.unit
    def test_validate_url_invalid(self, validator):
        """Test URL validation with invalid URLs."""
        assert validator.validate_url("not-a-url") is False
        assert validator.validate_url("") is False
        assert validator.validate_url("ftp://") is False

    @pytest.mark.unit
    def test_validate_url_exception_returns_false(self, validator):
        """Test validate_url returns False when urlparse raises."""
        assert validator.validate_url(None) is False

    @pytest.mark.unit
    def test_validate_file_type_valid(self, validator):
        """Test file type validation with valid extension."""
        mock_file = MagicMock()
        mock_file.filename = "document.pdf"

        is_valid, msg = validator.validate_file_type(mock_file, FileType.DOCUMENT)
        assert is_valid is True
        assert "Valid" in msg

    @pytest.mark.unit
    def test_validate_file_type_no_filename(self, validator):
        """Test file type validation with no filename."""
        mock_file = MagicMock()
        mock_file.filename = None

        is_valid, msg = validator.validate_file_type(mock_file, FileType.DOCUMENT)
        assert is_valid is False
        assert "No filename" in msg

    @pytest.mark.unit
    def test_validate_file_type_invalid_extension(self, validator):
        """Test file type validation with wrong extension."""
        mock_file = MagicMock()
        mock_file.filename = "image.exe"

        is_valid, msg = validator.validate_file_type(mock_file, FileType.IMAGE)
        assert is_valid is False
        assert "not allowed" in msg

    @pytest.mark.unit
    def test_validate_file_size_valid(self, validator):
        """Test file size validation within limits."""
        mock_file = MagicMock()
        mock_file.file = BytesIO(b"x" * 100)  # 100 bytes

        is_valid, msg = validator.validate_file_size(mock_file, FileType.DOCUMENT)
        assert is_valid is True
        assert "Valid" in msg

    @pytest.mark.unit
    def test_validate_file_size_no_content(self, validator):
        """Test file size validation with no file content."""
        mock_file = MagicMock()
        mock_file.file = None

        is_valid, msg = validator.validate_file_size(mock_file, FileType.DOCUMENT)
        assert is_valid is False
        assert "No file content" in msg

    @pytest.mark.unit
    def test_validate_file_size_exceeds_limit(self, validator):
        """Test file size validation when file exceeds limit."""
        mock_file = MagicMock()
        # IMAGE limit is 10MB, create 11MB
        mock_file.file = BytesIO(b"x" * (11 * 1024 * 1024))

        is_valid, msg = validator.validate_file_size(mock_file, FileType.IMAGE)
        assert is_valid is False
        assert "exceeds" in msg.lower()

    @pytest.mark.unit
    def test_validate_file_content_safe(self, validator):
        """Test file content validation with safe content."""
        mock_file = MagicMock()
        mock_file.file = BytesIO(b"Normal safe text content for validation.")

        is_valid, msg = validator.validate_file_content(mock_file)
        assert is_valid is True
        assert "safe" in msg.lower()

    @pytest.mark.unit
    def test_validate_file_content_malicious(self, validator):
        """Test file content validation detects malicious content."""
        mock_file = MagicMock()
        mock_file.file = BytesIO(b"<script>alert('xss')</script>")

        is_valid, msg = validator.validate_file_content(mock_file)
        assert is_valid is False
        assert "validation failed" in msg.lower() or "xss" in msg.lower()

    @pytest.mark.unit
    def test_validate_api_key_empty(self, validator):
        """Test API key validation with empty key."""
        is_valid, msg = validator.validate_api_key("", "openai")
        assert is_valid is False
        assert "required" in msg.lower()

    @pytest.mark.unit
    def test_validate_api_key_openai_valid(self, validator):
        """Test OpenAI API key validation with valid format."""
        is_valid, msg = validator.validate_api_key("sk-" + "x" * 25, "openai")
        assert is_valid is True

    @pytest.mark.unit
    def test_validate_api_key_openai_invalid_prefix(self, validator):
        """Test OpenAI API key validation with wrong prefix."""
        is_valid, msg = validator.validate_api_key("invalid-prefix-key", "openai")
        assert is_valid is False
        assert "format" in msg.lower() or "start" in msg.lower()

    @pytest.mark.unit
    def test_validate_api_key_openai_too_short(self, validator):
        """Test OpenAI API key validation with too short key."""
        is_valid, msg = validator.validate_api_key("sk-123", "openai")
        assert is_valid is False
        assert "short" in msg.lower()

    @pytest.mark.unit
    def test_validate_model_valid(self, validator):
        """Test model validation with valid model."""
        is_valid, msg = validator.validate_model("gpt-4", "openai")
        assert is_valid is True

    @pytest.mark.unit
    def test_validate_model_invalid(self, validator):
        """Test model validation with invalid model."""
        is_valid, msg = validator.validate_model("invalid-model", "openai")
        assert is_valid is False
        assert "valid" in msg.lower()

    @pytest.mark.unit
    def test_validate_file_content_no_content(self, validator):
        """Test file content validation with no file content."""
        mock_file = MagicMock()
        mock_file.file = None

        is_valid, msg = validator.validate_file_content(mock_file)
        assert is_valid is False
        assert "No file content" in msg

    @pytest.mark.unit
    def test_validate_file_valid(self, validator):
        """Test comprehensive file validation with valid file."""
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.file = BytesIO(b"Safe PDF-like content for testing.")

        is_valid, errors = validator.validate_file(mock_file, FileType.DOCUMENT)
        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.unit
    def test_validate_file_invalid_type(self, validator):
        """Test comprehensive file validation fails on wrong type."""
        mock_file = MagicMock()
        mock_file.filename = "test.exe"
        mock_file.file = BytesIO(b"content")

        is_valid, errors = validator.validate_file(mock_file, FileType.IMAGE)
        assert is_valid is False
        assert any("not allowed" in e for e in errors)

    @pytest.mark.unit
    def test_validate_file_invalid_size(self, validator):
        """Test comprehensive file validation fails when file exceeds size limit."""
        mock_file = MagicMock()
        mock_file.filename = "large.pdf"
        mock_file.file = BytesIO(b"x" * (11 * 1024 * 1024))  # 11MB, exceeds IMAGE 10MB

        is_valid, errors = validator.validate_file(mock_file, FileType.IMAGE)
        assert is_valid is False
        assert any("exceeds" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_validate_file_invalid_content(self, validator):
        """Test comprehensive file validation fails when content is malicious."""
        mock_file = MagicMock()
        mock_file.filename = "malicious.pdf"
        mock_file.file = BytesIO(b"<script>alert(1)</script>")

        is_valid, errors = validator.validate_file(mock_file, FileType.DOCUMENT)
        assert is_valid is False
        assert any("validation failed" in e.lower() or "content" in e.lower() for e in errors)

    @pytest.mark.unit
    def test_validate_api_key_unknown_service(self, validator):
        """Test API key validation for unknown service returns True (not validated)."""
        is_valid, msg = validator.validate_api_key("any-key", "unknown_service")
        assert is_valid is True
        assert "not validated" in msg.lower()

    @pytest.mark.unit
    def test_validate_model_unknown_service(self, validator):
        """Test model validation for unknown service returns True."""
        is_valid, msg = validator.validate_model("any-model", "unknown_service")
        assert is_valid is True

    @pytest.mark.unit
    def test_validate_numeric_value_valid(self, validator):
        """Test validate_numeric_value with value in range."""
        is_valid, msg = validator.validate_numeric_value(5.0, min_val=0, max_val=10)
        assert is_valid is True
        assert "Valid" in msg

    @pytest.mark.unit
    def test_validate_numeric_value_below_min(self, validator):
        """Test validate_numeric_value with value below min."""
        is_valid, msg = validator.validate_numeric_value(0, min_val=1, max_val=10)
        assert is_valid is False
        assert ">=" in msg

    @pytest.mark.unit
    def test_validate_numeric_value_above_max(self, validator):
        """Test validate_numeric_value with value above max."""
        is_valid, msg = validator.validate_numeric_value(15, min_val=0, max_val=10)
        assert is_valid is False
        assert "<=" in msg

    @pytest.mark.unit
    def test_validate_configuration_returns_tuple(self, validator):
        """Test validate_configuration returns errors and warnings lists."""
        errors, warnings = validator.validate_configuration()
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
