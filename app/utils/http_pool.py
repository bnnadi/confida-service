"""
HTTP connection pool for better performance and reliability.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.utils.logger import get_logger

logger = get_logger(__name__)

class HTTPPool:
    """HTTP connection pool for better performance."""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info("HTTP connection pool initialized")
    
    def get_session(self) -> requests.Session:
        """Get the configured session."""
        return self.session
    
    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("HTTP connection pool closed")

# Global instance
http_pool = HTTPPool()
