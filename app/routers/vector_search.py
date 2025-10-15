"""
Vector Search API Endpoints

This module provides REST API endpoints for vector search and semantic search capabilities.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.semantic_search_service import semantic_search_service
from app.services.vector_service import vector_service
from app.services.embedding_service import embedding_service
from app.models.vector_models import (
    QuestionSearchRequest, QuestionSearchResponse,
    JobSearchRequest, JobSearchResponse,
    SimilarContentRequest, SearchResponse,
    QuestionSuggestionRequest, SearchResponse as QuestionSuggestionResponse,
    RecommendationRequest, RecommendationResponse,
    UserPatternRequest, UserPatternResponse,
    VectorHealthResponse,
    EmbeddingRequest, EmbeddingResponse,
    BatchEmbeddingRequest, BatchEmbeddingResponse
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/vector", tags=["vector-search"])

@router.post("/search/questions", response_model=QuestionSearchResponse)
async def search_questions(request: QuestionSearchRequest):
    """Search for similar questions using semantic search."""
    try:
        results = await semantic_search_service.search_questions(
            query=request.query,
            filters=request.filters,
            limit=request.limit
        )
        
        return QuestionSearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            filters=request.filters
        )
        
    except Exception as e:
        logger.error(f"Failed to search questions: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/search/job-descriptions", response_model=JobSearchResponse)
async def search_job_descriptions(request: JobSearchRequest):
    """Search for similar job descriptions."""
    try:
        results = await semantic_search_service.search_job_descriptions(
            query=request.query,
            role=request.role,
            limit=request.limit
        )
        
        return JobSearchResponse(
            results=results,
            total=len(results),
            query=request.query,
            filters={"role": request.role} if request.role else None
        )
        
    except Exception as e:
        logger.error(f"Failed to search job descriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/search/similar", response_model=SearchResponse)
async def search_similar_content(request: SimilarContentRequest):
    """Search for content similar to the provided text."""
    try:
        results = await semantic_search_service.search_similar_content(
            content=request.content,
            content_type=request.content_type,
            filters=request.filters,
            limit=request.limit
        )
        
        return SearchResponse(
            results=results,
            total=len(results),
            query=request.content,
            filters=request.filters
        )
        
    except Exception as e:
        logger.error(f"Failed to search similar content: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/suggestions/questions", response_model=SearchResponse)
async def get_question_suggestions(request: QuestionSuggestionRequest):
    """Get question suggestions based on job description and role."""
    try:
        results = await semantic_search_service.get_question_suggestions(
            job_description=request.job_description,
            role=request.role,
            difficulty=request.difficulty,
            count=request.count
        )
        
        return SearchResponse(
            results=results,
            total=len(results),
            query=request.job_description,
            filters={
                "role": request.role,
                "difficulty": request.difficulty
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get question suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")

@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Get personalized content recommendations."""
    try:
        recommendations = await semantic_search_service.get_content_recommendations(
            user_id=request.user_id,
            content_type=request.content_type,
            user_profile=request.user_profile,
            limit=request.limit
        )
        
        return RecommendationResponse(
            recommendations=recommendations,
            total=len(recommendations),
            user_id=request.user_id,
            content_type=request.content_type
        )
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")

@router.post("/patterns/similar", response_model=UserPatternResponse)
async def find_similar_user_patterns(request: UserPatternRequest):
    """Find similar user patterns for recommendations."""
    try:
        patterns = await semantic_search_service.find_user_patterns(
            user_id=request.user_id,
            pattern_data=request.pattern_data,
            limit=request.limit
        )
        
        return UserPatternResponse(
            patterns=patterns,
            total=len(patterns),
            user_id=request.user_id
        )
        
    except Exception as e:
        logger.error(f"Failed to find similar user patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Pattern search failed: {str(e)}")

@router.post("/embeddings/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for text."""
    try:
        embedding = await embedding_service.generate_embedding(
            text=request.text,
            model=request.model,
            use_cache=request.use_cache
        )
        
        return EmbeddingResponse(
            embedding=embedding,
            model=request.model or embedding_service.default_model,
            text_length=len(request.text),
            cached=False  # Would need to track this in the service
        )
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@router.post("/embeddings/batch", response_model=BatchEmbeddingResponse)
async def generate_batch_embeddings(request: BatchEmbeddingRequest):
    """Generate embeddings for multiple texts."""
    try:
        embeddings = await embedding_service.generate_batch_embeddings(
            texts=request.texts,
            model=request.model,
            batch_size=request.batch_size
        )
        
        return BatchEmbeddingResponse(
            embeddings=embeddings,
            model=request.model or embedding_service.default_model,
            total_texts=len(request.texts),
            cached_count=0  # Would need to track this in the service
        )
        
    except Exception as e:
        logger.error(f"Failed to generate batch embeddings: {e}")
        raise HTTPException(status_code=500, detail=f"Batch embedding generation failed: {str(e)}")

@router.get("/health", response_model=VectorHealthResponse)
async def vector_health_check():
    """Check vector service health."""
    try:
        health = await semantic_search_service.health_check()
        return VectorHealthResponse(**health)
        
    except Exception as e:
        logger.error(f"Vector health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/collections")
async def get_collections_info():
    """Get information about vector collections."""
    try:
        stats = await vector_service.get_collection_stats()
        return {
            "collections": stats,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get collections info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get collections info: {str(e)}")

@router.get("/models")
async def get_available_models():
    """Get information about available embedding models."""
    try:
        models = embedding_service.get_available_models()
        return {
            "models": models,
            "default_model": embedding_service.default_model,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@router.post("/collections/initialize")
async def initialize_collections():
    """Initialize all vector collections."""
    try:
        await vector_service.initialize_collections()
        return {
            "message": "Collections initialized successfully",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize collections: {e}")
        raise HTTPException(status_code=500, detail=f"Collection initialization failed: {str(e)}")

@router.get("/search/quick")
async def quick_search(
    query: str = Query(..., description="Search query"),
    content_type: str = Query("questions", description="Type of content to search"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results")
):
    """Quick search endpoint for simple queries."""
    try:
        if content_type == "questions":
            results = await semantic_search_service.search_questions(
                query=query,
                limit=limit
            )
        elif content_type == "job_descriptions":
            results = await semantic_search_service.search_job_descriptions(
                query=query,
                limit=limit
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported content type: {content_type}")
        
        return {
            "results": results,
            "total": len(results),
            "query": query,
            "content_type": content_type
        }
        
    except Exception as e:
        logger.error(f"Quick search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")
