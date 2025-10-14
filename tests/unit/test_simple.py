"""
Simple tests to verify the testing suite is working.

These tests are designed to pass quickly and verify the basic
testing infrastructure is functioning correctly.
"""
import pytest
from unittest.mock import Mock


class TestSimple:
    """Simple test cases to verify testing infrastructure."""
    
    @pytest.mark.unit
    def test_basic_math(self):
        """Test basic mathematical operations."""
        assert 2 + 2 == 4
        assert 3 * 3 == 9
        assert 10 / 2 == 5
    
    @pytest.mark.unit
    def test_string_operations(self):
        """Test basic string operations."""
        text = "Hello, World!"
        assert len(text) == 13
        assert "Hello" in text
        assert text.upper() == "HELLO, WORLD!"
    
    @pytest.mark.unit
    def test_list_operations(self):
        """Test basic list operations."""
        numbers = [1, 2, 3, 4, 5]
        assert len(numbers) == 5
        assert sum(numbers) == 15
        assert max(numbers) == 5
        assert min(numbers) == 1
    
    @pytest.mark.unit
    def test_dict_operations(self):
        """Test basic dictionary operations."""
        data = {"name": "John", "age": 30, "city": "New York"}
        assert "name" in data
        assert data["age"] == 30
        assert len(data) == 3
    
    @pytest.mark.unit
    def test_mock_functionality(self):
        """Test that mocking works correctly."""
        mock_obj = Mock()
        mock_obj.method.return_value = "mocked result"
        
        result = mock_obj.method()
        assert result == "mocked result"
        mock_obj.method.assert_called_once()
    
    @pytest.mark.unit
    def test_exception_handling(self):
        """Test exception handling."""
        with pytest.raises(ValueError):
            raise ValueError("Test exception")
        
        with pytest.raises(ZeroDivisionError):
            1 / 0
    
    @pytest.mark.unit
    def test_async_functionality(self):
        """Test async functionality."""
        import asyncio
        
        async def async_function():
            return "async result"
        
        async def test_async():
            result = await async_function()
            assert result == "async result"
        
        # Run the async test
        asyncio.run(test_async())
    
    @pytest.mark.unit
    def test_environment_variables(self):
        """Test environment variable handling."""
        import os
        
        # Set a test environment variable
        os.environ["TEST_VAR"] = "test_value"
        
        # Test that it can be read
        assert os.environ.get("TEST_VAR") == "test_value"
        
        # Clean up
        del os.environ["TEST_VAR"]
    
    @pytest.mark.unit
    def test_file_operations(self):
        """Test basic file operations."""
        import tempfile
        import os
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # Test that the file exists and has content
            assert os.path.exists(temp_file)
            with open(temp_file, 'r') as f:
                content = f.read()
                assert content == "test content"
        finally:
            # Clean up
            os.unlink(temp_file)
    
    @pytest.mark.unit
    def test_json_operations(self):
        """Test JSON operations."""
        import json
        
        data = {"name": "John", "age": 30}
        json_string = json.dumps(data)
        parsed_data = json.loads(json_string)
        
        assert parsed_data == data
        assert json_string == '{"name": "John", "age": 30}'
