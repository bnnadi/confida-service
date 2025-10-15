"""
Qdrant Vector Database Configuration

This module provides configuration and connection management for Qdrant vector database,
enabling semantic search capabilities for InterviewIQ.
"""
import os
from typing import Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class QdrantConfig:
    """Configuration for Qdrant vector database collections."""
    
    # Base collection template
    BASE_COLLECTION_CONFIG = {
        "vector_size": 1536,  # OpenAI embedding size
        "distance": Distance.COSINE
    }
    
    # Collection-specific payload schemas
    PAYLOAD_SCHEMAS = {
        "job_descriptions": {
            "role": "keyword",
            "company": "keyword", 
            "level": "keyword",
            "skills": "keyword[]",
            "created_at": "datetime"
        },
        "questions": {
            "session_id": "keyword",
            "difficulty": "keyword",
            "category": "keyword",
            "subcategory": "keyword",
            "role": "keyword",
            "skills": "keyword[]",
            "created_at": "datetime"
        },
        "answers": {
            "user_id": "keyword",
            "question_id": "keyword",
            "session_id": "keyword",
            "score": "float",
            "created_at": "datetime"
        },
        "user_patterns": {
            "user_id": "keyword",
            "skill_level": "keyword",
            "performance_trend": "float",
            "learning_style": "keyword",
            "created_at": "datetime"
        }
    }
    
    @classmethod
    def _build_collection_config(cls, collection_name: str) -> Dict[str, Any]:
        """Build collection configuration from template and schema."""
        return {
            **cls.BASE_COLLECTION_CONFIG,
            "payload_schema": cls.PAYLOAD_SCHEMAS.get(collection_name, {})
        }
    
    @classmethod
    def get_collections(cls) -> Dict[str, Dict[str, Any]]:
        """Get all collection configurations."""
        return {
            name: cls._build_collection_config(name) 
            for name in cls.PAYLOAD_SCHEMAS.keys()
        }
    
    # Backward compatibility
    COLLECTIONS = property(get_collections)
    
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.client: Optional[QdrantClient] = None
        self._initialized = False
    
    def get_client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if not self._initialized:
            self._initialize_client()
        return self.client
    
    def _initialize_client(self):
        """Initialize Qdrant client connection."""
        try:
            if self.qdrant_api_key:
                self.client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key
                )
            else:
                self.client = QdrantClient(url=self.qdrant_url)
            
            self._initialized = True
            logger.info(f"✅ Qdrant client initialized successfully at {self.qdrant_url}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            raise
    
    async def create_collections(self):
        """Create all required vector collections."""
        if not self._initialized:
            self._initialize_client()
        
        try:
            for collection_name, config in self.COLLECTIONS.items():
                # Check if collection already exists
                try:
                    collection_info = self.client.get_collection(collection_name)
                    logger.info(f"Collection '{collection_name}' already exists")
                    continue
                except Exception:
                    # Collection doesn't exist, create it
                    pass
                
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=config["vector_size"],
                        distance=config["distance"]
                    )
                )
                logger.info(f"✅ Created collection '{collection_name}'")
            
            logger.info("✅ All Qdrant collections created successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to create Qdrant collections: {e}")
            raise
    
    async def delete_collections(self):
        """Delete all collections (for testing/cleanup)."""
        if not self._initialized:
            self._initialize_client()
        
        try:
            for collection_name in self.COLLECTIONS.keys():
                try:
                    self.client.delete_collection(collection_name)
                    logger.info(f"✅ Deleted collection '{collection_name}'")
                except Exception as e:
                    logger.warning(f"Collection '{collection_name}' may not exist: {e}")
            
            logger.info("✅ All Qdrant collections deleted")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete Qdrant collections: {e}")
            raise
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get information about a specific collection."""
        if not self._initialized:
            self._initialize_client()
        
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "status": collection_info.status,
                "optimizer_status": collection_info.optimizer_status,
                "payload_schema": self.COLLECTIONS.get(collection_name, {}).get("payload_schema", {})
            }
        except Exception as e:
            logger.error(f"Failed to get collection info for '{collection_name}': {e}")
            return {"error": str(e)}
    
    def get_all_collections_info(self) -> Dict[str, Any]:
        """Get information about all collections."""
        collections_info = {}
        for collection_name in self.COLLECTIONS.keys():
            collections_info[collection_name] = self.get_collection_info(collection_name)
        return collections_info
    
    def health_check(self) -> Dict[str, Any]:
        """Check Qdrant service health."""
        try:
            if not self._initialized:
                self._initialize_client()
            
            # Try to get cluster info
            cluster_info = self.client.get_cluster_info()
            
            return {
                "status": "healthy",
                "url": self.qdrant_url,
                "cluster_info": cluster_info,
                "collections": list(self.COLLECTIONS.keys())
            }
            
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {
                "status": "unhealthy",
                "url": self.qdrant_url,
                "error": str(e)
            }

# Global Qdrant configuration instance
qdrant_config = QdrantConfig()
