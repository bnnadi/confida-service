"""
Unified Logging Configuration for Confida

This module consolidates all logging configuration into a single, comprehensive
logging setup that eliminates redundancy and provides consistent logging across
the entire application.
"""
import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import get_settings

def get_logging_config() -> Dict[str, Any]:
    """Get unified logging configuration."""
    settings = get_settings()
    
    # Determine log level based on debug routes setting
    log_level = "DEBUG" if settings.ENABLE_DEBUG_ROUTES else "INFO"
    
    # Log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    detailed_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": detailed_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "json": {
                "format": '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s", "line": %(lineno)d}',
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "detailed",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            },
            "debug_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "filename": "logs/debug.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 3
            }
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "app.services": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "app.routers": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "app.utils": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "app.database": {
                "level": "INFO",
                "handlers": ["console", "file", "error_file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file", "error_file"]
        }
    }
    
    # Add debug file handler in development
    if settings.ENABLE_DEBUG_ROUTES:
        config["loggers"]["app"]["handlers"].append("debug_file")
        config["loggers"]["app.services"]["handlers"].append("debug_file")
        config["loggers"]["app.routers"]["handlers"].append("debug_file")
        config["loggers"]["app.utils"]["handlers"].append("debug_file")
    
    return config

def setup_logging():
    """Setup unified logging configuration."""
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Get logger to confirm setup
    logger = logging.getLogger("app")
    logger.info("✅ Unified logging configuration initialized")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with unified configuration."""
    return logging.getLogger(name)

# Initialize logging on import
setup_logging()
