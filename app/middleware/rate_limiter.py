from fastapi import HTTPException
import time
from collections import defaultdict
from app.exceptions import RateLimitExceededError

class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def check_rate_limit(self, client_id: str = "default"):
        """Simplified rate limiting with extracted cleanup logic."""
        now = time.time()
        # Cleanup will be done after adding the request
        
        if len(self.requests[client_id]) >= self.max_requests:
            raise RateLimitExceededError("Rate limit exceeded")
        
        self.requests[client_id].append(now)
        self._cleanup_old_data(now)
    
    def _cleanup_old_data(self, now: float):
        """Consolidated cleanup for old requests and clients."""
        cutoff_time = now - self.window_seconds
        
        # Clean up old requests for all clients
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id] 
                if req_time > cutoff_time
            ]
            
            # Remove clients with no recent requests
            if not self.requests[client_id]:
                del self.requests[client_id]
        
        # Additional cleanup if we have too many clients
        if len(self.requests) > 1000:
            # Keep only the most recent clients
            sorted_clients = sorted(
                self.requests.items(), 
                key=lambda x: max(x[1]) if x[1] else 0, 
                reverse=True
            )
            self.requests = dict(sorted_clients[:500])  # Keep top 500 clients

rate_limiter = RateLimiter() 