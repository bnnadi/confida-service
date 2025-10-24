"""
Database package for Confida application.

Note: Database operations are now handled by the unified DatabaseService.
Import from app.services.database_service for database operations.
"""
from . import models
from .models import Base

__all__ = ["Base", "models"]
