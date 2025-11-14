"""
Request and Response models for Question Bank API endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class QuestionCreateRequest(BaseModel):
    """Request model for creating a new question."""
    question_text: str = Field(..., min_length=5, max_length=2000, description="The question text")
    category: str = Field(..., min_length=1, max_length=100, description="Question category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Question subcategory")
    difficulty_level: str = Field("medium", description="Difficulty level: easy, medium, or hard")
    compatible_roles: Optional[List[str]] = Field(default_factory=list, description="List of compatible roles")
    required_skills: Optional[List[str]] = Field(default_factory=list, description="List of required skills")
    industry_tags: Optional[List[str]] = Field(default_factory=list, description="List of industry tags")
    question_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class QuestionUpdateRequest(BaseModel):
    """Request model for updating an existing question."""
    question_text: Optional[str] = Field(None, min_length=5, max_length=2000, description="The question text")
    category: Optional[str] = Field(None, min_length=1, max_length=100, description="Question category")
    subcategory: Optional[str] = Field(None, max_length=100, description="Question subcategory")
    difficulty_level: Optional[str] = Field(None, description="Difficulty level: easy, medium, or hard")
    compatible_roles: Optional[List[str]] = Field(None, description="List of compatible roles")
    required_skills: Optional[List[str]] = Field(None, description="List of required skills")
    industry_tags: Optional[List[str]] = Field(None, description="List of industry tags")
    question_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class QuestionResponse(BaseModel):
    """Response model for question data."""
    id: str = Field(..., description="Question UUID")
    question_text: str = Field(..., description="The question text")
    category: str = Field(..., description="Question category")
    subcategory: Optional[str] = Field(None, description="Question subcategory")
    difficulty_level: str = Field(..., description="Difficulty level")
    compatible_roles: List[str] = Field(default_factory=list, description="List of compatible roles")
    required_skills: List[str] = Field(default_factory=list, description="List of required skills")
    industry_tags: List[str] = Field(default_factory=list, description="List of industry tags")
    usage_count: int = Field(0, description="Number of times this question has been used")
    average_score: Optional[float] = Field(None, description="Average score for this question")
    success_rate: Optional[float] = Field(None, description="Success rate for this question")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    question_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        from_attributes = True


class QuestionFilters(BaseModel):
    """Filter model for question search."""
    category: Optional[str] = Field(None, description="Filter by category")
    difficulty_level: Optional[str] = Field(None, description="Filter by difficulty level")
    compatible_roles: Optional[List[str]] = Field(None, description="Filter by compatible roles")
    required_skills: Optional[List[str]] = Field(None, description="Filter by required skills")
    industry_tags: Optional[List[str]] = Field(None, description="Filter by industry tags")
    min_usage_count: Optional[int] = Field(None, ge=0, description="Minimum usage count")
    min_success_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum success rate")
    min_average_score: Optional[float] = Field(None, ge=0.0, description="Minimum average score")


class QuestionBulkUpdateRequest(BaseModel):
    """Request model for bulk updating questions."""
    question_id: str = Field(..., description="Question UUID")
    question_text: Optional[str] = Field(None, min_length=5, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    difficulty_level: Optional[str] = Field(None)
    compatible_roles: Optional[List[str]] = Field(None)
    required_skills: Optional[List[str]] = Field(None)
    industry_tags: Optional[List[str]] = Field(None)
    question_metadata: Optional[Dict[str, Any]] = Field(None)


class QuestionSuggestion(BaseModel):
    """Response model for question suggestions."""
    id: str = Field(..., description="Question UUID")
    question_text: str = Field(..., description="The question text")
    category: str = Field(..., description="Question category")
    difficulty_level: str = Field(..., description="Difficulty level")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score for the role/job description")
    compatible_roles: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class QuestionPerformanceResponse(BaseModel):
    """Response model for question performance analytics."""
    question_id: Optional[str] = Field(None, description="Question ID if filtering by specific question")
    category: Optional[str] = Field(None, description="Category if filtering by category")
    time_period: str = Field(..., description="Time period for analytics")
    total_uses: int = Field(0, description="Total number of times question(s) were used")
    average_score: Optional[float] = Field(None, description="Average score")
    success_rate: Optional[float] = Field(None, description="Success rate")
    performance_trend: Optional[List[Dict[str, Any]]] = Field(None, description="Performance trend over time")


class QuestionUsageResponse(BaseModel):
    """Response model for question usage statistics."""
    time_period: str = Field(..., description="Time period for statistics")
    total_questions: int = Field(0, description="Total questions in bank")
    total_uses: int = Field(0, description="Total question uses")
    most_used_questions: List[Dict[str, Any]] = Field(default_factory=list, description="Most frequently used questions")
    least_used_questions: List[Dict[str, Any]] = Field(default_factory=list, description="Least frequently used questions")
    usage_by_category: Dict[str, int] = Field(default_factory=dict, description="Usage count by category")
    usage_by_difficulty: Dict[str, int] = Field(default_factory=dict, description="Usage count by difficulty")


class SystemOverviewResponse(BaseModel):
    """Response model for system overview analytics."""
    total_questions: int = Field(0, description="Total questions in bank")
    questions_by_category: Dict[str, int] = Field(default_factory=dict, description="Question count by category")
    questions_by_difficulty: Dict[str, int] = Field(default_factory=dict, description="Question count by difficulty")
    total_uses: int = Field(0, description="Total question uses")
    average_success_rate: Optional[float] = Field(None, description="Average success rate across all questions")
    top_performing_questions: List[Dict[str, Any]] = Field(default_factory=list, description="Top performing questions")
    recent_activity: Optional[List[Dict[str, Any]]] = Field(None, description="Recent question activity")


class BulkImportResponse(BaseModel):
    """Response model for bulk import operations."""
    imported_count: int = Field(0, description="Number of questions successfully imported")
    failed_count: int = Field(0, description="Number of questions that failed to import")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class BulkUpdateResponse(BaseModel):
    """Response model for bulk update operations."""
    updated_count: int = Field(0, description="Number of questions successfully updated")
    failed_count: int = Field(0, description="Number of questions that failed to update")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class QualityCheckResponse(BaseModel):
    """Response model for quality check operations."""
    total_questions: int = Field(0, description="Total questions checked")
    issues_found: int = Field(0, description="Number of issues found")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="List of quality issues")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")

