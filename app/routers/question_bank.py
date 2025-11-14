"""
Question Bank API Endpoints

Provides comprehensive API for question bank management, including CRUD operations,
analytics, and admin functionality.
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func

from app.services.database_service import get_db
from app.services.question_bank_service import QuestionBankService
from app.services.question_analytics_service import QuestionAnalyticsService
from app.middleware.auth_middleware import get_current_user_required, get_current_admin
from app.models.question_requests import (
    QuestionCreateRequest,
    QuestionUpdateRequest,
    QuestionResponse,
    QuestionFilters,
    QuestionSuggestion,
    QuestionPerformanceResponse,
    QuestionUsageResponse,
    SystemOverviewResponse,
    BulkImportResponse,
    BulkUpdateResponse,
    QuestionBulkUpdateRequest,
    QualityCheckResponse
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/questions", tags=["question-bank"])


def _question_to_response(question) -> QuestionResponse:
    """Convert Question model to QuestionResponse."""
    return QuestionResponse(
        id=str(question.id),
        question_text=question.question_text,
        category=question.category,
        subcategory=question.subcategory,
        difficulty_level=question.difficulty_level,
        compatible_roles=question.compatible_roles or [],
        required_skills=question.required_skills or [],
        industry_tags=question.industry_tags or [],
        usage_count=question.usage_count,
        average_score=question.average_score,
        success_rate=question.success_rate,
        created_at=question.created_at,
        updated_at=question.updated_at,
        question_metadata=question.question_metadata or {}
    )


# CRUD Endpoints

@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    question_data: QuestionCreateRequest,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new question in the question bank.
    
    Requires admin authentication.
    """
    try:
        service = QuestionBankService(db)
        question = service.create_question(question_data)
        db.commit()
        return _question_to_response(question)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating question: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create question"
        )


