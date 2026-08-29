"""
Pydantic schemas for Video API responses.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class VideoBase(BaseModel):
    """Fields shared across all video representations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    channel_id: str
    title: str
    description: Optional[str] = None
    tags: Optional[str] = None
    published_at: Optional[datetime] = None
    duration: Optional[str] = None
    duration_seconds: Optional[int] = None
    category_id: Optional[str] = None
    made_for_kids: Optional[bool] = None
    is_short: bool = False
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    last_updated: Optional[datetime] = None


class VideoOut(VideoBase):
    """Full video response returned by the API, with computed engagement rate."""
    engagement_rate: Optional[float] = None


class VideoList(BaseModel):
    """Paginated list of videos."""
    items: list[VideoOut]
    total: int
