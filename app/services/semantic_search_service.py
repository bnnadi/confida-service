"""
Semantic Search Service

This service provides comprehensive semantic search capabilities leveraging
the vector database for intelligent content discovery and recommendations.
"""
from typing import List, Dict, Any, Optional
from app.services.unified_vector_service import unified_vector_service
from app.services.embedding_service import embedding_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

class SemanticSearchService:
    """Service for semantic search and content recommendations."""
    
    def __init__(self):
        self.vector_service = unified_vector_service
        self.embedding_service = embedding_service
    
    async def search_questions(
        self, 
        query: str, 
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar questions using semantic search."""
        try:
            logger.info("Searching questions with query: '%s...'", query[:100])
            
            # Use vector service to find similar questions
            results = await unified_vector_service.find_similar_questions(
                query=query,
                filters=filters,
                limit=limit
            )
            
            # Apply additional text-based filtering if needed
            if filters and "text_contains" in filters:
                text_filter = filters["text_contains"].lower()
                results = [
                    r for r in results 
                    if text_filter in r.get("text", "").lower()
                ]
            
            # Apply score threshold
            if filters and "min_score" in filters:
                min_score = filters["min_score"]
                results = [r for r in results if r.get("score", 0) >= min_score]
            
            # Sort by score (descending)
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            logger.info("Found %d matching questions", len(results))
            return results
            
        except Exception as e:
            logger.error("❌ Failed to search questions: %s", e)
            raise
    
    async def search_job_descriptions(
        self, 
        query: str, 
        role: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar job descriptions."""
        try:
            logger.info("Searching job descriptions with query: '%s...'", query[:100])
            
            results = await self.vector_service.find_similar_job_descriptions(
                query=query,
                filters={"role": role} if role else None,
                limit=limit
            )
            
            logger.info("Found %d matching job descriptions", len(results))
            return results
            
        except Exception as e:
            logger.error("❌ Failed to search job descriptions: %s", e)
            raise
    
    async def find_user_patterns(
        self, 
        user_id: str, 
        pattern_data: Dict[str, Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar user patterns for recommendations."""
        try:
            logger.info("Finding similar patterns for user %s", user_id)
            
            # Convert pattern_data to query string
            query = f"user pattern: {pattern_data.get('skill_level', 'intermediate')} {pattern_data.get('learning_style', 'practical')} {' '.join(pattern_data.get('preferred_categories', []))}"
            
            results = await self.vector_service.find_similar_user_patterns(
                query=query,
                filters={"user_id": user_id},
                limit=limit
            )
            
            logger.info("Found %d similar user patterns", len(results))
            return results
            
        except Exception as e:
            logger.error("❌ Failed to find user patterns: %s", e)
            raise
    
    async def get_content_recommendations(
        self, 
        user_id: str, 
        content_type: str = "questions",
        user_profile: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized content recommendations based on user patterns."""
        try:
            logger.info("Getting %s recommendations for user %s", content_type, user_id)
            
            # If no user profile provided, create a basic one
            if not user_profile:
                user_profile = {
                    "skill_level": "intermediate",
                    "learning_style": "practical",
                    "preferred_categories": ["technical", "behavioral"]
                }
            
            # Find similar user patterns
            similar_patterns = await self.find_user_patterns(
                user_id=user_id,
                pattern_data=user_profile,
                limit=5
            )
            
            # Generate recommendations based on patterns
            recommendations = []
            
            if content_type == "questions":
                # Get questions from similar users
                for pattern in similar_patterns:
                    pattern_user_id = pattern.get("user_id")
                    if pattern_user_id:
                        # This would typically query a database for questions by user
                        # For now, we'll use semantic search with the user's pattern
                        pattern_questions = await self.search_questions(
                            query=f"questions for {pattern.get('skill_level', 'intermediate')} level",
                            filters={
                                "category": pattern.get("preferred_categories", ["technical"])[0] if pattern.get("preferred_categories") else None
                            },
                            limit=2
                        )
                        
                        # Add source information
                        for q in pattern_questions:
                            q["source"] = "similar_user"
                            q["similarity_score"] = pattern.get("score", 0)
                        
                        recommendations.extend(pattern_questions)
            
            elif content_type == "job_descriptions":
                # Get job descriptions from similar users
                for pattern in similar_patterns:
                    pattern_user_id = pattern.get("user_id")
                    if pattern_user_id:
                        pattern_jobs = await self.search_job_descriptions(
                            query=f"job description for {pattern.get('skill_level', 'intermediate')} level",
                            role=pattern.get("preferred_roles", ["software_engineer"])[0] if pattern.get("preferred_roles") else None,
                            limit=2
                        )
                        
                        # Add source information
                        for j in pattern_jobs:
                            j["source"] = "similar_user"
                            j["similarity_score"] = pattern.get("score", 0)
                        
                        recommendations.extend(pattern_jobs)
            
            # Remove duplicates and rank by relevance
            unique_recommendations = self._deduplicate_recommendations(recommendations)
            ranked_recommendations = self._rank_recommendations(unique_recommendations, user_profile)
            
            logger.info("Generated %d recommendations", len(ranked_recommendations))
            return ranked_recommendations[:limit]
            
        except Exception as e:
            logger.error("❌ Failed to get content recommendations: %s", e)
            raise
    
    async def search_similar_content(
        self, 
        content: str, 
        content_type: str = "questions",
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for content similar to the provided text."""
        try:
            logger.info("Searching similar %s for content: '%s...'", content_type, content[:100])
            
            if content_type == "questions":
                results = await self.search_questions(
                    query=content,
                    filters=filters,
                    limit=limit
                )
            elif content_type == "job_descriptions":
                results = await self.search_job_descriptions(
                    query=content,
                    role=filters.get("role") if filters else None,
                    limit=limit
                )
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
            
            logger.info("Found %d similar %s", len(results), content_type)
            return results
            
        except Exception as e:
            logger.error("❌ Failed to search similar content: %s", e)
            raise
    
    async def get_question_suggestions(
        self, 
        job_description: str, 
        role: str,
        difficulty: str = "medium",
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """Get question suggestions based on job description and role."""
        try:
            logger.info("Getting question suggestions for role '%s' (difficulty: %s)", role, difficulty)
            
            # Search for similar job descriptions first
            similar_jobs = await self.search_job_descriptions(
                query=job_description,
                role=role,
                limit=3
            )
            
            # Extract key terms from similar job descriptions
            key_terms = []
            for job in similar_jobs:
                # Extract skills, technologies, etc. from job descriptions
                # This is a simplified version - in practice, you'd use NLP
                text = job.get("text", "").lower()
                if "python" in text:
                    key_terms.append("python")
                if "javascript" in text:
                    key_terms.append("javascript")
                if "react" in text:
                    key_terms.append("react")
                if "database" in text:
                    key_terms.append("database")
                if "api" in text:
                    key_terms.append("api")
            
            # Search for questions using key terms
            query = f"{' '.join(key_terms[:5])} {role} interview questions"
            
            results = await self.search_questions(
                query=query,
                filters={
                    "difficulty": difficulty,
                    "role": role
                },
                limit=count
            )
            
            # If we don't have enough results, do a broader search
            if len(results) < count:
                broader_results = await self.search_questions(
                    query=job_description,
                    filters={
                        "difficulty": difficulty,
                        "category": "technical"
                    },
                    limit=count - len(results)
                )
                results.extend(broader_results)
            
            logger.info("Generated %d question suggestions", len(results))
            return results[:count]
            
        except Exception as e:
            logger.error("❌ Failed to get question suggestions: %s", e)
            raise
    
    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate recommendations based on content ID or text."""
        seen = set()
        unique_recommendations = []
        
        for rec in recommendations:
            # Use ID if available, otherwise use text hash
            key = rec.get("id") or rec.get("text", "")
            if key not in seen:
                seen.add(key)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _rank_recommendations(
        self, 
        recommendations: List[Dict[str, Any]], 
        user_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank recommendations based on user profile and relevance."""
        def calculate_relevance_score(rec: Dict[str, Any]) -> float:
            score = rec.get("score", 0)  # Base similarity score
            
            # Boost score based on user preferences
            if user_profile.get("skill_level") == rec.get("difficulty"):
                score += 0.1
            
            if user_profile.get("preferred_categories"):
                preferred_cats = user_profile["preferred_categories"]
                if rec.get("category") in preferred_cats:
                    score += 0.2
            
            # Boost score for similar user recommendations
            if rec.get("source") == "similar_user":
                score += rec.get("similarity_score", 0) * 0.1
            
            return score
        
        # Sort by relevance score
        recommendations.sort(key=calculate_relevance_score, reverse=True)
        return recommendations
    
    async def health_check(self) -> Dict[str, Any]:
        """Check semantic search service health."""
        try:
            embedding_models = self.embedding_service.get_available_models()
            
            return {
                "status": "healthy",
                "vector_service": {"status": "available"},
                "embedding_models": embedding_models
            }
            
        except Exception as e:
            logger.error("Semantic search service health check failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global semantic search service instance
semantic_search_service = SemanticSearchService()
