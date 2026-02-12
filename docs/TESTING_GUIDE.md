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
│   ├── test_database_models.py
│   ├── test_data_aggregator.py      # Dashboard data aggregation tests
│   ├── test_dashboard_service.py    # Dashboard service tests
│   ├── test_tts_configuration.py    # TTS configuration validation tests
│   ├── test_voice_cache.py          # Voice cache service tests
│   └── test_answer_audio_file_persistence.py  # Answer audio file ID persistence tests
├── integration/                # Integration tests
│   ├── test_interview_endpoints.py
│   ├── test_session_endpoints.py
│   ├── test_dashboard_endpoints.py  # Dashboard API endpoint tests
│   ├── test_answer_audio_file_persistence.py  # Answer audio file ID persistence integration tests
│   ├── test_speech_endpoints.py    # Admin speech synthesis endpoint tests
│   ├── test_api_endpoints.py       # Core API endpoint tests
│   ├── test_admin_endpoints.py     # Admin endpoint tests
│   ├── test_auth.py                # Authentication tests
│   └── test_scoring_endpoints.py   # Scoring endpoint tests
├── e2e/                       # End-to-end tests
│   └── test_complete_interview_flow.py
├── fixtures/                  # Test fixtures and utilities
└── utils/                     # Test utilities and helpers
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
python scripts/run_tests.py --marker integration

# Run specific test file
python scripts/run_tests.py --test tests/unit/test_question_bank_service.py

# Run the admin speech tooling endpoint tests
pytest tests/integration/test_speech_endpoints.py -v

# Run dashboard tests
pytest tests/unit/test_data_aggregator.py tests/unit/test_dashboard_service.py tests/integration/test_dashboard_endpoints.py -v

# Run dashboard tests with coverage
pytest tests/unit/test_data_aggregator.py --cov=app.services.data_aggregator --cov-report=term-missing

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

#### Dashboard Service Tests

Dashboard service tests verify data aggregation and formatting logic:

```python
@pytest.mark.unit
def test_get_user_sessions_summary_with_sessions(db_session, sample_user):
    """Test getting session summary with multiple sessions."""
    aggregator = DataAggregator(db_session)
    
    # Create test sessions
    session1 = InterviewSession(
        user_id=sample_user.id,
        role="Python Developer",
        status="completed",
        overall_score={"overall": 8.5}
    )
    # ... add sessions
    
    result = aggregator.get_user_sessions_summary(str(sample_user.id))
    
    assert result["total_sessions"] == 2
    assert result["average_score"] == 8.0
```

**Location**: 
- `tests/unit/test_data_aggregator.py` - Data aggregation logic
- `tests/unit/test_dashboard_service.py` - Dashboard service formatting

**Markers**: `@pytest.mark.unit`
**Focus**: Data aggregation, progress tracking, trend analysis, insights generation

#### TTS and Voice Cache Tests

TTS and voice cache tests verify text-to-speech functionality and caching:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_singleflight_pattern(voice_cache):
    """Test singleflight pattern prevents duplicate synthesis."""
    call_count = 0
    
    async def mock_synthesize():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return {"audio_data": "encoded_audio", "provider": "test"}
    
    # Simulate concurrent requests
    cache_key = voice_cache.generate_cache_key(...)
    results = await asyncio.gather(*[request() for _ in range(5)])
    
    # Should only call synthesize once
    assert call_count == 1
