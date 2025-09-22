"""
Async HTTP client utility for better performance.
"""

import httpx
from typing import Optional, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

class HTTPClient:
    """Async HTTP client for better performance."""
    
    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make async GET request."""
        async with self as client:
            return await client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make async POST request."""
        async with self as client:
            return await client.post(url, **kwargs)
    
    async def health_check(self, url: str) -> bool:
        """Check if a service is healthy."""
        try:
            async with self as client:
                response = await client.get(url, timeout=5.0)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for {url}: {e}")
            return False
