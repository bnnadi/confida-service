# InterviewIQ Backend

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

Analyze a candidate's answer and provide feedback.

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
  "score": {
    "clarity": 7,
    "confidence": 6
  },
  "missingKeywords": ["WCAG", "ARIA", "accessibility compliance", "design systems"],
  "improvements": [
    "Mention accessibility compliance",
    "Highlight design system experience",
    "Provide specific examples of React projects"
  ],
  "idealAnswer": "I've built accessible React apps following WCAG guidelines, implemented ARIA attributes for screen readers, and worked extensively with design systems to ensure consistency across applications..."
}
```

### 3. Health Check
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
- **Mock Responses**: All endpoints currently return static mock data
- **TODO Comments**: Marked locations for future AI/ML integration
- **Error Handling**: Basic error handling with HTTP status codes

### Future Enhancements
- [ ] Integrate OpenAI GPT for intelligent question generation
- [ ] Add Whisper integration for voice input processing
- [ ] Implement answer analysis using AI models
- [ ] Add authentication and rate limiting
- [ ] Database integration for storing interview sessions

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

## Dependencies

- **fastapi**: Modern web framework for building APIs
- **uvicorn**: ASGI server for running FastAPI applications
- **pydantic**: Data validation using Python type annotations
- **python-multipart**: Support for form data (future file uploads)

## License

[Add your license here] 