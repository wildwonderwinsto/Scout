"""
Pydantic schemas for Channel API responses.
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ChannelBase(BaseModel):
    """Fields shared across all channel representations."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    created_at: Optional[datetime] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None
    view_count: Optional[int] = None
    topics: Optional[str] = None
    banner_url: Optional[str] = None
    profile_image_url: Optional[str] = None
    hidden_subscriber_count: Optional[bool] = None
    made_for_kids: Optional[bool] = None
    last_updated: Optional[datetime] = None


class ChannelOut(ChannelBase):
    """Full channel response returned by the API."""
    avg_views_per_video: Optional[float] = None


class ChannelList(BaseModel):
    """Paginated list of channels."""
    items: list[ChannelOut]
    total: int
