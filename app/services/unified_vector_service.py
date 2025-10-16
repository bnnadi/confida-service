"""
Unified Vector Service for Confida

This service combines high-level vector operations, storage engine functionality,
and content management capabilities, eliminating the need for separate VectorService,
VectorStorageEngine, and VectorContentManager classes.
"""
import uuid
import inspect
from typing import List, Dict, Any, Optional, Tuple, Type
from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue, SearchRequest
from app.database.qdrant_config import qdrant_config
from app.services.embedding_service import embedding_service
from app.utils.logger import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)


class UnifiedVectorService:
    """Unified service for vector database operations with integrated storage engine and content management."""
    
    def __init__(self):
        self.qdrant = qdrant_config
        self.embedding_service = embedding_service
        
        # Auto-generate metadata mappings from Pydantic models
        self.metadata_mappings = self._generate_metadata_mappings()
        
        # Content type to model mapping for auto-generation
        self.content_models = {
            "answer": self._get_answer_model(),
            "user_pattern": self._get_user_pattern_model(),
            "job_description": self._get_job_description_model(),
            "question": self._get_question_model(),
            "session": self._get_session_model()
        }
    
    # Collection Management
    async def initialize_collections(self):
        """Initialize all required vector collections."""
        try:
            await self.qdrant.create_collections()
            logger.info("✅ Vector collections initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize vector collections: {e}")
            raise
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections."""
        try:
            collections = ["questions", "answers", "job_descriptions", "user_patterns", "sessions"]
            stats = {}
            
            for collection in collections:
                try:
                    collection_info = self.qdrant.get_client().get_collection(collection)
                    stats[collection] = {
                        "points_count": collection_info.points_count,
                        "status": collection_info.status,
                        "vectors_count": collection_info.vectors_count
                    }
                except Exception as e:
                    stats[collection] = {"error": str(e)}
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}
    
    # Generic Vector Storage Operations
    async def store_content(
        self, 
        content: str, 
        collection_name: str, 
        content_type: str, 
        metadata: Dict[str, Any] = None
    ) -> str:
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
            
            logger.info(f"✅ Stored {content_type} content in {collection_name} with ID {point_id}")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store {content_type} content: {e}")
            raise
    
    async def search_content(
        self,
        query: str,
        collection_name: str,
        filters: Dict[str, Any] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Unified content search with filtering."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = self._build_filter(filters) if filters else None
            
            # Search
            results = self.qdrant.get_client().search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "content": result.payload.get("content", ""),
                    "metadata": {k: v for k, v in result.payload.items() if k != "content"}
                })
            
            logger.info(f"Found {len(formatted_results)} results in {collection_name}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Failed to search {collection_name}: {e}")
            raise
    
    # Question Operations
    async def store_question(
        self, 
        question_text: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store a question in the vector database."""
        question_metadata = {
            "text": question_text,
            "difficulty": metadata.get("difficulty", "medium"),
            "category": metadata.get("category", "general"),
            "subcategory": metadata.get("subcategory", ""),
            "role": metadata.get("role", ""),
            "skills": metadata.get("skills", []),
            "question_id": metadata.get("question_id", ""),
            **metadata
        }
        
        return await self.store_content(
            content=question_text,
            collection_name="questions",
            content_type="question",
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
        """Store an answer in the vector database."""
        answer_metadata = {
            "text": answer_text,
            "session_id": metadata.get("session_id", ""),
            "question_id": metadata.get("question_id", ""),
            "user_id": metadata.get("user_id", ""),
            "score": metadata.get("score", 0.0),
            "role": metadata.get("role", ""),
            **metadata
        }
        
        return await self.store_content(
            content=answer_text,
            collection_name="answers",
            content_type="answer",
            metadata=answer_metadata
        )
    
    async def find_similar_answers(
        self, 
        query: str, 
        filters: Dict[str, Any] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar answers using semantic search."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = self._build_answer_filter(filters)
            
            # Search
            results = self.qdrant.get_client().search(
                collection_name="answers",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            similar_answers = []
            for result in results:
                similar_answers.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                    "session_id": result.payload.get("session_id"),
                    "question_id": result.payload.get("question_id"),
                    "user_id": result.payload.get("user_id"),
                    "score": result.payload.get("score"),
                    "role": result.payload.get("role"),
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["text", "session_id", "question_id", "user_id", "score", "role"]}
                })
            
            logger.info(f"Found {len(similar_answers)} similar answers")
            return similar_answers
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar answers: {e}")
            raise
    
    # Job Description Operations
    async def store_job_description(
        self, 
        job_description: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store a job description in the vector database."""
        jd_metadata = {
            "text": job_description,
            "role": metadata.get("role", ""),
            "company": metadata.get("company", ""),
            "industry": metadata.get("industry", ""),
            "level": metadata.get("level", ""),
            "skills": metadata.get("skills", []),
            **metadata
        }
        
        return await self.store_content(
            content=job_description,
            collection_name="job_descriptions",
            content_type="job_description",
            metadata=jd_metadata
        )
    
    async def find_similar_job_descriptions(
        self, 
        query: str, 
        filters: Dict[str, Any] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar job descriptions using semantic search."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = self._build_job_description_filter(filters)
            
            # Search
            results = self.qdrant.get_client().search(
                collection_name="job_descriptions",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            similar_jds = []
            for result in results:
                similar_jds.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                    "role": result.payload.get("role"),
                    "company": result.payload.get("company"),
                    "industry": result.payload.get("industry"),
                    "level": result.payload.get("level"),
                    "skills": result.payload.get("skills", []),
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["text", "role", "company", "industry", "level", "skills"]}
                })
            
            logger.info(f"Found {len(similar_jds)} similar job descriptions")
            return similar_jds
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar job descriptions: {e}")
            raise
    
    # User Pattern Operations
    async def store_user_pattern(
        self, 
        pattern_data: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store user pattern data in the vector database."""
        pattern_metadata = {
            "text": pattern_data,
            "user_id": metadata.get("user_id", ""),
            "pattern_type": metadata.get("pattern_type", ""),
            "strength": metadata.get("strength", 0.0),
            "frequency": metadata.get("frequency", 0),
            **metadata
        }
        
        return await self.store_content(
            content=pattern_data,
            collection_name="user_patterns",
            content_type="user_pattern",
            metadata=pattern_metadata
        )
    
    async def find_similar_user_patterns(
        self, 
        query: str, 
        filters: Dict[str, Any] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar user patterns using semantic search."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = self._build_user_pattern_filter(filters)
            
            # Search
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
                    "text": result.payload.get("text"),
                    "user_id": result.payload.get("user_id"),
                    "pattern_type": result.payload.get("pattern_type"),
                    "strength": result.payload.get("strength"),
                    "frequency": result.payload.get("frequency"),
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["text", "user_id", "pattern_type", "strength", "frequency"]}
                })
            
            logger.info(f"Found {len(similar_patterns)} similar user patterns")
            return similar_patterns
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar user patterns: {e}")
            raise
    
    # Session Operations
    async def store_session(
        self, 
        session_data: str, 
        metadata: Dict[str, Any]
    ) -> str:
        """Store session data in the vector database."""
        session_metadata = {
            "text": session_data,
            "session_id": metadata.get("session_id", ""),
            "user_id": metadata.get("user_id", ""),
            "role": metadata.get("role", ""),
            "mode": metadata.get("mode", ""),
            "status": metadata.get("status", ""),
            **metadata
        }
        
        return await self.store_content(
            content=session_data,
            collection_name="sessions",
            content_type="session",
            metadata=session_metadata
        )
    
    async def find_similar_sessions(
        self, 
        query: str, 
        filters: Dict[str, Any] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find similar sessions using semantic search."""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Build filter
            search_filter = self._build_session_filter(filters)
            
            # Search
            results = self.qdrant.get_client().search(
                collection_name="sessions",
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit
            )
            
            # Format results
            similar_sessions = []
            for result in results:
                similar_sessions.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                    "session_id": result.payload.get("session_id"),
                    "user_id": result.payload.get("user_id"),
                    "role": result.payload.get("role"),
                    "mode": result.payload.get("mode"),
                    "status": result.payload.get("status"),
                    "metadata": {k: v for k, v in result.payload.items() 
                               if k not in ["text", "session_id", "user_id", "role", "mode", "status"]}
                })
            
            logger.info(f"Found {len(similar_sessions)} similar sessions")
            return similar_sessions
            
        except Exception as e:
            logger.error(f"❌ Failed to find similar sessions: {e}")
            raise
    
    # Helper Methods
    def _build_payload(self, content_type: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload with type-specific metadata."""
        base_payload = {"content": content}
        
        # Add type-specific metadata
        if content_type in self.metadata_mappings:
            type_metadata = self.metadata_mappings[content_type]
            for field, value in metadata.items():
                if field in type_metadata:
                    base_payload[field] = value
        
        # Add all metadata
        base_payload.update(metadata)
        return base_payload
    
    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from dictionary."""
        conditions = []
        
        for field, value in filters.items():
            if isinstance(value, list):
                conditions.append(FieldCondition(key=field, match=MatchValue(value=value)))
            else:
                conditions.append(FieldCondition(key=field, match=MatchValue(value=value)))
        
        return Filter(must=conditions) if conditions else None
    
    def _build_question_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build filter for question searches."""
        if not filters:
            return None
        
        question_filters = {}
        for key, value in filters.items():
            if key in ["difficulty", "category", "subcategory", "role"]:
                question_filters[key] = value
        
        return self._build_filter(question_filters)
    
    def _build_answer_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build filter for answer searches."""
        if not filters:
            return None
        
        answer_filters = {}
        for key, value in filters.items():
            if key in ["session_id", "question_id", "user_id", "role"]:
                answer_filters[key] = value
        
        return self._build_filter(answer_filters)
    
    def _build_job_description_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build filter for job description searches."""
        if not filters:
            return None
        
        jd_filters = {}
        for key, value in filters.items():
            if key in ["role", "company", "industry", "level"]:
                jd_filters[key] = value
        
        return self._build_filter(jd_filters)
    
    def _build_user_pattern_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build filter for user pattern searches."""
        if not filters:
            return None
        
        pattern_filters = {}
        for key, value in filters.items():
            if key in ["user_id", "pattern_type"]:
                pattern_filters[key] = value
        
        return self._build_filter(pattern_filters)
    
    def _build_session_filter(self, filters: Dict[str, Any]) -> Filter:
        """Build filter for session searches."""
        if not filters:
            return None
        
        session_filters = {}
        for key, value in filters.items():
            if key in ["session_id", "user_id", "role", "mode", "status"]:
                session_filters[key] = value
        
        return self._build_filter(session_filters)
    
    def _generate_metadata_mappings(self) -> Dict[str, List[str]]:
        """Generate metadata mappings for different content types."""
        return {
            "question": ["text", "difficulty", "category", "subcategory", "role", "skills", "question_id"],
            "answer": ["text", "session_id", "question_id", "user_id", "score", "role"],
            "job_description": ["text", "role", "company", "industry", "level", "skills"],
            "user_pattern": ["text", "user_id", "pattern_type", "strength", "frequency"],
            "session": ["text", "session_id", "user_id", "role", "mode", "status"]
        }
    
    def _get_answer_model(self) -> Type[BaseModel]:
        """Get answer model for auto-generation."""
        # This would return a Pydantic model for answer validation
        return None
    
    def _get_user_pattern_model(self) -> Type[BaseModel]:
        """Get user pattern model for auto-generation."""
        # This would return a Pydantic model for user pattern validation
        return None
    
    def _get_job_description_model(self) -> Type[BaseModel]:
        """Get job description model for auto-generation."""
        # This would return a Pydantic model for job description validation
        return None
    
    def _get_question_model(self) -> Type[BaseModel]:
        """Get question model for auto-generation."""
        # This would return a Pydantic model for question validation
        return None
    
    def _get_session_model(self) -> Type[BaseModel]:
        """Get session model for auto-generation."""
        # This would return a Pydantic model for session validation
        return None


# Global vector service instance
unified_vector_service = UnifiedVectorService()
