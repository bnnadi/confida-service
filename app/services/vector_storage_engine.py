"""
Vector Storage Engine for unified content storage.
Eliminates massive code duplication in vector service methods.
"""

import uuid
from typing import Dict, Any, List, Optional
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue
from app.utils.logger import get_logger

logger = get_logger(__name__)

class VectorStorageEngine:
    """Unified engine for vector content storage with type-specific metadata handling."""
    
    def __init__(self, qdrant_client, embedding_service):
        self.qdrant = qdrant_client
        self.embedding_service = embedding_service
        
        # Type-specific metadata field mappings
        self.metadata_mappings = {
            "answer": {"user_id", "question_id", "session_id", "score"},
            "user_pattern": {"user_id", "skill_level", "performance_trend", "learning_style"},
            "job_description": {"role"},
            "question": {"category", "difficulty_level", "tags"},
            "session": {"user_id", "session_type", "status"}
        }
    
    async def store_content(self, content: str, collection_name: str, 
                          content_type: str, metadata: Dict[str, Any] = None) -> str:
        """Unified content storage with type-specific metadata handling."""
        try:
            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(content)
            point_id = str(uuid.uuid4())
            
            # Build type-specific payload
            payload = self._build_payload(content_type, content, metadata or {})
            
            # Create and store point
            point = PointStruct(id=point_id, vector=embedding, payload=payload)
            
            self.qdrant.get_client().upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.info(f"✅ Stored {content_type} in {collection_name} (ID: {point_id})")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store {content_type}: {e}")
            raise
    
    def _build_payload(self, content_type: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload based on content type with relevant metadata fields."""
        # Base payload with common fields
        base_payload = {
            "text": content,
            "content_type": content_type,
            "created_at": metadata.get("created_at")
        }
        
        # Add type-specific metadata fields
        relevant_fields = self.metadata_mappings.get(content_type, set())
        type_specific_metadata = {
            k: v for k, v in metadata.items() 
            if k in relevant_fields
        }
        
        return {**base_payload, **type_specific_metadata}
    
    async def search_similar_content(self, query: str, collection_name: str, 
                                   filters: Dict[str, Any] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Unified semantic search with optional filters."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build search filter if provided
            search_filter = self._build_search_filter(filters) if filters else None
            
            # Perform search
            results = self.qdrant.get_client().search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            return self._format_search_results(results)
            
        except Exception as e:
            logger.error(f"❌ Failed to search {collection_name}: {e}")
            raise
    
    def _build_search_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from simple key-value pairs."""
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Handle list values (e.g., multiple roles)
                for v in value:
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=v)))
            else:
                # Handle single values
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        
        return Filter(must=conditions) if conditions else None
    
    def _format_search_results(self, results) -> List[Dict[str, Any]]:
        """Format search results into consistent structure."""
        formatted_results = []
        
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "metadata": {k: v for k, v in result.payload.items() if k != "text"}
            })
        
        return formatted_results

class VectorContentManager:
    """High-level manager for different types of vector content."""
    
    def __init__(self, storage_engine: VectorStorageEngine):
        self.storage = storage_engine
    
    async def store_job_description(self, job_description: str, role: str, 
                                  metadata: Dict[str, Any] = None) -> str:
        """Store job description with role metadata."""
        return await self.storage.store_content(
            content=job_description,
            collection_name="job_descriptions",
            content_type="job_description",
            metadata={**(metadata or {}), "role": role}
        )
    
    async def store_answer(self, answer_text: str, metadata: Dict[str, Any]) -> str:
        """Store answer with user and session metadata."""
        return await self.storage.store_content(
            content=answer_text,
            collection_name="answers",
            content_type="answer",
            metadata=metadata
        )
    
    async def store_user_pattern(self, user_id: str, pattern_data: Dict[str, Any]) -> str:
        """Store user pattern for recommendations."""
        pattern_text = self._generate_pattern_text(pattern_data)
        return await self.storage.store_content(
            content=pattern_text,
            collection_name="user_patterns",
            content_type="user_pattern",
            metadata={**pattern_data, "user_id": user_id}
        )
    
    async def store_question(self, question_text: str, metadata: Dict[str, Any]) -> str:
        """Store question with category and difficulty metadata."""
        return await self.storage.store_content(
            content=question_text,
            collection_name="questions",
            content_type="question",
            metadata=metadata
        )
    
    async def find_similar_job_descriptions(self, query: str, role: str = None, 
                                          limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar job descriptions with optional role filter."""
        filters = {"role": role} if role else None
        return await self.storage.search_similar_content(
            query=query,
            collection_name="job_descriptions",
            filters=filters,
            limit=limit
        )
    
    async def find_similar_answers(self, query: str, user_id: str = None, 
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar answers with optional user filter."""
        filters = {"user_id": user_id} if user_id else None
        return await self.storage.search_similar_content(
            query=query,
            collection_name="answers",
            filters=filters,
            limit=limit
        )
    
    async def find_similar_user_patterns(self, user_id: str, pattern_data: Dict[str, Any], 
                                       limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar user patterns excluding current user."""
        pattern_text = self._generate_pattern_text(pattern_data)
        filters = {"user_id": {"$ne": user_id}}  # Exclude current user
        
        return await self.storage.search_similar_content(
            query=pattern_text,
            collection_name="user_patterns",
            filters=filters,
            limit=limit
        )
    
    def _generate_pattern_text(self, pattern_data: Dict[str, Any]) -> str:
        """Generate text representation of user pattern for embedding."""
        components = []
        
        if skill_level := pattern_data.get("skill_level"):
            components.append(f"skill level: {skill_level}")
        
        if performance_trend := pattern_data.get("performance_trend"):
            components.append(f"performance: {performance_trend}")
        
        if learning_style := pattern_data.get("learning_style"):
            components.append(f"learning style: {learning_style}")
        
        return " ".join(components) if components else "general pattern"