```

**Location**: 
- `tests/unit/test_tts_configuration.py` - TTS configuration validation
- `tests/unit/test_voice_cache.py` - Voice cache service tests

**Markers**: `@pytest.mark.unit`
**Focus**: Cache key generation, cache hits/misses, singleflight pattern, settings hash, statistics tracking

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

#### Dashboard API Tests

Dashboard API tests verify the dashboard data aggregation endpoints:

```python
@pytest.mark.integration
def test_get_dashboard_overview_success(client, sample_user, sample_sessions, mock_current_user):
    """Test successful dashboard overview retrieval."""
    with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
        response = client.get(
            f"/api/v1/dashboard/overview/{sample_user.id}",
            params={"days": 30}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(sample_user.id)
    assert "total_sessions" in data
    assert "average_score" in data
```

**Location**: `tests/integration/test_dashboard_endpoints.py`
**Markers**: `@pytest.mark.integration`
**Focus**: Dashboard endpoints, data aggregation, authentication, authorization

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

### Dashboard Test Coverage

The dashboard functionality includes comprehensive test coverage:

- **Data Aggregator Service**: 11 unit tests covering:
  - Session summary aggregation
  - User progress tracking
  - Recent activity retrieval
  - Streak calculation
  - Skill breakdown analysis
  - Performance metrics calculation
  - Trend data analysis
  - User insights generation

- **Dashboard Service**: 7 unit tests covering:
  - Overview data formatting
  - Progress data formatting
  - Analytics data formatting
  - Performance metrics formatting
  - Trends formatting
  - Insights formatting

- **Dashboard API Endpoints**: 11 integration tests covering:
  - All 6 dashboard endpoints (overview, progress, analytics, metrics, trends, insights)
  - Authentication and authorization
  - Input validation
  - Error handling
  - Empty data scenarios

**Total Dashboard Tests**: 29 test cases

### TTS and Voice Cache Test Coverage

The TTS and voice cache functionality includes comprehensive test coverage:

- **TTS Configuration Tests**: 20+ unit tests covering:
  - Default TTS settings validation
  - Environment variable configuration
  - Provider validation (Coqui, ElevenLabs, PlayHT)
  - API key validation
  - Format and version validation
  - Startup validation

- **Voice Cache Service Tests**: 12 unit tests covering:
  - Settings hash generation (deterministic)
  - Cache key generation (deterministic)
  - Cache hit/miss behavior
  - Cache storage and retrieval
  - Audio data caching
  - Singleflight pattern (prevents duplicate synthesis)
  - Error propagation
  - Statistics tracking
  - Cache disabled behavior
  - Helper methods
  - Singleton pattern

**Total TTS/Voice Cache Tests**: 32+ test cases

### Answer Audio File Persistence Test Coverage

The answer audio file persistence functionality (Ticket #082) includes comprehensive test coverage:

- **Unit Tests**: 5 unit tests covering:
  - Answer model with audio_file_id field
  - Answer model without audio_file_id (backward compatibility)
  - SessionQuestion.session_specific_context storage
  - Context update preserving existing data
  - Linked storage in both Answer and SessionQuestion

- **Integration Tests**: 5 integration tests covering:
  - `/analyze-answer` endpoint with audio_file_id
  - `/analyze-answer` endpoint without audio_file_id (backward compatibility)
  - `/sessions/questions/{id}/answers` endpoint with audio_file_id
  - GET `/sessions/questions/{id}/answers` endpoint returning audio_file_id
  - Deterministic audio file ID persistence

**Total Answer Audio File Persistence Tests**: 10 test cases

**Location**: 
- `tests/unit/test_answer_audio_file_persistence.py` - Unit tests for model persistence
- `tests/integration/test_answer_audio_file_persistence.py` - Integration tests for API endpoints

**Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`

**Focus**: Audio file ID storage, session persistence, backward compatibility, deterministic behavior

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

Coverage is configured in the CI workflow rather than in `pytest.ini`, so local test runs are fast by default. To run coverage locally:

```bash
# Run tests with coverage (same flags as CI)
python -m pytest tests/ -v --cov=app --cov-report=xml --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions

The testing suite is integrated with GitHub Actions for continuous integration. The CI has two jobs:

**test** -- runs against a Postgres 13 + Redis 6 service container on Python 3.11:

```yaml
# .github/workflows/test.yml (condensed)
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:13, ports: ["5432:5432"] }
      redis:    { image: redis:6, ports: ["6379:6379"] }
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with: { python-version: '3.11' }
    - run: |
        python -m pip install -r requirements.txt
        python -m pip install -r requirements-test.txt
    - run: python app/database/migrate.py upgrade head
    - run: python -m pytest tests/ -v --cov=app --cov-report=xml --cov-report=term-missing --junitxml=test-results.xml
    - uses: codecov/codecov-action@v4
      with: { fail_ci_if_error: false }
```

**security** -- runs Bandit static analysis and Safety dependency checks (non-blocking).

### Test Stages

1. **Unit Tests**: Fast, isolated tests
2. **Integration Tests**: Component interaction tests
3. **End-to-End Tests**: Complete workflow tests
4. **Security Tests**: Security vulnerability tests (separate CI job)

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
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "name": "Test User"
    }
    user = User(**user_data)
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user
```

> **Note**: Fixtures use UUID-based emails to prevent UNIQUE constraint errors when tests run in parallel or without full transaction rollback.

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

