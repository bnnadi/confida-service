"""
Vector Search Models

Pydantic models for vector search API requests and responses.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class QuestionSearchRequest(BaseModel):
    """Request model for question search."""
    query: str = Field(..., description="Search query text")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Python async programming concepts",
                "filters": {
                    "difficulty": "medium",
                    "category": "technical",
                    "role": "python_developer"
                },
                "limit": 10
            }
        }

class JobSearchRequest(BaseModel):
    """Request model for job description search."""
    query: str = Field(..., description="Search query text")
    role: Optional[str] = Field(None, description="Filter by specific role")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Senior Python developer with React experience",
                "role": "python_developer",
                "limit": 5
            }
        }

class SimilarContentRequest(BaseModel):
    """Request model for similar content search."""
    content: str = Field(..., description="Content to find similar items for")
    content_type: str = Field("questions", description="Type of content to search")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    
    class Config:
        schema_extra = {
            "example": {
                "content": "How do you handle database connections in Python?",
                "content_type": "questions",
                "filters": {
                    "difficulty": "medium",
                    "category": "technical"
                },
                "limit": 5
            }
        }

class QuestionSuggestionRequest(BaseModel):
    """Request model for question suggestions."""
    job_description: str = Field(..., description="Job description text")
    role: str = Field(..., description="Job role")
    difficulty: str = Field("medium", description="Question difficulty level")
    count: int = Field(5, ge=1, le=20, description="Number of questions to suggest")
    
    class Config:
        schema_extra = {
            "example": {
                "job_description": "We are looking for a Senior Python Developer with experience in FastAPI, PostgreSQL, and Docker...",
                "role": "python_developer",
                "difficulty": "medium",
                "count": 5
            }
        }

class RecommendationRequest(BaseModel):
    """Request model for content recommendations."""
    user_id: str = Field(..., description="User ID")
    content_type: str = Field("questions", description="Type of content to recommend")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="User profile information")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of recommendations")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_123",
                "content_type": "questions",
                "user_profile": {
                    "skill_level": "intermediate",
                    "learning_style": "practical",
                    "preferred_categories": ["technical", "behavioral"]
                },
                "limit": 10
            }
        }

class UserPatternRequest(BaseModel):
    """Request model for user pattern analysis."""
    user_id: str = Field(..., description="User ID")
    pattern_data: Dict[str, Any] = Field(..., description="User pattern data")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of similar patterns")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_123",
                "pattern_data": {
                    "skill_level": "intermediate",
                    "performance_trend": 0.75,
                    "learning_style": "practical",
                    "preferred_categories": ["technical"],
                    "strengths": ["python", "fastapi"],
                    "weaknesses": ["system_design"]
                },
                "limit": 10
            }
        }

class SearchResult(BaseModel):
    """Model for search results."""
    id: str = Field(..., description="Result ID")
    score: float = Field(..., description="Similarity score")
    text: str = Field(..., description="Content text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "q_123",
                "score": 0.85,
                "text": "Explain the difference between async and sync programming in Python",
                "metadata": {
                    "difficulty": "medium",
                    "category": "technical",
                    "role": "python_developer"
                }
            }
        }

class QuestionSearchResult(SearchResult):
    """Model for question search results."""
    difficulty: Optional[str] = Field(None, description="Question difficulty")
    category: Optional[str] = Field(None, description="Question category")
    subcategory: Optional[str] = Field(None, description="Question subcategory")
    role: Optional[str] = Field(None, description="Compatible role")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    question_id: Optional[str] = Field(None, description="Original question ID")

class JobSearchResult(SearchResult):
    """Model for job description search results."""
    role: Optional[str] = Field(None, description="Job role")
    company: Optional[str] = Field(None, description="Company name")
    level: Optional[str] = Field(None, description="Experience level")

class UserPattern(BaseModel):
    """Model for user pattern results."""
    id: str = Field(..., description="Pattern ID")
    score: float = Field(..., description="Similarity score")
    user_id: str = Field(..., description="User ID")
    skill_level: Optional[str] = Field(None, description="Skill level")
    performance_trend: Optional[float] = Field(None, description="Performance trend")
    learning_style: Optional[str] = Field(None, description="Learning style")
    pattern_data: Dict[str, Any] = Field(default_factory=dict, description="Pattern data")

class Recommendation(BaseModel):
    """Model for content recommendations."""
    id: str = Field(..., description="Recommendation ID")
    content_type: str = Field(..., description="Type of content")
    title: str = Field(..., description="Content title")
    description: str = Field(..., description="Content description")
    relevance_score: float = Field(..., description="Relevance score")
    source: str = Field(..., description="Recommendation source")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class SearchResponse(BaseModel):
    """Response model for search operations."""
    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    
    class Config:
        schema_extra = {
            "example": {
                "results": [
                    {
                        "id": "q_123",
                        "score": 0.85,
                        "text": "Explain the difference between async and sync programming in Python",
                        "metadata": {
                            "difficulty": "medium",
                            "category": "technical"
                        }
                    }
                ],
                "total": 1,
                "query": "Python async programming",
                "filters": {
                    "difficulty": "medium"
                }
            }
        }

class QuestionSearchResponse(SearchResponse):
    """Response model for question search."""
    results: List[QuestionSearchResult] = Field(..., description="Question search results")

class JobSearchResponse(SearchResponse):
    """Response model for job description search."""
    results: List[JobSearchResult] = Field(..., description="Job search results")

class RecommendationResponse(BaseModel):
    """Response model for recommendations."""
    recommendations: List[Recommendation] = Field(..., description="Content recommendations")
    total: int = Field(..., description="Total number of recommendations")
    user_id: str = Field(..., description="User ID")
    content_type: str = Field(..., description="Content type")

class UserPatternResponse(BaseModel):
    """Response model for user pattern search."""
    patterns: List[UserPattern] = Field(..., description="Similar user patterns")
    total: int = Field(..., description="Total number of patterns")
    user_id: str = Field(..., description="User ID")

class VectorHealthResponse(BaseModel):
    """Response model for vector service health check."""
    status: str = Field(..., description="Service status")
    qdrant: Dict[str, Any] = Field(..., description="Qdrant health info")
    embedding_models: Dict[str, Any] = Field(..., description="Available embedding models")
    collections: Dict[str, Any] = Field(..., description="Collection information")

class EmbeddingRequest(BaseModel):
    """Request model for embedding generation."""
    text: str = Field(..., description="Text to generate embedding for")
    model: Optional[str] = Field(None, description="Embedding model to use")
    use_cache: bool = Field(True, description="Whether to use cached embeddings")
    
    class Config:
        schema_extra = {
            "example": {
                "text": "Python async programming concepts",
                "model": "text-embedding-3-small",
                "use_cache": True
            }
        }

class BatchEmbeddingRequest(BaseModel):
    """Request model for batch embedding generation."""
    texts: List[str] = Field(..., description="List of texts to generate embeddings for")
    model: Optional[str] = Field(None, description="Embedding model to use")
    batch_size: int = Field(100, ge=1, le=1000, description="Batch size for processing")
    
    class Config:
        schema_extra = {
            "example": {
                "texts": [
                    "Python async programming concepts",
                    "FastAPI best practices",
                    "Database connection pooling"
                ],
                "model": "text-embedding-3-small",
                "batch_size": 100
            }
        }

class EmbeddingResponse(BaseModel):
    """Response model for embedding generation."""
    embedding: List[float] = Field(..., description="Generated embedding vector")
    model: str = Field(..., description="Model used for generation")
    text_length: int = Field(..., description="Length of input text")
    cached: bool = Field(False, description="Whether result was cached")

class BatchEmbeddingResponse(BaseModel):
    """Response model for batch embedding generation."""
    embeddings: List[List[float]] = Field(..., description="Generated embedding vectors")
    model: str = Field(..., description="Model used for generation")
    total_texts: int = Field(..., description="Total number of texts processed")
    cached_count: int = Field(0, description="Number of cached results")
