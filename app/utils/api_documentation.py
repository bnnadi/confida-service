"""
API Documentation Utilities for InterviewIQ.

This module provides simplified, maintainable utilities for API documentation
including examples, error responses, and usage guides.
"""

from typing import Dict, Any, List
from fastapi.openapi.utils import get_openapi
from fastapi import FastAPI


class APIDocumentationBuilder:
    """Simplified builder for API documentation with clean, maintainable code."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.examples = self._get_api_examples()
        self.error_responses = self._get_error_responses()
    
    def build_openapi_schema(self) -> Dict[str, Any]:
        """Build comprehensive OpenAPI schema with examples and documentation."""
        if self.app.openapi_schema:
            return self.app.openapi_schema
        
        openapi_schema = get_openapi(
            title=self.app.title,
            version=self.app.version,
            description=self.app.description,
            routes=self.app.routes,
            contact=getattr(self.app, 'contact', None),
            license_info=getattr(self.app, 'license_info', None),
            servers=getattr(self.app, 'servers', None)
        )
        
        # Add organized tags
        openapi_schema["tags"] = self._get_api_tags()
        
        # Add common schemas
        openapi_schema["components"]["schemas"].update(self._get_common_schemas())
        
        # Add examples to endpoints
        self._add_examples_to_endpoints(openapi_schema)
        
        self.app.openapi_schema = openapi_schema
        return openapi_schema
    
    def _get_api_tags(self) -> List[Dict[str, str]]:
        """Get organized API tags for better documentation structure."""
        return [
            {
                "name": "Authentication",
                "description": "🔐 User authentication and authorization endpoints"
            },
            {
                "name": "Interview",
                "description": "🎯 Core interview functionality - question generation and answer analysis"
            },
            {
                "name": "Sessions",
                "description": "📊 Interview session management and tracking"
            },
            {
                "name": "Files",
                "description": "📁 File upload and management operations"
            },
            {
                "name": "Speech",
                "description": "🎤 Speech-to-text and audio processing"
            },
            {
                "name": "Vector Search",
                "description": "🔍 Semantic search through question banks"
            },
            {
                "name": "Cache",
                "description": "⚡ Caching operations and management"
            },
            {
                "name": "Health",
                "description": "💚 System health checks and monitoring"
            },
            {
                "name": "Analytics",
                "description": "📈 Performance analytics and reporting"
            },
            {
                "name": "Intelligent Questions",
                "description": "🧠 AI-powered intelligent question selection"
            }
        ]
    
    def _get_common_schemas(self) -> Dict[str, Any]:
        """Get common response schemas for consistent API documentation."""
        return {
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "description": "Error message",
                        "example": "Validation error occurred"
                    },
                    "detail": {
                        "type": "string",
                        "description": "Detailed error information",
                        "example": "The field 'role' is required"
                    },
                    "status_code": {
                        "type": "integer",
                        "description": "HTTP status code",
                        "example": 400
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Error timestamp",
                        "example": "2024-01-15T10:30:00Z"
                    }
                },
                "required": ["error", "status_code", "timestamp"]
            },
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Success message",
                        "example": "Operation completed successfully"
                    },
                    "data": {
                        "type": "object",
                        "description": "Response data"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Response timestamp",
                        "example": "2024-01-15T10:30:00Z"
                    }
                },
                "required": ["message", "timestamp"]
            },
            "ValidationError": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                        "example": "Validation Error"
                    },
                    "detail": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "loc": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "example": ["body", "role"]
                                },
                                "msg": {
                                    "type": "string",
                                    "example": "field required"
                                },
                                "type": {
                                    "type": "string",
                                    "example": "value_error.missing"
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _get_api_examples(self) -> Dict[str, Any]:
        """Get comprehensive API examples for better developer experience."""
        return {
            "parse_jd_request": {
                "summary": "Parse Job Description Request",
                "description": "Example request for parsing a job description and generating interview questions",
                "value": {
                    "role": "Senior Software Engineer",
                    "job_description": "We are looking for a Senior Software Engineer with 5+ years of experience in Python, FastAPI, and cloud technologies. The ideal candidate should have experience with microservices architecture, database design, and team leadership."
                }
            },
            "parse_jd_response": {
                "summary": "Parse Job Description Response",
                "description": "Example response with generated interview questions",
                "value": {
                    "questions": [
                        "Can you describe your experience with microservices architecture and how you've implemented it in previous projects?",
                        "How would you design a scalable database schema for a high-traffic application?",
                        "Tell me about a time when you had to lead a team through a challenging technical project."
                    ],
                    "role_analysis": {
                        "required_skills": ["Python", "FastAPI", "Microservices"],
                        "seniority_level": "Senior",
                        "experience_years": 5
                    }
                }
            },
            "analyze_answer_request": {
                "summary": "Analyze Answer Request",
                "description": "Example request for analyzing an interview answer",
                "value": {
                    "job_description": "Senior Software Engineer position...",
                    "question": "Describe your experience with microservices architecture",
                    "answer": "I have 3 years of experience building microservices using Python and FastAPI. I've designed and implemented several microservices that handle user authentication, payment processing, and data analytics."
                }
            },
            "analyze_answer_response": {
                "summary": "Analyze Answer Response",
                "description": "Example response with detailed feedback",
                "value": {
                    "score": {
                        "overall": 8.5,
                        "clarity": 9.0,
                        "confidence": 8.0,
                        "relevance": 8.5
                    },
                    "feedback": "Excellent answer! You clearly demonstrated relevant experience with specific technologies. Consider adding more details about challenges faced and solutions implemented.",
                    "suggestions": [
                        "Provide specific examples of microservices you've built",
                        "Mention any challenges you faced and how you overcame them",
                        "Discuss the impact of your microservices on system performance"
                    ]
                }
            }
        }
    
    def _get_error_responses(self) -> Dict[str, Any]:
        """Get standardized error responses for consistent API behavior."""
        return {
            "400": {
                "description": "Bad Request - Invalid input data",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ValidationError"},
                        "example": {
                            "error": "Validation Error",
                            "detail": [
                                {
                                    "loc": ["body", "role"],
                                    "msg": "field required",
                                    "type": "value_error.missing"
                                }
                            ]
                        }
                    }
                }
            },
            "401": {
                "description": "Unauthorized - Invalid or missing authentication",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": "Authentication required",
                            "detail": "Invalid or missing API token",
                            "status_code": 401,
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            },
            "403": {
                "description": "Forbidden - Insufficient permissions",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": "Access denied",
                            "detail": "Insufficient permissions for this operation",
                            "status_code": 403,
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            },
            "404": {
                "description": "Not Found - Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": "Resource not found",
                            "detail": "The requested resource does not exist",
                            "status_code": 404,
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            },
            "429": {
                "description": "Too Many Requests - Rate limit exceeded",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": "Rate limit exceeded",
                            "detail": "Too many requests. Please try again later.",
                            "status_code": 429,
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            },
            "500": {
                "description": "Internal Server Error - Server error occurred",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                        "example": {
                            "error": "Internal server error",
                            "detail": "An unexpected error occurred. Please try again later.",
                            "status_code": 500,
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    }
                }
            }
        }
    
    def _add_examples_to_endpoints(self, openapi_schema: Dict[str, Any]) -> None:
        """Add examples to API endpoints for better documentation."""
        # This would be implemented to add examples to specific endpoints
        # For now, we'll keep it simple and add examples through the schemas
        pass


def get_usage_guides() -> Dict[str, str]:
    """Get simplified usage guides for common API operations."""
    return {
        "quick_start": """
