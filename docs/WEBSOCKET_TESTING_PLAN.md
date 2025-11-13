# WebSocket Testing Plan for Ticket #043

## Overview

This document outlines the comprehensive test suite for the Real-Time Feedback WebSocket API implementation (Ticket #043).

## Test Coverage

### ✅ Unit Tests

#### 1. `tests/unit/test_speech_analyzer.py`
Tests for the `SpeechAnalyzer` service covering:
- ✅ Empty transcript analysis
- ✅ Basic transcript analysis
- ✅ Filler word detection
- ✅ Pace calculation
- ✅ Pause detection
- ✅ Audio chunk analysis (with and without transcript)
- ✅ Real-time suggestions generation (slow/fast pace, filler words, clarity)
- ✅ Optimal speech scenarios
- ✅ State reset functionality

**Coverage**: Core speech analysis logic, metrics calculation, suggestion generation

#### 2. `tests/unit/test_real_time_feedback_service.py`
Tests for the `RealTimeFeedbackService` covering:
- ✅ Metrics building (with/without volume)
- ✅ Error feedback creation
- ✅ Audio chunk processing (success and error cases)
- ✅ Transcript chunk processing (with and without AI feedback)
- ✅ AI service integration (available/unavailable)
- ✅ Session management (register, cleanup, get info)
- ✅ Feedback message generation

**Coverage**: Service orchestration, error handling, AI integration, session management

### ✅ Integration Tests

#### 3. `tests/integration/test_websocket_endpoints.py`
Tests for WebSocket endpoints covering all ticket requirements:

**Testing Step 1: WebSocket Connection Establishment**
- ✅ Connection establishment
- ✅ Connection status message
- ✅ Authentication requirement
- ✅ Health check endpoint

**Testing Step 2: Real-Time Feedback Generation**
- ✅ Transcript message handling
- ✅ Feedback response format
- ✅ Metrics and suggestions in feedback

**Testing Step 3: Live Speech Analysis**
- ✅ Audio chunk message handling
- ✅ Binary audio data handling
- ✅ Speech analysis feedback

**Testing Step 4: Real-Time Data Streaming**
- ✅ Multiple message handling
- ✅ Continuous feedback stream
- ✅ Message sequencing

**Testing Step 5: Connection Management**
- ✅ Connection registration
- ✅ Connection cleanup on disconnect
- ✅ Active connection tracking

**Testing Step 6: Error Handling**
- ✅ Invalid JSON handling
- ✅ Processing errors
- ✅ Error feedback format
- ✅ Connection error recovery

**Additional Tests:**
- ✅ Ping/pong keepalive
- ✅ Metadata updates
- ✅ Question ID parameter handling

## Test Execution

### Run All WebSocket Tests
```bash
# Run all WebSocket-related tests
pytest tests/unit/test_speech_analyzer.py tests/unit/test_real_time_feedback_service.py tests/integration/test_websocket_endpoints.py -v

# Run with coverage
pytest tests/unit/test_speech_analyzer.py tests/unit/test_real_time_feedback_service.py tests/integration/test_websocket_endpoints.py --cov=app.services.speech_analyzer --cov=app.services.real_time_feedback --cov=app.routers.websocket -v
```

### Run by Category
```bash
# Unit tests only
pytest tests/unit/test_speech_analyzer.py tests/unit/test_real_time_feedback_service.py -v -m unit

# Integration tests only
pytest tests/integration/test_websocket_endpoints.py -v -m integration
```

### Run Specific Test
```bash
# Run specific test function
pytest tests/integration/test_websocket_endpoints.py::TestWebSocketEndpoints::test_websocket_connection_establishment -v
```

## Test Requirements

### Dependencies
All required dependencies are already in `requirements.txt`:
- `pytest>=7.4.0`
- `pytest-asyncio>=0.21.0`
- `websockets>=12.0` (for WebSocket support)
- `httpx>=0.25.0` (for TestClient)

### Test Fixtures
Tests use existing fixtures from `tests/conftest.py`:
- `client` - FastAPI TestClient
- `mock_ai_client` - Mock AI service client
- `sample_user` - Sample user for authentication
- `db_session` - Database session

### Mocking Strategy
- **Authentication**: Mocked via `authenticate_websocket` to avoid database dependencies
- **AI Service**: Mocked to avoid external API calls
- **Database**: Uses test database from fixtures

## Coverage Goals

### Target Coverage
- **Unit Tests**: 90%+ coverage for services
- **Integration Tests**: All WebSocket endpoints and message types
- **Overall**: Meet project requirement of 85%+ coverage

### Current Coverage Areas
✅ Speech analysis logic  
✅ Feedback generation  
✅ Error handling  
✅ Session management  
✅ WebSocket connection lifecycle  
✅ Message handling (all types)  
✅ Authentication  

## Test Scenarios Covered

### Happy Path
1. ✅ Successful WebSocket connection
2. ✅ Successful transcript processing
3. ✅ Successful audio chunk processing
4. ✅ Real-time feedback generation
5. ✅ Multiple message handling

### Error Scenarios
1. ✅ Authentication failure
2. ✅ Invalid JSON messages
3. ✅ Processing errors
4. ✅ Connection errors
5. ✅ Missing required fields

### Edge Cases
1. ✅ Empty transcripts
2. ✅ Audio without transcript
3. ✅ Optimal speech (no suggestions)
4. ✅ Non-existent sessions
5. ✅ Invalid question IDs

## Future Test Enhancements

### Performance Tests (Testing Step 7)
- Load testing with multiple concurrent connections
- Message throughput testing
- Latency measurement

### Scalability Tests (Testing Step 7)
- Connection pool management
- Memory usage under load
- Resource cleanup verification

### Message Queuing Tests (Testing Step 8)
- Redis integration (when implemented)
- Message persistence
- Queue reliability

## Notes

- Tests use FastAPI's `TestClient.websocket_connect()` for WebSocket testing
- All async tests are properly marked with `@pytest.mark.asyncio`
- Tests follow existing project patterns and conventions
- Mocking is used to isolate units and avoid external dependencies
- Tests are designed to be fast and runnable in CI/CD pipelines

## Running Tests in CI/CD

Tests are automatically run in CI/CD pipelines and should:
- Pass all unit tests (< 5 seconds)
- Pass all integration tests (< 30 seconds)
- Meet coverage requirements (85%+)
- Not require external services (all mocked)

