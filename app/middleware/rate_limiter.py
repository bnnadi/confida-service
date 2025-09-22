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
        now = time.time()
        client_requests = self.requests[client_id]
        
        # More efficient: only keep recent requests
        cutoff_time = now - self.window_seconds
        self.requests[client_id] = [req_time for req_time in client_requests if req_time > cutoff_time]
        
        if len(self.requests[client_id]) >= self.max_requests:
            raise RateLimitExceededError("Rate limit exceeded")
        
        self.requests[client_id].append(now)
        
        # Clean up old clients periodically
        if len(self.requests) > 1000:  # Arbitrary threshold
            self._cleanup_old_clients(now)
    
    def _cleanup_old_clients(self, now: float):
        """Clean up old client data to prevent memory leaks."""
        cutoff_time = now - self.window_seconds
        clients_to_remove = []
        
        for client_id, requests in self.requests.items():
            # Remove clients with no recent requests
            recent_requests = [req_time for req_time in requests if req_time > cutoff_time]
            if recent_requests:
                self.requests[client_id] = recent_requests
            else:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.requests[client_id]

rate_limiter = RateLimiter() 