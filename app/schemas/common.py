"""
Shared Pydantic schemas for pagination, filter parameters, and common responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    skip: int = Field(default=0, ge=0, description="Number of records to skip")
    limit: int = Field(default=100, ge=1, le=500, description="Maximum records to return")


class StatusResponse(BaseModel):
    """Generic status response."""
    status: str
    message: Optional[str] = None
    service: str = "youtube-trend-scout"