# 🚀 Quick Start Guide

## 1. Authentication
```bash
curl -X POST "https://api.interviewiq.com/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "your_username", "password": "your_password"}'
```

## 2. Generate Interview Questions
```bash
curl -X POST "https://api.interviewiq.com/parse-jd" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "role": "Senior Software Engineer",
    "job_description": "Looking for a senior engineer with Python experience..."
  }'
```

## 3. Analyze Interview Answer
```bash
curl -X POST "https://api.interviewiq.com/analyze-answer" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "job_description": "Senior Software Engineer position...",
    "question": "Describe your Python experience",
    "answer": "I have 5 years of Python experience..."
  }'
```
        """,
        
        "python_sdk": """
# 🐍 Python SDK Example

```python
import requests

class InterviewIQClient:
    def __init__(self, api_key, base_url="https://api.interviewiq.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def generate_questions(self, role, job_description):
        response = requests.post(
            f"{self.base_url}/parse-jd",
            headers=self.headers,
            json={"role": role, "job_description": job_description}
        )
        return response.json()
    
    def analyze_answer(self, job_description, question, answer):
        response = requests.post(
            f"{self.base_url}/analyze-answer",
            headers=self.headers,
            json={
                "job_description": job_description,
                "question": question,
                "answer": answer
            }
        )
        return response.json()

# Usage
client = InterviewIQClient("your_api_key")
questions = client.generate_questions("Software Engineer", "Job description...")
feedback = client.analyze_answer("Job description...", "Question?", "My answer...")
```
        """,
        
        "javascript_sdk": """
# 🟨 JavaScript SDK Example

```javascript
class InterviewIQClient {
    constructor(apiKey, baseUrl = 'https://api.interviewiq.com') {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async generateQuestions(role, jobDescription) {
        const response = await fetch(`${this.baseUrl}/parse-jd`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ role, job_description: jobDescription })
        });
        return await response.json();
    }
    
    async analyzeAnswer(jobDescription, question, answer) {
        const response = await fetch(`${this.baseUrl}/analyze-answer`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                job_description: jobDescription,
                question,
                answer
            })
        });
        return await response.json();
    }
}

// Usage
const client = new InterviewIQClient('your_api_key');
const questions = await client.generateQuestions('Software Engineer', 'Job description...');
const feedback = await client.analyzeAnswer('Job description...', 'Question?', 'My answer...');
```
        """
    }
