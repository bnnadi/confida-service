"""
Redis-based rate limiter for production deployments.
"""

import redis
from fastapi import HTTPException
from app.exceptions import RateLimitExceededError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RedisRateLimiter:
    """Redis-based rate limiter for production deployments."""
    
    def __init__(self, redis_url: str = None, max_requests: int = 10, window_seconds: int = 60):
        try:
            self.redis = redis.from_url(redis_url or "redis://localhost:6379")
            self.max_requests = max_requests
            self.window_seconds = window_seconds
            logger.info("Redis rate limiter initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis rate limiter: {e}")
            self.redis = None
    
    def check_rate_limit(self, client_id: str = "default"):
        """Check rate limit using Redis."""
        if not self.redis:
            # Fallback to no rate limiting if Redis is not available
            return
        
        try:
            key = f"rate_limit:{client_id}"
            current = self.redis.incr(key)
            
            if current == 1:
                self.redis.expire(key, self.window_seconds)
            
            if current > self.max_requests:
                raise RateLimitExceededError(f"Rate limit exceeded for client {client_id}")
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiting: {e}")
            # Don't block requests if Redis is down
        except RateLimitExceededError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in rate limiting: {e}")
            # Don't block requests on unexpected errors
