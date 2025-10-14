"""
Embedding Generation Service

This service provides embedding generation capabilities for text content,
supporting both OpenAI and local Sentence Transformer models for semantic search.
"""
import hashlib
import json
import asyncio
from typing import List, Optional, Dict, Any
import openai
from sentence_transformers import SentenceTransformer
import numpy as np
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class EmbeddingService:
    """Service for generating embeddings for text content."""
    
    def __init__(self):
        self.openai_client = self._init_openai_client()
        self.sentence_transformer = self._init_sentence_transformer()
        self.cache = self._init_cache()
        self.default_model = "text-embedding-3-small"
        self.local_model_name = "all-MiniLM-L6-v2"
    
    def _init_openai_client(self):
        """Initialize OpenAI client for embeddings."""
        if settings.OPENAI_API_KEY:
            try:
                return openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                return None
        return None
    
    def _init_sentence_transformer(self):
        """Initialize Sentence Transformer for local embeddings."""
        try:
            return SentenceTransformer(self.local_model_name)
        except ImportError:
            logger.warning("Sentence Transformers not available. Install with: pip install sentence-transformers")
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize Sentence Transformer: {e}")
            return None
    
    def _init_cache(self):
        """Initialize embedding cache."""
        return EmbeddingCache()
    
    async def generate_embedding(
        self, 
        text: str, 
        model: str = None,
        use_cache: bool = True
    ) -> List[float]:
        """Generate embedding for text."""
        model = model or self.default_model
        
        # Check cache first
        if use_cache:
            cached_embedding = await self.cache.get(text, model)
            if cached_embedding:
                logger.debug(f"Cache hit for embedding: {model}")
                return cached_embedding
        
        # Generate embedding
        if model.startswith("text-embedding") and self.openai_client:
            embedding = await self._generate_openai_embedding(text, model)
        elif self.sentence_transformer:
            embedding = await self._generate_local_embedding(text)
        else:
            raise ValueError(f"No embedding model available for {model}")
        
        # Cache the result
        if use_cache:
            await self.cache.set(text, model, embedding)
        
        logger.debug(f"Generated embedding for text (length: {len(text)}) using {model}")
        return embedding
    
    async def generate_batch_embeddings(
        self, 
        texts: List[str], 
        model: str = None,
        batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        model = model or self.default_model
        embeddings = []
        
        logger.info(f"Generating embeddings for {len(texts)} texts using {model}")
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            if model.startswith("text-embedding") and self.openai_client:
                batch_embeddings = await self._generate_openai_batch_embeddings(batch, model)
            elif self.sentence_transformer:
                batch_embeddings = await self._generate_local_batch_embeddings(batch)
            else:
                raise ValueError(f"No embedding model available for {model}")
            
            embeddings.extend(batch_embeddings)
        
        logger.info(f"Successfully generated {len(embeddings)} embeddings")
        return embeddings
    
    async def _generate_openai_embedding(self, text: str, model: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.embeddings.create(
                    input=text,
                    model=model
                )
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    async def _generate_openai_batch_embeddings(self, texts: List[str], model: str) -> List[List[float]]:
        """Generate embeddings for batch using OpenAI API."""
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.embeddings.create(
                    input=texts,
                    model=model
                )
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            raise
    
    async def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local Sentence Transformer."""
        try:
            embedding = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sentence_transformer.encode(text)
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Local embedding generation failed: {e}")
            raise
    
    async def _generate_local_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using local Sentence Transformer."""
        try:
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.sentence_transformer.encode(texts)
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Local batch embedding generation failed: {e}")
            raise
    
    def get_available_models(self) -> Dict[str, Any]:
        """Get information about available embedding models."""
        models = {
            "openai": {
                "available": self.openai_client is not None,
                "models": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
                "default": "text-embedding-3-small"
            },
            "local": {
                "available": self.sentence_transformer is not None,
                "model": self.local_model_name,
                "vector_size": 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings
            }
        }
        return models
    
    def get_model_vector_size(self, model: str = None) -> int:
        """Get the vector size for a specific model."""
        model = model or self.default_model
        
        if model.startswith("text-embedding-3-small"):
            return 1536
        elif model.startswith("text-embedding-3-large"):
            return 3072
        elif model.startswith("text-embedding-ada-002"):
            return 1536
        elif self.sentence_transformer and model == "local":
            return 384
        else:
            return 1536  # Default to OpenAI small model size


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    async def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get cached embedding."""
        key = self._generate_key(text, model)
        
        if key in self.cache:
            # Update access order for LRU
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        
        return None
    
    async def set(self, text: str, model: str, embedding: List[float], ttl: int = 3600):
        """Cache embedding."""
        key = self._generate_key(text, model)
        
        # Implement LRU eviction
        if len(self.cache) >= self.max_size:
            # Remove least recently used item
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]
        
        self.cache[key] = embedding
        self.access_order.append(key)
    
    def _generate_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"embedding:{model}:{text_hash}"
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        self.access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": "N/A"  # Would need to track hits/misses for this
        }


# Global embedding service instance
embedding_service = EmbeddingService()
