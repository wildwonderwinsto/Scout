"""
Video endpoints.

GET /videos/{video_id} — Fetch and return a single video with engagement rate
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.video import VideoOut
from app.services.data_fetcher import fetch_and_store_video

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: str, db: Session = Depends(get_db)):
    """
    Fetch a single YouTube video by ID.

    If the video isn't in the database yet, it's fetched from the
    YouTube Data API and stored (with a snapshot) before returning.
    """
    video = fetch_and_store_video(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found on YouTube")

    video_out = VideoOut.model_validate(video)
    video_out.engagement_rate = video.engagement_rate
    return video_out
