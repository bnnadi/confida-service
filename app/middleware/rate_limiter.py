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
        
        # More efficient cleanup using filter
        self.requests[client_id] = [
            req_time for req_time in client_requests 
            if now - req_time < self.window_seconds
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            raise RateLimitExceededError("Rate limit exceeded")
        
        self.requests[client_id].append(now)

rate_limiter = RateLimiter() 