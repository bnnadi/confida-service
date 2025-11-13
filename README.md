# Confida Backend

AI-powered interview coaching backend with intelligent question generation and answer analysis.

## Features

- **Job Description Parsing**: Generate relevant interview questions based on role and job description
- **Answer Analysis**: Evaluate candidate responses with scoring, feedback, and improvement suggestions
- **RESTful API**: Clean, documented endpoints with automatic OpenAPI documentation
- **CORS Support**: Configured for React frontend integration

## Project Structure

```
jd-ai-backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entrypoint
│   ├── routers/
│   │   ├── __init__.py
│   │   └── interview.py   # Endpoints for parse-jd & analyze-answer
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py     # Pydantic request/response models
│   └── services/
│       ├── __init__.py
│       └── mock_logic.py  # Placeholder for future AI logic
├── requirements.txt
└── README.md
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd jd-ai-backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Development Mode
```bash
uvicorn app.main:app --reload --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. Parse Job Description
**POST** `/api/v1/parse-jd`

Generate interview questions based on job description.

**Request:**
```json
{
  "role": "Senior Frontend Engineer",
  "jobDescription": "We are looking for a Senior Frontend Engineer with 5+ years of experience in React, TypeScript, and accessibility..."
}
```

**Response:**
```json
{
  "questions": [
    "Tell me about yourself",
    "How have you worked with React?",
    "What's your experience with accessibility?",
    "Can you describe your experience with Senior Frontend Engineer?",
    "What challenges have you faced in your previous roles?"
  ]
}
```

### 2. Analyze Answer
**POST** `/api/v1/analyze-answer`

Analyze a candidate's answer and provide comprehensive feedback with 100-point scoring rubric.

**Request:**
```json
{
  "jobDescription": "We are looking for a Senior Frontend Engineer with 5+ years of experience in React, TypeScript, and accessibility...",
  "question": "How have you worked with React?",
  "answer": "I have used React for 5 years and built several applications..."
}
```

**Response:**
```json
{
  "analysis": "Detailed analysis of the answer...",
  "score": {
    "clarity": 7,
    "confidence": 6
  },
  "enhanced_score": {
    "total_score": 75.5,
    "grade_tier": "Strong",
    "verbal_communication": 32.0,
    "interview_readiness": 16.0,
    "non_verbal_communication": 18.5,
    "adaptability_engagement": 9.0,
    "verbal_communication_details": {
      "articulation": {"score": 4.0, "feedback": "Clear articulation"},
      "content_relevance": {"score": 4.5, "feedback": "Highly relevant"},
      "structure": {"score": 3.5, "feedback": "Well organized"},
      "vocabulary": {"score": 4.0, "feedback": "Appropriate word choice"},
      "delivery_confidence": {"score": 4.0, "feedback": "Confident delivery"}
    },
    "top_strengths": ["Clear communication", "Good preparation"],
    "improvement_areas": ["Could improve pacing", "More examples needed"]
  },
  "suggestions": [
    "Mention accessibility compliance",
    "Highlight design system experience",
    "Provide specific examples of React projects"
  ]
}
```

**Enhanced Scoring System:**
- **100-Point Scale**: Comprehensive scoring across 5 categories
- **17 Sub-Dimensions**: Detailed evaluation of specific skills
- **Grade Tiers**: Excellent (90-100), Strong (75-89), Average (60-74), At Risk (0-59)
- **Category Breakdown**:
  - Verbal Communication (40 points)
  - Interview Readiness (20 points)
  - Non-verbal Communication (25 points)
  - Adaptability & Engagement (15 points)

### 3. Real-Time Feedback WebSocket
**WebSocket** `/ws/feedback/{session_id}`

Real-time feedback endpoint for live speech analysis during interviews.

**Connection:**
```
ws://localhost:8000/ws/feedback/{session_id}?token={access_token}
```

**Message Types (Client → Server):**
- `{"type": "audio_chunk", "data": "base64_encoded_audio", "chunk_index": 0, "is_final": false}`
- `{"type": "transcript", "data": "transcript text"}`
- `{"type": "ping"}` - Keepalive

