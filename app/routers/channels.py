"""
Channel endpoints.

GET /channels/{channel_id}        — Fetch and return a single channel
GET /channels/{channel_id}/videos — Fetch and return a channel's recent videos
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models.channel import Channel
from app.schemas.channel import ChannelOut
from app.schemas.video import VideoList, VideoOut
from app.schemas.scan import ChannelAnalysis
from app.services.data_fetcher import fetch_and_store_channel, fetch_and_store_channel_videos
from app.services.channel_analysis import analyze_channel
from app.services.snapshot_service import update_specific_videos, get_snapshot_stats

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/{channel_id_or_url:path}/analysis", response_model=ChannelAnalysis)
def get_channel_analysis(
    channel_id_or_url: str,
    max_videos: int = 50,
    outlier_threshold: float = 2.0,
    db: Session = Depends(get_db),
):
    """
    Comprehensive channel analysis.

    Pass a channel ID (UC...), a handle (@MrBeast), or a full URL.
    Returns channel stats, average views, recent videos, top outliers,
    and health/engagement metrics.
    """
    # Remove leading slash if path param captured it
    channel_id_or_url = channel_id_or_url.strip("/")
    
    analysis = analyze_channel(db, channel_id_or_url, max_videos, outlier_threshold)
    if "error" in analysis:
        raise HTTPException(status_code=404, detail=analysis["error"])
    return analysis


@router.post("/snapshots/refresh")
def manual_snapshot_refresh(video_ids: List[str], db: Session = Depends(get_db)):
    """
    Manually trigger a snapshot update for a list of video IDs.
    This creates new snapshot records immediately, enabling VPH calculation.
    """
    if len(video_ids) > 50:
        raise HTTPException(status_code=400, detail="Max 50 videos per manual refresh")
    update_specific_videos(db, video_ids)
    return {"message": f"Refreshed {len(video_ids)} videos"}


@router.get("/snapshots/stats")
def snapshot_stats(db: Session = Depends(get_db)):
    """Return stats about the background snapshot collection system."""
    return get_snapshot_stats(db)


@router.get("/{channel_id}", response_model=ChannelOut)
def get_channel(channel_id: str, db: Session = Depends(get_db)):
    """
    Fetch a YouTube channel by ID.

    If the channel isn't in the database yet, it's fetched from the
    YouTube Data API and stored before returning.
    """
    channel = fetch_and_store_channel(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found on YouTube")

    # Build response with computed avg_views_per_video
    channel_data = ChannelOut.model_validate(channel)
    channel_data.avg_views_per_video = channel.avg_views_per_video
    return channel_data


@router.get("/{channel_id}/videos", response_model=VideoList)
def get_channel_videos(
    channel_id: str,
    max_results: int = Query(default=50, ge=1, le=100, description="Number of recent videos to fetch"),
    db: Session = Depends(get_db),
):
    """
    Fetch a channel's recent videos (from their uploads playlist).

    Each video is stored in the database with a snapshot for VPH tracking.
    The response includes computed engagement_rate for each video.
    """
    videos = fetch_and_store_channel_videos(db, channel_id, max_results)
    if not videos:
        raise HTTPException(status_code=404, detail="No videos found for this channel")

    items = []
    for v in videos:
        video_out = VideoOut.model_validate(v)
        video_out.engagement_rate = v.engagement_rate
        items.append(video_out)

    return VideoList(items=items, total=len(items))
