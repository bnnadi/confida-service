# Dual-Mode Interview System

This document describes the new dual-mode interview system that supports both Practice Scenarios and Job-Based Interviews using a shared question engine.

## Overview

The system now supports two distinct entry paths for interview sessions:

1. **Practice Mode**: Uses pre-defined scenarios with curated questions
2. **Interview Mode**: Generates questions dynamically using AI based on job descriptions

Both modes share the same scoring, feedback, and session management infrastructure.

## New API Endpoints

### 1. Create Session (Updated)
**POST** `/api/v1/sessions/`

Creates a new interview session supporting both modes.

#### Request Body
```json
{
  "user_id": "string",
  "mode": "practice" | "interview",
  "role": "string",
  
  // For practice mode
  "scenario_id": "string",  // Required for practice mode
  
  // For interview mode  
  "job_title": "string",        // Required for interview mode
  "job_description": "string"   // Required for interview mode
}
```

#### Response
```json
{
  "id": "uuid",
  "user_id": "uuid", 
  "mode": "practice" | "interview",
  "role": "string",
  "job_description": "string" | null,
  "scenario_id": "string" | null,
  "question_source": "scenario" | "generated",
  "status": "active",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### 2. Preview Session
**GET** `/api/v1/sessions/preview`

Preview a session without creating it.

#### Query Parameters
- `mode`: "practice" | "interview" (required)
- `role`: string (required)
- `scenario_id`: string (required for practice mode)
- `job_title`: string (required for interview mode)
- `job_description`: string (required for interview mode)

#### Response
```json
{
  "mode": "practice" | "interview",
  "role": "string",
  "questions": [
    {
      "id": "string",
      "text": "string", 
      "type": "behavioral" | "technical" | "situational" | "general",
      "difficulty_level": "easy" | "medium" | "hard",
      "category": "string"
    }
  ],
  "total_questions": 5,
  "estimated_duration": 15
}
```

### 3. Get Available Scenarios
**GET** `/api/v1/sessions/scenarios`

Get list of available practice scenarios.

#### Response
```json
{
  "scenarios": [
    {
      "id": "software_engineer",
      "name": "Software Engineer", 
      "description": "Practice questions for software engineering roles"
    }
  ],
  "total": 5
}
```

## Available Practice Scenarios

1. **software_engineer**: Software engineering roles
2. **data_scientist**: Data science roles
3. **product_manager**: Product management roles
4. **sales_representative**: Sales roles
5. **marketing_manager**: Marketing roles

## Database Changes

### New Columns in `interview_sessions` table:
- `mode`: "practice" | "interview" (default: "interview")
- `scenario_id`: string (nullable, for practice mode)
- `question_source`: "scenario" | "generated" (default: "generated")
- `question_ids`: JSONB array of question IDs
- `job_context`: JSONB object with job-specific context
- `job_description`: Now nullable (for practice mode)

## Usage Examples

### Create Practice Session
```bash
curl -X POST "http://localhost:8000/api/v1/sessions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "user-123",
    "mode": "practice",
    "role": "Software Engineer",
    "scenario_id": "software_engineer"
  }'
```

### Create Interview Session
```bash
curl -X POST "http://localhost:8000/api/v1/sessions/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "user_id": "user-123", 
    "mode": "interview",
    "role": "Senior Software Engineer",
    "job_title": "Senior Software Engineer",
    "job_description": "We are looking for a Senior Software Engineer with 5+ years of experience..."
  }'
```

### Preview Practice Session
```bash
curl "http://localhost:8000/api/v1/sessions/preview?mode=practice&role=Software%20Engineer&scenario_id=software_engineer"
```

### Preview Interview Session
```bash
curl "http://localhost:8000/api/v1/sessions/preview?mode=interview&role=Senior%20Software%20Engineer&job_title=Senior%20Software%20Engineer&job_description=We%20are%20looking%20for..."
```

## Architecture

### Question Engine Service
The `QuestionEngine` service provides unified question generation:

- `generate_questions_from_scenario(scenario_id)`: Generate questions from practice scenarios
- `generate_questions_from_job(title, description)`: Generate questions using AI
- `get_available_scenarios()`: Get list of available scenarios
- `_classify_question_type(question_text)`: Classify question types

### Session Service Updates
The `SessionService` now includes:

- `create_practice_session()`: Create practice sessions
- `create_interview_session()`: Create job-based sessions  
- `preview_practice_session()`: Preview practice sessions
- `preview_interview_session()`: Preview interview sessions
- `get_available_scenarios()`: Get available scenarios

## Benefits

1. **Unified Experience**: Both modes use the same scoring and feedback system
2. **Flexible Entry Points**: Users can choose between practice and real interview preparation
3. **Consistent API**: Same endpoints work for both modes with different parameters
4. **Extensible**: Easy to add new practice scenarios or question types
5. **Backward Compatible**: Existing interview mode continues to work

## Testing

Run the test script to verify the implementation:

```bash
python test_dual_mode.py
```

This will test:
- Scenarios endpoint
- Practice session preview
- Interview session preview
- Session creation (requires authentication)
