"""
UUID utility functions for consistent ID handling across services.
"""
import uuid
from typing import Union


def to_uuid(value: Union[str, uuid.UUID]) -> uuid.UUID:
    """Convert a value to UUID. Accepts str or UUID."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))