CI uses **PostgreSQL** (provided via a service container). Locally, you can use either Postgres or SQLite -- `conftest.py` respects whatever `DATABASE_URL` is set in your environment via `os.environ.setdefault()`.

```bash
# Local development with Postgres (recommended)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_confida"

# Local development with SQLite (quick, no server needed)
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

1. **Identify the test type** (unit, integration, e2e, security)
2. **Choose the appropriate test file** or create a new one
3. **Follow the test structure** (Arrange-Act-Assert)
4. **Add appropriate markers** (`@pytest.mark.unit`, etc.)
5. **Write descriptive test names** and docstrings
6. **Ensure test isolation** and proper cleanup

### Dashboard Testing Examples

#### Testing Data Aggregation

```python
def test_get_user_sessions_summary_with_date_range(db_session, sample_user):
    """Test getting session summary with date filtering."""
    aggregator = DataAggregator(db_session)
    
    # Create old and recent sessions
    old_session = InterviewSession(
        user_id=sample_user.id,
        status="completed",
        overall_score={"overall": 6.0},
        created_at=datetime.utcnow() - timedelta(days=60)
    )
    recent_session = InterviewSession(
        user_id=sample_user.id,
        status="completed",
        overall_score={"overall": 9.0},
        created_at=datetime.utcnow() - timedelta(days=5)
    )
    
    # Test with date range
    start_date = datetime.utcnow() - timedelta(days=30)
    result = aggregator.get_user_sessions_summary(
        str(sample_user.id),
        start_date=start_date
    )
    
    assert result["total_sessions"] == 1
    assert result["average_score"] == 9.0
```

#### Testing Dashboard Endpoints

```python
@pytest.mark.integration
def test_get_dashboard_overview_unauthorized(client, sample_user):
    """Test dashboard overview with unauthorized access."""
    other_user_id = str(uuid.uuid4())
    mock_user = {
        "user_id": other_user_id,
        "email": "other@example.com",
        "is_admin": False
    }
    
    with patch('app.routers.dashboard.get_current_user_required', return_value=mock_user):
        response = client.get(
            f"/api/v1/dashboard/overview/{sample_user.id}",
            params={"days": 30}
        )
    
    assert response.status_code == 403
```

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

## Dashboard Testing Guide

### Overview

The dashboard functionality includes comprehensive testing for data aggregation, service logic, and API endpoints. All dashboard tests follow the same patterns as other tests in the codebase.

### Running Dashboard Tests

```bash
# Run all dashboard tests
pytest tests/unit/test_data_aggregator.py tests/unit/test_dashboard_service.py tests/integration/test_dashboard_endpoints.py -v

# Run specific dashboard test file
pytest tests/unit/test_data_aggregator.py -v

# Run with coverage
pytest tests/unit/test_data_aggregator.py --cov=app.services.data_aggregator --cov-report=term-missing

# Run specific test
pytest tests/unit/test_data_aggregator.py::TestDataAggregator::test_get_user_sessions_summary_with_sessions -v
```

### Test Files

1. **`tests/unit/test_data_aggregator.py`** - Tests for `DataAggregator` service
   - Session summary aggregation
   - Progress tracking
   - Activity retrieval
   - Streak calculation
   - Skill breakdown
   - Performance metrics
   - Trend analysis
   - User insights

2. **`tests/unit/test_dashboard_service.py`** - Tests for `DashboardService`
   - Overview data formatting
   - Progress data formatting
   - Analytics data formatting
   - Metrics formatting
   - Trends formatting
   - Insights formatting

3. **`tests/integration/test_dashboard_endpoints.py`** - Tests for dashboard API endpoints
   - All 6 dashboard endpoints
   - Authentication and authorization
   - Input validation
   - Error handling
   - Edge cases

### Test Fixtures

Dashboard tests use standard fixtures from `conftest.py`:
- `db_session` - Database session
- `sample_user` - Test user
- `sample_sessions` - Test interview sessions
- `mock_current_user` - Mock authenticated user
- `mock_admin_user` - Mock admin user

### Common Test Patterns

#### Testing Data Aggregation

```python
def test_aggregation_method(db_session, sample_user):
    """Test aggregation method with sample data."""
    aggregator = DataAggregator(db_session)
    
    # Create test data
    session = InterviewSession(
        user_id=sample_user.id,
        status="completed",
        overall_score={"overall": 8.0}
    )
    db_session.add(session)
    db_session.commit()
    
    # Test aggregation
    result = aggregator.get_method(str(sample_user.id))
    
    # Assert results
    assert result["key"] == expected_value
