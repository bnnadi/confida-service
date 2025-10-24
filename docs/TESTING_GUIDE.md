# Confida Testing Guide

This guide provides comprehensive documentation for the Confida testing suite, including how to run tests, understand test coverage, and contribute to the testing framework.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Types](#test-types)
5. [Test Coverage](#test-coverage)
6. [CI/CD Integration](#cicd-integration)
7. [Writing Tests](#writing-tests)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

## Overview

The Confida testing suite provides comprehensive coverage of the application with multiple test types:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions and API endpoints
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test system performance and scalability
- **Security Tests**: Test security vulnerabilities and best practices

### Test Framework

- **pytest**: Primary testing framework
- **FastAPI TestClient**: API endpoint testing
- **SQLAlchemy**: Database testing with test fixtures
- **pytest-cov**: Code coverage reporting
- **pytest-asyncio**: Async test support

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Global test configuration and fixtures
├── unit/                       # Unit tests
│   ├── test_question_bank_service.py
│   ├── test_hybrid_ai_service.py
│   └── test_database_models.py
├── integration/                # Integration tests
│   ├── test_interview_endpoints.py
│   └── test_session_endpoints.py
├── e2e/                       # End-to-end tests
│   └── test_complete_interview_flow.py
├── fixtures/                  # Test fixtures and utilities
├── utils/                     # Test utilities and helpers
└── performance/               # Performance tests
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test type
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
```

### Using the Test Runner Script

```bash
# Run all tests with coverage
python scripts/run_tests.py --type all --coverage

# Run unit tests only
python scripts/run_tests.py --type unit

# Run tests with specific marker
python scripts/run_tests.py --marker performance

# Run specific test file
python scripts/run_tests.py --test tests/unit/test_question_bank_service.py

# Run with verbose output
python scripts/run_tests.py --type all --verbose
```

### Test Markers

```bash
# Run unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# Run end-to-end tests
pytest -m e2e

# Run performance tests
pytest -m performance

# Run security tests
pytest -m security

# Run slow tests
pytest -m slow

# Run database tests
pytest -m database
```

## Test Types

### Unit Tests

Unit tests focus on testing individual components in isolation:

```python
@pytest.mark.unit
def test_question_bank_service_get_questions():
    """Test getting questions from question bank."""
    # Arrange
    service = QuestionBankService(mock_db_session)
    
    # Act
    questions = service.get_questions_for_role("Python Developer", "Job description")
    
    # Assert
    assert len(questions) > 0
    assert all(q.category == "technical" for q in questions)
```

**Location**: `tests/unit/`
**Markers**: `@pytest.mark.unit`
**Focus**: Individual functions, methods, and classes

### Integration Tests

Integration tests verify component interactions and API endpoints:

```python
@pytest.mark.integration
def test_parse_job_description_success(client, sample_parse_request, mock_ai_service):
    """Test successful job description parsing."""
    # Arrange
    with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
        # Act
        response = client.post("/api/v1/parse-jd", json=sample_parse_request)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0
```

**Location**: `tests/integration/`
**Markers**: `@pytest.mark.integration`
**Focus**: API endpoints, service interactions, database operations

### End-to-End Tests

End-to-end tests verify complete user workflows:

```python
@pytest.mark.e2e
def test_complete_interview_session_flow(client, sample_user, mock_ai_service):
    """Test complete interview session flow from creation to completion."""
    # Step 1: Create interview session
    session_data = {
        "role": "Senior Python Developer",
        "job_description": "Looking for Python developer"
    }
    
    # Step 2: Get session questions
    # Step 3: Analyze answers
    # Step 4: Complete session
    # Step 5: Verify final state
```

**Location**: `tests/e2e/`
**Markers**: `@pytest.mark.e2e`
**Focus**: Complete user journeys, workflow validation

### Performance Tests

Performance tests measure system performance and scalability:

```python
@pytest.mark.performance
def test_api_response_time(client, sample_parse_request):
    """Test API response time under load."""
    # Arrange
    start_time = time.time()
    
    # Act
    response = client.post("/api/v1/parse-jd", json=sample_parse_request)
    
    # Assert
    end_time = time.time()
    response_time = end_time - start_time
    assert response_time < 2.0  # Should respond within 2 seconds
```

**Location**: `tests/performance/`
**Markers**: `@pytest.mark.performance`
**Focus**: Response times, throughput, resource usage

### Security Tests

Security tests verify security vulnerabilities and best practices:

```python
@pytest.mark.security
def test_sql_injection_protection(client):
    """Test protection against SQL injection attacks."""
    # Arrange
    malicious_input = "'; DROP TABLE users; --"
    
    # Act
    response = client.post("/api/v1/parse-jd", json={
        "role": malicious_input,
        "jobDescription": "Test"
    })
    
    # Assert
    assert response.status_code == 422  # Should reject malicious input
```

**Location**: `tests/security/`
**Markers**: `@pytest.mark.security`
**Focus**: Security vulnerabilities, input validation, authentication

## Test Coverage

### Coverage Requirements

- **Minimum Coverage**: 85%
- **Target Coverage**: 90%
- **Critical Components**: 95%

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Generate XML coverage report
pytest --cov=app --cov-report=xml

# Generate terminal coverage report
pytest --cov=app --cov-report=term-missing
```

### Coverage Configuration

```ini
# pytest.ini
[tool:pytest]
addopts = 
    --cov=app
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=85
```

## CI/CD Integration

### GitHub Actions

The testing suite is integrated with GitHub Actions for continuous integration:

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Test Stages

1. **Unit Tests**: Fast, isolated tests
2. **Integration Tests**: Component interaction tests
3. **End-to-End Tests**: Complete workflow tests
4. **Performance Tests**: Performance and scalability tests
5. **Security Tests**: Security vulnerability tests

## Writing Tests

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_function_name():
    """Test description explaining what is being tested."""
    # Arrange - Set up test data and conditions
    input_data = {"key": "value"}
    expected_result = "expected"
    
    # Act - Execute the function being tested
    result = function_under_test(input_data)
    
    # Assert - Verify the results
    assert result == expected_result
    assert len(result) > 0
```

### Test Fixtures

Use pytest fixtures for test setup and teardown:

```python
@pytest.fixture
def sample_user(test_db_session):
    """Create a sample user for testing."""
    user_data = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User"
    }
    user = User(**user_data)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user
```

### Mocking

Use mocks for external dependencies:

```python
@patch('app.services.hybrid_ai_service.OpenAIService')
def test_ai_service_integration(mock_openai_service):
    """Test AI service integration with mocked external service."""
    # Arrange
    mock_openai_service.return_value.generate_questions.return_value = ["Question 1"]
    
    # Act
    result = hybrid_ai_service.generate_interview_questions("Python Developer", "Job description")
    
    # Assert
    assert len(result["questions"]) == 1
    assert result["questions"][0] == "Question 1"
```

### Database Testing

Use test database fixtures for database operations:

```python
def test_create_user(test_db_session):
    """Test user creation in database."""
    # Arrange
    user_data = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "name": "Test User"
    }
    
    # Act
    user = User(**user_data)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    
    # Assert
    assert user.id == user_data["id"]
    assert user.email == user_data["email"]
```

### Async Testing

Use pytest-asyncio for async function testing:

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    # Arrange
    input_data = "test input"
    
    # Act
    result = await async_function(input_data)
    
    # Assert
    assert result is not None
    assert result["status"] == "success"
```

## Best Practices

### Test Naming

- Use descriptive test names that explain what is being tested
- Follow the pattern: `test_<function_name>_<scenario>`
- Examples:
  - `test_create_user_success`
  - `test_create_user_duplicate_email`
  - `test_analyze_answer_invalid_input`

### Test Organization

- Group related tests in the same test class
- Use test classes for shared setup and teardown
- Keep tests focused on a single behavior

### Test Data

- Use factories or fixtures for test data generation
- Avoid hardcoded test data when possible
- Use realistic test data that reflects production scenarios

### Assertions

- Use specific assertions that clearly indicate what failed
- Test both positive and negative cases
- Verify edge cases and error conditions

### Test Isolation

- Each test should be independent and runnable in isolation
- Use proper setup and teardown to avoid test interference
- Mock external dependencies to ensure test isolation

### Performance

- Keep unit tests fast (< 1 second each)
- Use appropriate test markers for slow tests
- Consider test execution time in CI/CD pipelines

## Troubleshooting

### Common Issues

#### Test Database Issues

```bash
# Error: Database connection failed
# Solution: Check DATABASE_URL environment variable
export DATABASE_URL="sqlite:///./test_confida.db"

# Error: Migration failed
# Solution: Run database migrations
python app/database/migrate.py upgrade head
```

#### Import Issues

```bash
# Error: Module not found
# Solution: Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Error: Import error in tests
# Solution: Check __init__.py files in test directories
```

#### Async Test Issues

```bash
# Error: Async test not running
# Solution: Install pytest-asyncio
pip install pytest-asyncio

# Error: Event loop issues
# Solution: Use proper async test fixtures
@pytest.mark.asyncio
async def test_async_function():
    # Test implementation
```

#### Coverage Issues

```bash
# Error: Coverage too low
# Solution: Add more tests or exclude non-testable code
# In pytest.ini:
[tool:pytest]
addopts = --cov=app --cov-omit="*/migrations/*,*/tests/*"

# Error: Coverage report not generated
# Solution: Install pytest-cov
pip install pytest-cov
```

### Debugging Tests

```bash
# Run tests with verbose output
pytest -v

# Run specific test with debugging
pytest -v -s tests/unit/test_specific.py::test_function

# Run tests with pdb debugging
pytest --pdb

# Run tests with logging
pytest --log-cli-level=DEBUG
```

### Test Environment Setup

```bash
# Set up test environment
python scripts/run_tests.py --setup

# Clean up test environment
python scripts/run_tests.py --cleanup

# Run tests without cleanup
python scripts/run_tests.py --type all --no-cleanup
```

## Contributing to Tests

### Adding New Tests

1. **Identify the test type** (unit, integration, e2e, performance, security)
2. **Choose the appropriate test file** or create a new one
3. **Follow the test structure** (Arrange-Act-Assert)
4. **Add appropriate markers** (`@pytest.mark.unit`, etc.)
5. **Write descriptive test names** and docstrings
6. **Ensure test isolation** and proper cleanup

### Test Review Checklist

- [ ] Test covers the intended functionality
- [ ] Test is isolated and doesn't depend on other tests
- [ ] Test uses appropriate fixtures and mocks
- [ ] Test has clear assertions and error messages
- [ ] Test follows naming conventions
- [ ] Test is properly documented
- [ ] Test passes in CI/CD pipeline

### Test Maintenance

- **Regular Review**: Review tests during code reviews
- **Update Tests**: Update tests when functionality changes
- **Remove Obsolete Tests**: Remove tests for deprecated functionality
- **Monitor Coverage**: Ensure coverage doesn't decrease
- **Performance Monitoring**: Monitor test execution time

## Resources

### Documentation

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

### Tools

- **pytest**: Primary testing framework
- **pytest-cov**: Coverage reporting
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking utilities
- **FastAPI TestClient**: API testing
- **SQLAlchemy**: Database testing

### CI/CD

- **GitHub Actions**: Continuous integration
- **Codecov**: Coverage reporting
- **Docker**: Containerized testing
- **PostgreSQL**: Test database
- **Redis**: Test cache

For additional support, contact the development team or refer to the project's issue tracker.
