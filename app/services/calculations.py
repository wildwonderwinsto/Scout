"""
Calculation engine placeholder.

This module will contain the core ranking algorithms:
- Breakout Score = Video Views / Channel Average Views
- VPH (Views Per Hour) from snapshot diffs
- Trending velocity ranking
- Outlier detection across a niche

Implemented in Step 2.
"""

from typing import Optional
from app.models.video import Video
from app.models.channel import Channel
from app.models.snapshot import VideoSnapshot
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_breakout_score(
    video_views: int,
    channel_avg_views: float,
) -> Optional[float]:
    """
    Breakout Score = Video Views / Channel Average Views.

    A score of 1.0 means the video is performing at the channel's average.
    A score of 10.0 means 10x overperformance — a strong outlier signal.

    Returns None if channel_avg_views is zero or missing.
    """
    if not channel_avg_views or channel_avg_views <= 0:
        return None
    return round(video_views / channel_avg_views, 2)


def calculate_engagement_rate(
    likes: Optional[int],
    comments: Optional[int],
    views: Optional[int],
) -> Optional[float]:
    """
    Engagement Rate = (Likes + Comments) / Views.

    Used as a quality gate — videos below 2% engagement may indicate
    bought views or viewbait.
    """
    if not views or views <= 0:
        return None
    like_count = likes or 0
    comment_count = comments or 0
    return round((like_count + comment_count) / views, 4)


def calculate_vph(
    snapshot_old: Optional[VideoSnapshot],
    snapshot_new: Optional[VideoSnapshot],
) -> Optional[float]:
    """
    Views Per Hour = (new_views - old_views) / hours_elapsed.

    Requires two snapshots taken at different times for the same video.
    Returns None if timestamps are identical or data is invalid.

    Will be fully wired up when scheduled snapshot collection is implemented
    in Step 2.
    """
    if not snapshot_old or not snapshot_new:
        return None
    if snapshot_old.captured_at >= snapshot_new.captured_at:
        return None

    view_diff = snapshot_new.view_count - snapshot_old.view_count
    time_diff: timedelta = snapshot_new.captured_at - snapshot_old.captured_at
    hours = time_diff.total_seconds() / 3600

    if hours <= 0:
        return None

    return round(view_diff / hours, 1)
