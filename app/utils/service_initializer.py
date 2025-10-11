"""
Service initialization utilities for consistent error handling.
"""

import os
from typing import Optional, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

class ServiceInitializer:
    """Utility class for initializing external services with consistent error handling."""
    
    @staticmethod
    def init_openai_client() -> Optional[Any]:
        """Initialize OpenAI client with consistent error handling."""
        if not os.getenv("OPENAI_API_KEY"):
            return None
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("✅ OpenAI client initialized successfully")
            return client
        except ImportError:
            logger.warning("⚠️ OpenAI library not installed")
        except Exception as e:
            logger.error(f"❌ Error initializing OpenAI client: {e}")
        return None
    
    @staticmethod
    def init_anthropic_client() -> Optional[Any]:
        """Initialize Anthropic client with consistent error handling."""
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            logger.info("✅ Anthropic client initialized successfully")
            return client
        except ImportError:
            logger.warning("⚠️ Anthropic library not installed")
        except Exception as e:
            logger.error(f"❌ Error initializing Anthropic client: {e}")
        return None