```

#### Testing API Endpoints

```python
@pytest.mark.integration
def test_endpoint_success(client, sample_user, mock_current_user):
    """Test successful endpoint call."""
    with patch('app.routers.dashboard.get_current_user_required', return_value=mock_current_user):
        response = client.get(
            f"/api/v1/dashboard/endpoint/{sample_user.id}",
            params={"days": 30}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Test Coverage

Dashboard tests provide comprehensive coverage:
- **Unit Tests**: 18 tests covering service logic
- **Integration Tests**: 11 tests covering API endpoints
- **Total**: 29 test cases

All dashboard functionality is tested with:
- Positive cases (successful operations)
- Negative cases (error conditions)
- Edge cases (empty data, boundary conditions)
- Authentication and authorization
- Input validation

For additional support, contact the development team or refer to the project's issue tracker.

## TTS and Voice Cache Testing Guide

### Overview

The TTS (Text-to-Speech) and voice cache functionality includes comprehensive testing for configuration validation, cache behavior, singleflight pattern implementation, and the admin speech synthesis endpoint. All TTS-related tests follow the same patterns as other tests in the codebase.

### Running TTS and Voice Cache Tests

```bash
# Run all TTS-related tests
pytest tests/unit/test_tts_configuration.py tests/unit/test_voice_cache.py -v

# Run voice cache tests only
pytest tests/unit/test_voice_cache.py -v

# Run admin speech tooling endpoint tests
pytest tests/integration/test_speech_endpoints.py -v

# Run TTS configuration tests only
pytest tests/unit/test_tts_configuration.py -v

# Run with coverage
pytest tests/unit/test_voice_cache.py --cov=app.services.voice_cache --cov-report=term-missing

# Run specific test
pytest tests/unit/test_voice_cache.py::TestVoiceCacheService::test_singleflight_pattern -v
```

### Test Files

1. **`tests/unit/test_tts_configuration.py`** - Tests for TTS configuration validation
   - Default settings validation
   - Environment variable configuration
   - Provider validation (Coqui, ElevenLabs, PlayHT)
   - API key validation
   - Format and version validation
   - Startup validation

2. **`tests/unit/test_voice_cache.py`** - Tests for VoiceCacheService
   - Settings hash generation
   - Cache key generation
   - Cache hit/miss behavior
   - Singleflight pattern
   - Statistics tracking
   - Error handling

3. **`tests/integration/test_speech_endpoints.py`** - Tests for the admin-only `POST /api/v1/speech/synthesize` endpoint
   - Successful synthesis with mocked `TTSService`
   - Base64 payload verification
   - Rate-limit propagation (`TTSProviderRateLimitError` → HTTP 429)
   - Admin guardrail (401 when unauthenticated or non-admin)

### Test Fixtures

Voice cache tests use standard fixtures:
- `voice_cache` - VoiceCacheService instance for testing

### Common Test Patterns

#### Testing Cache Key Generation

```python
@pytest.mark.unit
def test_cache_key_generation(voice_cache):
    """Test cache key generation is deterministic."""
    settings_hash = voice_cache.generate_settings_hash()
    
    key1 = voice_cache.generate_cache_key("test text", "voice1", "mp3", settings_hash)
    key2 = voice_cache.generate_cache_key("test text", "voice1", "mp3", settings_hash)
    
    # Same inputs should produce same key
    assert key1 == key2
    
    # Different inputs should produce different keys
    key3 = voice_cache.generate_cache_key("different text", "voice1", "mp3", settings_hash)
    assert key1 != key3
```

#### Testing Singleflight Pattern

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_singleflight_pattern(voice_cache):
    """Test singleflight pattern prevents duplicate synthesis."""
    call_count = 0
    
    async def mock_synthesize():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate synthesis time
        return {"audio_data": "encoded_audio", "provider": "test"}
    
    cache_key = voice_cache.generate_cache_key(
        "test text", "voice1", "mp3", voice_cache.generate_settings_hash()
    )
    
    # Run 5 concurrent requests
    results = await asyncio.gather(*[
        voice_cache.get_or_synthesize(cache_key, mock_synthesize) 
        for _ in range(5)
    ])
    
    # Should only call synthesize once
    assert call_count == 1
    assert voice_cache.stats["singleflight_hits"] == 4
```

#### Testing Cache Behavior

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_voice_and_get(voice_cache):
    """Test caching and retrieving voice data."""
    # Cache voice data
    success = await voice_cache.cache_voice(
        text="test text",
        voice_id="voice1",
        format="mp3",
        file_id="file123",
        duration=5.5,
        version=1
    )
    
    assert success is True
    
    # Retrieve cached data
    cached = await voice_cache.get_cached_voice("test text", "voice1", "mp3")
    
    assert cached is not None
    assert cached["file_id"] == "file123"
    assert cached["duration"] == 5.5
    assert voice_cache.stats["hits"] == 1
```

### Test Coverage

TTS and voice cache tests provide comprehensive coverage:
- **Configuration Tests**: 20+ tests covering all TTS settings and validation
- **Voice Cache Tests**: 12 tests covering cache functionality
- **Total**: 32+ test cases

All TTS and voice cache functionality is tested with:
- Positive cases (successful operations)
- Negative cases (error conditions)
- Edge cases (cache disabled, concurrent requests)
- Deterministic behavior (cache keys, settings hash)
- Performance patterns (singleflight)

### Key Test Scenarios

1. **Cache Key Determinism**: Same inputs always produce same cache key
2. **Settings Hash**: Settings changes invalidate cache correctly
3. **Singleflight Pattern**: Concurrent requests share one synthesis
4. **Cache Statistics**: Hits, misses, errors tracked correctly
5. **Error Propagation**: Errors propagate to waiting requests
6. **Cache Disabled**: Graceful handling when cache is disabled
7. **Admin Tooling Endpoint**: Happy-path, rate-limit, and authorization coverage for `/api/v1/speech/synthesize`

For additional support, contact the development team or refer to the project's issue tracker.

## Answer Audio File Persistence Testing Guide

### Overview

The answer audio file persistence functionality (Ticket #082) includes comprehensive testing for storing and retrieving user answer audio file IDs. This feature enables deterministic playback of user answers by persisting audio file IDs in both the `Answer` model and `SessionQuestion.session_specific_context`.

### Running Answer Audio File Persistence Tests

```bash
# Run all answer audio file persistence tests
pytest tests/unit/test_answer_audio_file_persistence.py tests/integration/test_answer_audio_file_persistence.py -v

# Run unit tests only
pytest tests/unit/test_answer_audio_file_persistence.py -v

# Run integration tests only
pytest tests/integration/test_answer_audio_file_persistence.py -v

# Run with coverage
pytest tests/unit/test_answer_audio_file_persistence.py --cov=app.database.models --cov-report=term-missing

# Run specific test
pytest tests/unit/test_answer_audio_file_persistence.py::TestAnswerAudioFilePersistence::test_answer_with_audio_file_id -v
```

### Test Files

1. **`tests/unit/test_answer_audio_file_persistence.py`** - Unit tests for answer audio file ID persistence
   - Answer model with audio_file_id
   - Answer model without audio_file_id (backward compatibility)
   - SessionQuestion context storage
   - Context update preserving existing data
   - Linked storage verification

2. **`tests/integration/test_answer_audio_file_persistence.py`** - Integration tests for API endpoints
   - `/analyze-answer` endpoint with audio_file_id
   - `/analyze-answer` endpoint without audio_file_id
   - `/sessions/questions/{id}/answers` POST endpoint
   - `/sessions/questions/{id}/answers` GET endpoint
   - Deterministic persistence verification

### Test Fixtures

Answer audio file persistence tests use standard fixtures from `conftest.py`:
- `test_db_session` - Database session for unit tests
- `db_session` - Database session for integration tests
- `sample_user` - Test user
- `sample_question` - Test question
- `sample_interview_session` - Test interview session
- `sample_question_with_session` - Question linked to session (integration tests)
- `mock_current_user` - Mock authenticated user
- `mock_ai_client` - Mock AI client for answer analysis

### Common Test Patterns

#### Testing Answer Model with Audio File ID

```python
@pytest.mark.unit
def test_answer_with_audio_file_id(test_db_session, sample_question):
    """Test creating an answer with audio_file_id."""
    audio_file_id = "audio_file_123"
    answer = Answer(
        question_id=sample_question.id,
        answer_text="Test answer",
        audio_file_id=audio_file_id
    )
    test_db_session.add(answer)
    test_db_session.commit()
    
    assert answer.audio_file_id == audio_file_id
```

#### Testing SessionQuestion Context Update

```python
@pytest.mark.unit
def test_session_question_context_update_audio_file_id(
    test_db_session, sample_interview_session, sample_question
):
    """Test updating SessionQuestion.session_specific_context with answer_audio_file_id."""
    session_question = SessionQuestion(
        session_id=sample_interview_session.id,
        question_id=sample_question.id,
        question_order=1,
        session_specific_context={"role": "senior_developer"}
    )
    test_db_session.add(session_question)
    test_db_session.commit()
    
    # Update with audio file ID
    audio_file_id = "audio_file_789"
    context = session_question.session_specific_context or {}
    context["answer_audio_file_id"] = audio_file_id
    session_question.session_specific_context = context
    test_db_session.commit()
    
    assert session_question.session_specific_context["answer_audio_file_id"] == audio_file_id
    assert session_question.session_specific_context["role"] == "senior_developer"  # Preserved
```

#### Testing API Endpoint Integration

```python
@pytest.mark.integration
def test_analyze_answer_with_audio_file_id(
    client, db_session, sample_user, mock_current_user, 
    sample_question_with_session, mock_ai_client
):
    """Test analyze_answer endpoint stores audio_file_id."""
    sample_question, session = sample_question_with_session
    audio_file_id = "test_audio_file_123"
    
    request_data = {
        "jobDescription": "Software Engineer position",
        "question": "What is your experience?",
        "answer": "I have 5 years of experience",
        "audio_file_id": audio_file_id
    }
    
    mock_ai_client.analyze_answer = AsyncMock(return_value={
        "analysis": "Good answer",
        "score": {"clarity": 8, "confidence": 7},
        "suggestions": []
    })
    
    with patch('app.routers.interview.get_ai_client_dependency', return_value=mock_ai_client), \
         patch('app.routers.interview.get_current_user_required', return_value=mock_current_user):
        response = client.post(
            f"/api/v1/interview/analyze-answer?question_id={sample_question.id}",
            json=request_data
        )
    
    assert response.status_code == 200
    
    # Verify answer was stored with audio_file_id
    answer = db_session.query(Answer).filter(
        Answer.question_id == sample_question.id
    ).first()
    assert answer.audio_file_id == audio_file_id
    
    # Verify SessionQuestion was updated
    session_question = db_session.query(SessionQuestion).filter(
        SessionQuestion.question_id == sample_question.id
    ).first()
    assert session_question.session_specific_context.get("answer_audio_file_id") == audio_file_id
```

### Test Coverage

Answer audio file persistence tests provide comprehensive coverage:
- **Unit Tests**: 5 tests covering model persistence and context storage
- **Integration Tests**: 5 tests covering API endpoints and deterministic behavior
- **Total**: 10 test cases

All answer audio file persistence functionality is tested with:
- Positive cases (successful storage and retrieval)
- Negative cases (backward compatibility without audio_file_id)
- Edge cases (context preservation, linked storage)
- Deterministic behavior (same question uses same audio file ID)
- API integration (both sync and async endpoints)

### Key Test Scenarios

1. **Answer Model Storage**: Audio file ID stored in `Answer.audio_file_id` field
2. **SessionQuestion Context**: Audio file ID stored in `SessionQuestion.session_specific_context["answer_audio_file_id"]`
3. **Backward Compatibility**: Answers without audio_file_id still work correctly
4. **Context Preservation**: Updating context preserves existing context data
5. **Linked Storage**: Both Answer and SessionQuestion store the same audio file ID
6. **Deterministic Behavior**: Same question in same session uses same audio file ID
7. **API Integration**: Both `/analyze-answer` and `/sessions/questions/{id}/answers` endpoints support audio_file_id

### Related Features

- **Ticket #082**: Sessions Persist Voice File IDs with Questions
- **Answer Model**: `app/database/models.py` - Answer model with `audio_file_id` field
- **SessionQuestion Model**: `app/database/models.py` - SessionQuestion model with `session_specific_context` JSONB field
- **API Endpoints**: 
  - `app/routers/interview.py` - `/analyze-answer` endpoint
  - `app/routers/sessions.py` - `/sessions/questions/{id}/answers` endpoints

For additional support, contact the development team or refer to the project's issue tracker.
