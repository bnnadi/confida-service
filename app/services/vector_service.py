"""
Vector Service for Qdrant Operations

This service provides high-level operations for vector database interactions,
including storing, searching, and managing vector embeddings in Qdrant.
"""
import uuid
from typing import List, Dict, Any, Optional, Tuple
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue, SearchRequest
from app.database.qdrant_config import qdrant_config
from app.services.embedding_service import embedding_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

class VectorService:
    """Service for vector database operations using Qdrant."""
    
    def __init__(self):
        self.qdrant = qdrant_config
        self.embedding_service = embedding_service
    
    async def initialize_collections(self):
        """Initialize all required vector collections."""
        try:
            await self.qdrant.create_collections()
            logger.info("✅ Vector collections initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize vector collections: {e}")
            raise
    
    # Generic Vector Storage Operations
    async def _store_vector_content(
        self, 
        content: str, 
        collection_name: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Generic vector storage method to reduce code duplication."""
        try:
            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(content)
            
            # Create point
            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": content,
                    "created_at": metadata.get("created_at"),
                    **(metadata or {})
                }
            )
            
            # Store in Qdrant
            self.qdrant.get_client().upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"✅ Stored content in {collection_name} (ID: {point_id})")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store content in {collection_name}: {e}")
            raise
    
    # Job Description Operations
    async def store_job_description(
        self, 
        job_description: str, 
        role: str, 
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store job description embedding in vector database."""
        return await self._store_vector_content(
            content=job_description,
            collection_name="job_descriptions",
            metadata={**metadata, "role": role} if metadata else {"role": role}
        )
    
    async def find_similar_job_descriptions(
        self, 
        query: str, 
        role: str = None, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar job descriptions using semantic search."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = None
            if role:
                search_filter = Filter(
                    must=[
                        FieldCondition(key="role", match=MatchValue(value=role))
                    ]
                )
            
            # Search
            results = self.qdrant.get_client().search(
                collection_name="job_descriptions",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            similar_jobs = []
            for result in results:
                similar_jobs.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                    "role": result.payload.get("role"),
                    "metadata": {k: v for k, v in result.payload.items() if k not in ["text", "role"]}
                })
            
            logger.info(f"Found {len(similar_jobs)} similar job descriptions")
            return similar_jobs
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar job descriptions: {e}")
            raise
    
    # Question Operations
    async def store_question(
        self, 
        question_text: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store question embedding in vector database."""
        # Prepare question-specific metadata
        question_metadata = {
            "difficulty": metadata.get("difficulty_level", "medium"),
            "category": metadata.get("category", "general"),
            "subcategory": metadata.get("subcategory"),
            "role": metadata.get("compatible_roles", [])[0] if metadata.get("compatible_roles") else None,
            "skills": metadata.get("required_skills", []),
            "question_id": metadata.get("question_id"),
            **metadata
        }
        
        return await self._store_vector_content(
            content=question_text,
            collection_name="questions",
            metadata=question_metadata
        )
    
    async def find_similar_questions(
        self, 
        query: str, 
        filters: Dict[str, Any] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar questions using semantic search."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = self._build_question_filter(filters)
            
            # Search
            results = self.qdrant.get_client().search(
                collection_name="questions",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            similar_questions = []
            for result in results:
                similar_questions.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                    "difficulty": result.payload.get("difficulty"),
                    "category": result.payload.get("category"),
                    "subcategory": result.payload.get("subcategory"),
                    "role": result.payload.get("role"),
                    "skills": result.payload.get("skills", []),
                    "question_id": result.payload.get("question_id"),
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["text", "difficulty", "category", "subcategory", "role", "skills", "question_id"]}
                })
            
            logger.info(f"Found {len(similar_questions)} similar questions")
            return similar_questions
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar questions: {e}")
            raise
    
    # Answer Operations
    async def store_answer(
        self, 
        answer_text: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store answer embedding in vector database."""
        try:
            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(answer_text)
            
            # Create point
            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": answer_text,
                    "user_id": metadata.get("user_id"),
                    "question_id": metadata.get("question_id"),
                    "session_id": metadata.get("session_id"),
                    "score": metadata.get("score"),
                    "created_at": metadata.get("created_at"),
                    **metadata
                }
            )
            
            # Store in Qdrant
            self.qdrant.get_client().upsert(
                collection_name="answers",
                points=[point]
            )
            
            logger.info(f"✅ Stored answer (ID: {point_id})")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store answer: {e}")
            raise
    
    # User Pattern Operations
    async def store_user_pattern(
        self, 
        user_id: str, 
        pattern_data: Dict[str, Any]
    ) -> str:
        """Store user pattern embedding for recommendations."""
        try:
            # Generate pattern text for embedding
            pattern_text = self._generate_pattern_text(pattern_data)
            embedding = await self.embedding_service.generate_embedding(pattern_text)
            
            # Create point
            point_id = str(uuid.uuid4())
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "skill_level": pattern_data.get("skill_level"),
                    "performance_trend": pattern_data.get("performance_trend"),
                    "learning_style": pattern_data.get("learning_style"),
                    "created_at": pattern_data.get("created_at"),
                    "pattern_data": pattern_data
                }
            )
            
            # Store in Qdrant
            self.qdrant.get_client().upsert(
                collection_name="user_patterns",
                points=[point]
            )
            
            logger.info(f"✅ Stored user pattern for user {user_id} (ID: {point_id})")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store user pattern: {e}")
            raise
    
    async def find_similar_user_patterns(
        self, 
        user_id: str, 
        pattern_data: Dict[str, Any], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar user patterns for recommendations."""
        try:
            # Generate pattern text for embedding
            pattern_text = self._generate_pattern_text(pattern_data)
            query_embedding = await self.embedding_service.generate_embedding(pattern_text)
            
            # Search for similar patterns (excluding current user)
            search_filter = Filter(
                must_not=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                ]
            )
            
            results = self.qdrant.get_client().search(
                collection_name="user_patterns",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            similar_patterns = []
            for result in results:
                similar_patterns.append({
                    "id": result.id,
                    "score": result.score,
                    "user_id": result.payload.get("user_id"),
                    "skill_level": result.payload.get("skill_level"),
                    "performance_trend": result.payload.get("performance_trend"),
                    "learning_style": result.payload.get("learning_style"),
                    "pattern_data": result.payload.get("pattern_data", {})
                })
            
            logger.info(f"Found {len(similar_patterns)} similar user patterns")
            return similar_patterns
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar user patterns: {e}")
            raise
    
    # Utility Methods
    def _build_question_filter(self, filters: Dict[str, Any] = None) -> Optional[Filter]:
        """Build Qdrant filter from search filters."""
        if not filters:
            return None
        
        conditions = []
        
        if "difficulty" in filters:
            conditions.append(
                FieldCondition(key="difficulty", match=MatchValue(value=filters["difficulty"]))
            )
        
        if "category" in filters:
            conditions.append(
                FieldCondition(key="category", match=MatchValue(value=filters["category"]))
            )
        
        if "subcategory" in filters:
            conditions.append(
                FieldCondition(key="subcategory", match=MatchValue(value=filters["subcategory"]))
            )
        
        if "role" in filters:
            conditions.append(
                FieldCondition(key="role", match=MatchValue(value=filters["role"]))
            )
        
        if "skills" in filters and isinstance(filters["skills"], list):
            for skill in filters["skills"]:
                conditions.append(
                    FieldCondition(key="skills", match=MatchValue(value=skill))
                )
        
        return Filter(must=conditions) if conditions else None
    
    def _generate_pattern_text(self, pattern_data: Dict[str, Any]) -> str:
        """Generate text representation of user pattern for embedding."""
        parts = []
        
        if "skill_level" in pattern_data:
            parts.append(f"Skill level: {pattern_data['skill_level']}")
        
        if "performance_trend" in pattern_data:
            parts.append(f"Performance trend: {pattern_data['performance_trend']}")
        
        if "learning_style" in pattern_data:
            parts.append(f"Learning style: {pattern_data['learning_style']}")
        
        if "preferred_categories" in pattern_data:
            parts.append(f"Preferred categories: {', '.join(pattern_data['preferred_categories'])}")
        
        if "strengths" in pattern_data:
            parts.append(f"Strengths: {', '.join(pattern_data['strengths'])}")
        
        if "weaknesses" in pattern_data:
            parts.append(f"Areas for improvement: {', '.join(pattern_data['weaknesses'])}")
        
        return " | ".join(parts)
    
    # Health and Status Methods
    async def health_check(self) -> Dict[str, Any]:
        """Check vector service health."""
        try:
            qdrant_health = self.qdrant.health_check()
            embedding_models = self.embedding_service.get_available_models()
            
            return {
                "status": "healthy" if qdrant_health["status"] == "healthy" else "unhealthy",
                "qdrant": qdrant_health,
                "embedding_models": embedding_models,
                "collections": self.qdrant.get_all_collections_info()
            }
            
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections."""
        try:
            stats = {}
            for collection_name in self.qdrant.COLLECTIONS.keys():
                stats[collection_name] = self.qdrant.get_collection_info(collection_name)
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


# Global vector service instance
vector_service = VectorService()
