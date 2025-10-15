import hashlib
import json
import redis
import time
from typing import Any, Optional, Dict, Union
from functools import wraps
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

class CacheManager:
    """Unified cache manager supporting both Redis and in-memory backends."""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
        
        # Initialize Redis if configured
        if settings.CACHE_BACKEND == "redis":
            try:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"⚠️ Redis cache not available, falling back to memory: {e}")
                self.redis_client = None
    
    def get_cache_key(self, service: str, operation: str, **kwargs) -> str:
        """Generate cache key from parameters."""
        # Create deterministic key from parameters
        key_data = {
            "service": service,
            "operation": operation,
            **{k: v for k, v in kwargs.items() if v is not None}
        }
        
        # Sort keys for consistent hashing
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"ai_cache:{service}:{operation}:{key_hash}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            if self.redis_client:
                return await self._get_from_redis(key)
            else:
                return self._get_from_memory(key)
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        value = self.redis_client.get(key)
        if value:
            self.cache_stats["hits"] += 1
            logger.debug(f"Cache hit for key: {key}")
            return json.loads(value)
        else:
            self.cache_stats["misses"] += 1
            logger.debug(f"Cache miss for key: {key}")
            return None
    
    def _get_from_memory(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key in self.memory_cache:
            cached_item = self.memory_cache[key]
            # Check if expired
            if time.time() < cached_item["expires_at"]:
                self.cache_stats["hits"] += 1
                logger.debug(f"Memory cache hit for key: {key}")
                return cached_item["value"]
            else:
                # Remove expired item
                del self.memory_cache[key]
        
        self.cache_stats["misses"] += 1
        logger.debug(f"Memory cache miss for key: {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache."""
        try:
            if self.redis_client:
                return await self._set_in_redis(key, value, ttl)
            else:
                return self._set_in_memory(key, value, ttl)
        except Exception as e:
            self.cache_stats["errors"] += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def _set_in_redis(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in Redis cache."""
        serialized_value = json.dumps(value, default=str)
        success = self.redis_client.setex(key, ttl, serialized_value)
        if success:
            logger.debug(f"Cached value in Redis for key: {key} (TTL: {ttl}s)")
        return bool(success)
    
    def _set_in_memory(self, key: str, value: Any, ttl: int) -> bool:
        """Set value in memory cache."""
        self.memory_cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
        logger.debug(f"Cached value in memory for key: {key} (TTL: {ttl}s)")
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            if self.redis_client:
                result = self.redis_client.delete(key)
                logger.debug(f"Deleted from Redis cache: {key}")
                return bool(result)
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    logger.debug(f"Deleted from memory cache: {key}")
                return True
                
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern."""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    logger.info(f"Cleared {deleted} Redis cache entries matching: {pattern}")
                    return deleted
                return 0
            else:
                # Memory cache pattern matching
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace("*", "") in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                logger.info(f"Cleared {len(keys_to_delete)} memory cache entries matching: {pattern}")
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "backend": "redis" if self.redis_client else "memory",
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "errors": self.cache_stats["errors"],
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
            "memory_cache_size": len(self.memory_cache) if not self.redis_client else 0
        }
    
    def reset_stats(self):
        """Reset cache statistics."""
        self.cache_stats = {"hits": 0, "misses": 0, "errors": 0}
        logger.info("Cache statistics reset")

# Global cache manager instance
cache_manager = CacheManager()

def _generate_cache_key(operation: str, cache_key_params: Optional[list], args: tuple, kwargs: dict) -> str:
    """Extract cache key generation logic to avoid duplication."""
    cache_key_kwargs = {}
    
    # Include specified parameters in cache key
    if cache_key_params:
        for param in cache_key_params:
            if param in kwargs:
                cache_key_kwargs[param] = kwargs[param]
    
    # Include first few positional args (typically role, job_description, etc.)
    if args:
        arg_mapping = ["role", "job_description", "question", "answer", "content"]
        for i, arg in enumerate(args[:len(arg_mapping)]):
            if arg is not None:
                cache_key_kwargs[arg_mapping[i]] = arg
    
    return cache_manager.get_cache_key(
        service=kwargs.get('service', 'default'),
        operation=operation,
        **cache_key_kwargs
    )

def cached(operation: str, ttl: int = 3600, cache_key_params: Optional[list] = None):
    """
    Cache decorator for AI service methods.
    
    Args:
        operation: Operation name for cache key generation
        ttl: Time to live in seconds
        cache_key_params: List of parameter names to include in cache key
    """
    def decorator(func):
        import asyncio
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(operation, cache_key_params, args, kwargs)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for {operation}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            logger.info(f"Cache miss for {operation}, result cached (TTL: {ttl}s)")
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(operation, cache_key_params, args, kwargs)
            
            # Try to get from cache
            try:
                loop = asyncio.get_event_loop()
                cached_result = loop.run_until_complete(cache_manager.get(cache_key))
                if cached_result is not None:
                    logger.info(f"Cache hit for {operation}")
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache get error in sync wrapper: {e}")
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(cache_manager.set(cache_key, result, ttl))
                logger.info(f"Cache miss for {operation}, result cached (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Cache set error in sync wrapper: {e}")
            
            return result
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

class CacheMetrics:
    """Cache metrics collection and reporting."""
    
    def __init__(self):
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_errors": 0,
            "operation_stats": {}
        }
    
    def record_request(self, operation: str, hit: bool, error: bool = False):
        """Record cache request metrics."""
        self.metrics["total_requests"] += 1
        
        # Determine metric type
        metric_type = "errors" if error else ("hits" if hit else "misses")
        self.metrics[f"cache_{metric_type}"] += 1
        
        # Per-operation stats
        if operation not in self.metrics["operation_stats"]:
            self.metrics["operation_stats"][operation] = {
                "requests": 0, "hits": 0, "misses": 0, "errors": 0
            }
        
        op_stats = self.metrics["operation_stats"][operation]
        op_stats["requests"] += 1
        op_stats[metric_type] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics."""
        total = self.metrics["total_requests"]
        hit_rate = (self.metrics["cache_hits"] / total * 100) if total > 0 else 0
        
        return {
            "overall": {
                "total_requests": total,
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"],
                "cache_errors": self.metrics["cache_errors"],
                "hit_rate": round(hit_rate, 2)
            },
            "by_operation": self.metrics["operation_stats"],
            "cache_backend": cache_manager.get_stats()
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_errors": 0,
            "operation_stats": {}
        }

# Global metrics instance
cache_metrics = CacheMetrics()
