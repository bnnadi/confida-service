from fastapi import Request, HTTPException
from app.config import get_settings
from app.exceptions import RateLimitExceededError
from app.middleware.rate_limiter import RateLimiter
from app.middleware.redis_rate_limiter import RedisRateLimiter
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

class EnhancedRateLimiter:
    """Enhanced rate limiter with per-endpoint and per-user-type configuration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_limiter = self._get_rate_limiter()
        self.endpoint_limiters = {}
        self.user_type_limiters = {}
    
    def _get_rate_limiter(self):
        """Get the appropriate rate limiter based on configuration."""
        if not self.settings.RATE_LIMIT_ENABLED:
            return None
        
        if self.settings.RATE_LIMIT_BACKEND == "redis":
            try:
                return RedisRateLimiter(
                    redis_url=self.settings.RATE_LIMIT_REDIS_URL,
                    max_requests=self.settings.RATE_LIMIT_DEFAULT_REQUESTS,
                    window_seconds=self.settings.RATE_LIMIT_DEFAULT_WINDOW
                )
            except Exception as e:
                logger.warning(f"Redis rate limiter not available, falling back to memory: {e}")
                return RateLimiter(
                    max_requests=self.settings.RATE_LIMIT_DEFAULT_REQUESTS,
                    window_seconds=self.settings.RATE_LIMIT_DEFAULT_WINDOW
                )
        else:
            return RateLimiter(
                max_requests=self.settings.RATE_LIMIT_DEFAULT_REQUESTS,
                window_seconds=self.settings.RATE_LIMIT_DEFAULT_WINDOW
            )
    
    def get_rate_limit_for_endpoint(self, endpoint: str) -> Dict[str, int]:
        """Get rate limit configuration for endpoint."""
        return self.settings.get_rate_limit_for_endpoint(endpoint)
    
    def get_rate_limit_for_user_type(self, user_type: str) -> Dict[str, int]:
        """Get rate limit configuration for user type."""
        return self.settings.get_rate_limit_for_user_type(user_type)
    
    def get_endpoint_limiter(self, endpoint: str) -> Optional[RateLimiter]:
        """Get or create rate limiter for specific endpoint."""
        if not self.rate_limiter:
            return None
        
        endpoint_config = self.get_rate_limit_for_endpoint(endpoint)
        endpoint_key = f"{endpoint}_{endpoint_config['requests']}_{endpoint_config['window']}"
        
        if endpoint_key not in self.endpoint_limiters:
            if self.settings.RATE_LIMIT_BACKEND == "redis":
                try:
                    self.endpoint_limiters[endpoint_key] = RedisRateLimiter(
                        redis_url=self.settings.RATE_LIMIT_REDIS_URL,
                        max_requests=endpoint_config['requests'],
                        window_seconds=endpoint_config['window']
                    )
                except Exception as e:
                    logger.warning(f"Redis endpoint limiter not available, using memory: {e}")
                    self.endpoint_limiters[endpoint_key] = RateLimiter(
                        max_requests=endpoint_config['requests'],
                        window_seconds=endpoint_config['window']
                    )
            else:
                self.endpoint_limiters[endpoint_key] = RateLimiter(
                    max_requests=endpoint_config['requests'],
                    window_seconds=endpoint_config['window']
                )
        
        return self.endpoint_limiters[endpoint_key]
    
    def get_user_type_limiter(self, user_type: str) -> Optional[RateLimiter]:
        """Get or create rate limiter for specific user type."""
        if not self.rate_limiter:
            return None
        
        user_config = self.get_rate_limit_for_user_type(user_type)
        user_key = f"{user_type}_{user_config['requests']}_{user_config['window']}"
        
        if user_key not in self.user_type_limiters:
            if self.settings.RATE_LIMIT_BACKEND == "redis":
                try:
                    self.user_type_limiters[user_key] = RedisRateLimiter(
                        redis_url=self.settings.RATE_LIMIT_REDIS_URL,
                        max_requests=user_config['requests'],
                        window_seconds=user_config['window']
                    )
                except Exception as e:
                    logger.warning(f"Redis user type limiter not available, using memory: {e}")
                    self.user_type_limiters[user_key] = RateLimiter(
                        max_requests=user_config['requests'],
                        window_seconds=user_config['window']
                    )
            else:
                self.user_type_limiters[user_key] = RateLimiter(
                    max_requests=user_config['requests'],
                    window_seconds=user_config['window']
                )
        
        return self.user_type_limiters[user_key]
    
    def check_rate_limit(self, request: Request, client_id: str = "default", user_type: str = "free") -> Dict[str, Any]:
        """Check rate limit for request with both endpoint and user type limits."""
        if not self.rate_limiter:
            return {"allowed": True, "reason": "rate_limiting_disabled"}
        
        endpoint = request.url.path
        endpoint_limiter = self.get_endpoint_limiter(endpoint)
        user_limiter = self.get_user_type_limiter(user_type)
        
        # Get configurations
        endpoint_config = self.get_rate_limit_for_endpoint(endpoint)
        user_config = self.get_rate_limit_for_user_type(user_type)
        
        # Check endpoint rate limit
        endpoint_allowed = True
        endpoint_remaining = endpoint_config['requests']
        
        if endpoint_limiter:
            try:
                endpoint_limiter.check_rate_limit(client_id)
                endpoint_allowed = True
                # Get remaining requests (approximate)
                endpoint_remaining = max(0, endpoint_config['requests'] - 1)
            except RateLimitExceededError:
                endpoint_allowed = False
                endpoint_remaining = 0
        
        # Check user type rate limit
        user_allowed = True
        user_remaining = user_config['requests']
        
        if user_limiter:
            try:
                user_limiter.check_rate_limit(client_id)
                user_allowed = True
                # Get remaining requests (approximate)
                user_remaining = max(0, user_config['requests'] - 1)
            except RateLimitExceededError:
                user_allowed = False
                user_remaining = 0
        
        # Both limits must pass
        allowed = endpoint_allowed and user_allowed
        
        # Use the more restrictive limit for response headers
        effective_limit = min(endpoint_config['requests'], user_config['requests'])
        effective_window = min(endpoint_config['window'], user_config['window'])
        effective_remaining = min(endpoint_remaining, user_remaining)
        
        result = {
            "allowed": allowed,
            "endpoint_limit": endpoint_config,
            "user_limit": user_config,
            "effective_limit": effective_limit,
            "effective_window": effective_window,
            "effective_remaining": effective_remaining,
            "client_id": client_id,
            "user_type": user_type,
            "endpoint": endpoint
        }
        
        if not allowed:
            if not endpoint_allowed:
                result["reason"] = "endpoint_rate_limit_exceeded"
            elif not user_allowed:
                result["reason"] = "user_type_rate_limit_exceeded"
            result["retry_after"] = effective_window
        
        return result
    
    def get_rate_limit_status(self, client_id: str, user_type: str = "free") -> Dict[str, Any]:
        """Get current rate limit status for a client."""
        if not self.rate_limiter:
            return {"status": "disabled"}
        
        # This would require implementing status methods in the rate limiters
        # For now, return basic information
        return {
            "client_id": client_id,
            "user_type": user_type,
            "endpoint_limits": self.settings.rate_limit_per_endpoint,
            "user_type_limits": self.settings.rate_limit_per_user_type,
            "backend": self.settings.RATE_LIMIT_BACKEND,
            "enabled": self.settings.RATE_LIMIT_ENABLED
        }
    
    def reset_rate_limit(self, client_id: str, user_type: str = "free") -> bool:
        """Reset rate limit for a specific client."""
        if not self.rate_limiter:
            return False
        
        try:
            # Reset all endpoint limiters for this client
            for limiter in self.endpoint_limiters.values():
                if hasattr(limiter, 'reset_client'):
                    limiter.reset_client(client_id)
            
            # Reset user type limiter for this client
            user_limiter = self.get_user_type_limiter(user_type)
            if user_limiter and hasattr(user_limiter, 'reset_client'):
                user_limiter.reset_client(client_id)
            
            logger.info(f"Rate limit reset for client {client_id} (user_type: {user_type})")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for client {client_id}: {e}")
            return False