@router.get("", response_model=List[QuestionResponse])
async def get_questions(
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty level"),
    compatible_roles: Optional[List[str]] = Query(None, description="Filter by compatible roles"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Get questions with filtering and pagination.
    
    Supports filtering by category, difficulty level, and compatible roles.
    """
    try:
        service = QuestionBankService(db)
        questions = service.get_questions(
            category=category,
            difficulty_level=difficulty_level,
            compatible_roles=compatible_roles,
            limit=limit,
            offset=offset
        )
        return [_question_to_response(q) for q in questions]
    except Exception as e:
        logger.error(f"Error getting questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve questions"
        )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific question by ID.
    """
    try:
        service = QuestionBankService(db)
        question = service.get_question_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        return _question_to_response(question)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve question"
        )


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: str,
    question_data: QuestionUpdateRequest,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing question.
    
    Requires admin authentication.
    """
    try:
        service = QuestionBankService(db)
        question = service.update_question(question_id, question_data)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        db.commit()
        return _question_to_response(question)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating question: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update question"
        )


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a question from the question bank.
    
    Requires admin authentication.
    Cannot delete questions that are linked to sessions.
    """
    try:
        service = QuestionBankService(db)
        success = service.delete_question(question_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        db.commit()
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting question: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete question"
        )


# Search and Filtering Endpoints

@router.get("/search", response_model=List[QuestionResponse])
async def search_questions(
    query: str = Query(..., min_length=1, description="Search query text"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty_level: Optional[str] = Query(None, description="Filter by difficulty level"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Search questions with advanced filtering.
    
    Performs text search on question text and supports additional filters.
    """
    try:
        filters = QuestionFilters(
            category=category,
            difficulty_level=difficulty_level
        )
        service = QuestionBankService(db)
        questions = service.search_questions(
            query_text=query,
            filters=filters,
            limit=limit,
            offset=offset
        )
        return [_question_to_response(q) for q in questions]
    except Exception as e:
        logger.error(f"Error searching questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search questions"
        )


@router.get("/suggestions", response_model=List[QuestionSuggestion])
async def get_question_suggestions(
    role: str = Query(..., min_length=1, description="Job role"),
    job_description: str = Query(..., min_length=10, description="Job description"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    db: Session = Depends(get_db)
):
    """
    Get question suggestions for a specific role and job description.
    
    Returns questions that are most relevant to the given role and job description.
    """
    try:
        service = QuestionBankService(db)
        suggestions = service.get_question_suggestions(
            role=role,
            job_description=job_description,
            limit=limit
        )
        return [
            QuestionSuggestion(
                id=str(q.id),
                question_text=q.question_text,
                category=q.category,
                difficulty_level=q.difficulty_level,
                relevance_score=0.8,  # Could be enhanced with actual relevance scoring
                compatible_roles=q.compatible_roles or [],
                required_skills=q.required_skills or []
            )
            for q in suggestions
        ]
    except Exception as e:
        logger.error(f"Error getting question suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get question suggestions"
        )


# Analytics Endpoints

@router.get("/analytics/performance", response_model=QuestionPerformanceResponse)
async def get_question_performance(
    question_id: Optional[str] = Query(None, description="Specific question ID"),
    category: Optional[str] = Query(None, description="Category filter"),
    time_period: str = Query("30d", description="Time period (e.g., 7d, 30d, 90d)"),
    db: Session = Depends(get_db)
):
    """
    Get question performance analytics.
    
    Returns performance metrics for questions, optionally filtered by question ID or category.
    """
    try:
        analytics = QuestionAnalyticsService(db)
        performance_data = analytics.get_question_performance(
            question_id=question_id,
            category=category,
            time_period=time_period
        )
        return QuestionPerformanceResponse(**performance_data)
    except Exception as e:
        logger.error(f"Error getting question performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get question performance"
        )


@router.get("/analytics/usage", response_model=QuestionUsageResponse)
async def get_question_usage_stats(
    time_period: str = Query("30d", description="Time period (e.g., 7d, 30d, 90d)"),
    db: Session = Depends(get_db)
):
    """
    Get question usage statistics.
    
    Returns usage statistics including most used questions, usage by category, etc.
    """
    try:
        analytics = QuestionAnalyticsService(db)
        usage_stats = analytics.get_usage_stats(time_period)
        return QuestionUsageResponse(**usage_stats)
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage statistics"
        )


@router.get("/analytics/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    db: Session = Depends(get_db)
):
    """
    Get system overview analytics.
    
    Returns comprehensive overview of the question bank including totals, distributions, and top performers.
    """
    try:
        analytics = QuestionAnalyticsService(db)
        overview = analytics.get_system_overview()
        return SystemOverviewResponse(**overview)
    except Exception as e:
        logger.error(f"Error getting system overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system overview"
        )


# Admin Endpoints

@router.post("/admin/bulk-import", response_model=BulkImportResponse)
async def bulk_import_questions(
    questions_data: List[QuestionCreateRequest],
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Bulk import questions from JSON.
    
    Requires admin authentication.
    """
    try:
        service = QuestionBankService(db)
        results = service.bulk_import_questions(questions_data)
        return BulkImportResponse(**results)
    except Exception as e:
        logger.error(f"Error bulk importing questions: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk import questions"
        )


@router.post("/admin/bulk-update", response_model=BulkUpdateResponse)
async def bulk_update_questions(
    updates: List[QuestionBulkUpdateRequest],
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Bulk update questions.
    
    Requires admin authentication.
    """
    try:
        service = QuestionBankService(db)
        # Convert to dict format expected by service
        update_dicts = [
            {
                "question_id": update.question_id,
                "question_text": update.question_text,
                "category": update.category,
                "subcategory": update.subcategory,
                "difficulty_level": update.difficulty_level,
                "compatible_roles": update.compatible_roles,
                "required_skills": update.required_skills,
                "industry_tags": update.industry_tags,
                "question_metadata": update.question_metadata
            }
            for update in updates
        ]
        results = service.bulk_update_questions(update_dicts)
        return BulkUpdateResponse(**results)
    except Exception as e:
        logger.error(f"Error bulk updating questions: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk update questions"
        )


@router.post("/admin/quality-check", response_model=QualityCheckResponse)
async def run_quality_check(
    current_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Run quality check on all questions.
    
    Requires admin authentication.
    Checks for issues like missing metadata, low usage, etc.
    """
    try:
        from app.utils.question_bank_utils import QuestionBankUtils
        
        # Find duplicate questions
        duplicates = QuestionBankUtils.find_duplicate_questions(db)
        
        # Find questions with missing metadata
        from app.database.models import Question
        from sqlalchemy import select, or_
        missing_metadata = db.execute(
            select(Question).where(
                or_(
                    Question.category.is_(None),
                    Question.difficulty_level.is_(None),
                    Question.compatible_roles.is_(None)
                )
            )
        ).scalars().all()
        
        issues = []
        if duplicates:
            issues.append({
                "type": "duplicates",
                "count": len(duplicates),
                "description": f"Found {len(duplicates)} duplicate question groups"
            })
        
        if missing_metadata:
            issues.append({
                "type": "missing_metadata",
                "count": len(missing_metadata),
                "description": f"Found {len(missing_metadata)} questions with missing metadata"
            })
        
        recommendations = []
        if duplicates:
            recommendations.append("Consider removing duplicate questions to improve question bank quality")
        if missing_metadata:
            recommendations.append("Fill in missing metadata for better question categorization and search")
        
        total_questions = db.execute(select(func.count(Question.id))).scalar() or 0
        
        return QualityCheckResponse(
            total_questions=total_questions,
            issues_found=len(issues),
            issues=issues,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"Error running quality check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run quality check"
        )

