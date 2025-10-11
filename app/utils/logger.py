"""
Centralized logging utility for consistent logging across the application.
"""

import logging
import sys
import os
from typing import Optional

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with consistent configuration."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Set log level from environment
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    return logger