**Response (Server → Client):**
```json
{
  "session_id": "session-123",
  "feedback_type": "speech_analysis",
  "message": "Keep going! Your speech is clear and well-paced.",
  "confidence": 0.85,
  "suggestions": ["Try speaking a bit faster"],
  "metrics": {
    "filler_words": 2,
    "pace": 150,
    "clarity": 0.8,
    "volume": 0.7,
    "pauses": 3,
    "confidence": 0.85
  }
}
```

### 4. Health Check
**GET** `/health`

Returns API health status.

**Response:**
```json
{
  "status": "healthy"
}
```

## Development

### Current Implementation
- **AI Service Microservice**: Primary AI processing through dedicated microservice
- **Hybrid AI Service**: Intelligent fallback to direct AI services when microservice unavailable
- **AI Integration**: Full OpenAI, Anthropic, and Ollama support with automatic fallback
- **Error Handling**: Comprehensive error handling with graceful degradation
- **Rate Limiting**: Built-in rate limiting middleware
- **Service Testing**: Admin endpoints for testing all AI services
- **Speech Processing**: Speech-to-text transcription support

### Features Implemented
- ✅ AI Service Microservice integration with pure HTTP client
- ✅ Clean microservice architecture with proper separation
- ✅ Question generation via AI service microservice
- ✅ Answer analysis via AI service microservice
- ✅ **Enhanced 100-Point Scoring Rubric System** - Comprehensive scoring with 5 categories and 17 sub-dimensions
- ✅ Speech-to-text transcription via AI service microservice
- ✅ **Real-Time Feedback WebSocket API** - WebSocket endpoints for live speech analysis and real-time feedback
- ✅ Rate limiting and admin endpoints
- ✅ Comprehensive error handling
- ✅ Centralized logging and configuration

### Future Enhancements
- [ ] Database schema migration for enhanced scoring data
- [ ] Progress tracking across scoring dimensions
- [ ] Analytics for dimension improvement over time
- [ ] Dimension-specific coaching tips
- [ ] Redis integration for WebSocket message queuing and scaling

### Adding New Endpoints
1. Create new router in `app/routers/`
2. Define schemas in `app/models/schemas.py`
3. Implement business logic in `app/services/`
4. Include router in `app/main.py`

## Testing

### Manual Testing
Use the interactive documentation at http://localhost:8000/docs to test endpoints.

### Example cURL Commands

**Parse Job Description:**
```bash
curl -X POST "http://localhost:8000/api/v1/parse-jd" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Senior Frontend Engineer",
    "jobDescription": "We are looking for a Senior Frontend Engineer with 5+ years of experience in React, TypeScript, and accessibility..."
  }'
```

**Analyze Answer:**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "jobDescription": "We are looking for a Senior Frontend Engineer...",
    "question": "How have you worked with React?",
    "answer": "I have used React for 5 years and built several applications..."
  }'
```

## AI Service Configuration

The backend uses a pure microservice architecture for AI operations:

### Environment Variables

```bash
# AI Service Microservice Configuration
AI_SERVICE_URL=http://localhost:8001
AI_SERVICE_TIMEOUT=30.0
AI_SERVICE_RETRY_ATTEMPTS=3
```

### Pure Microservice Architecture

The backend follows proper microservice separation:
1. **AI Service Client**: Pure HTTP client for AI service microservice
2. **No Fallback Logic**: Clean separation of concerns
3. **Health Monitoring**: Simple health checks for microservice connectivity
4. **Error Handling**: Proper HTTP error responses when microservice is unavailable

## Dependencies

- **fastapi**: Modern web framework for building APIs
- **uvicorn**: ASGI server for running FastAPI applications
- **pydantic**: Data validation using Python type annotations
- **python-multipart**: Support for form data (future file uploads)
- **httpx**: HTTP client for AI service microservice communication

**Note**: Direct AI service dependencies (OpenAI, Anthropic, Ollama, etc.) have been removed to maintain proper microservice separation.

## License

[Add your license here] 