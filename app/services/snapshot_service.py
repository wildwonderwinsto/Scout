"""
Background snapshot collection service.

Periodically refreshes video statistics for tracked videos so we can
compute accurate Views Per Hour (VPH) from real snapshot diffs instead
of relying on lifetime averages.

The scheduler calls `update_tracked_snapshots()` on a configurable interval
(default: every 60 minutes). Only videos from recent scans are refreshed
to conserve API quota.
"""

from typing import List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging

from app.services.youtube_client import YouTubeClient
from app.services.data_fetcher import upsert_video, add_snapshot, _get_client
from app.models.video import Video
from app.models.snapshot import VideoSnapshot
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Maximum number of videos to refresh per scheduler run (quota conservation)
MAX_VIDEOS_PER_RUN = 200


def update_tracked_snapshots():
    """
    Background job entry point.  Called by APScheduler on interval.

    Opens its own DB session (since background jobs don't have FastAPI's
    dependency injection) and refreshes snapshots for recently-active videos.
    """
    db = SessionLocal()
    try:
        _do_snapshot_update(db)
    except Exception as e:
        logger.error(f"Snapshot update job failed: {e}", exc_info=True)
    finally:
        db.close()


def _do_snapshot_update(db: Session):
    """
    Refresh statistics for videos that were recently scanned.

    Strategy: Only update videos that have at least one snapshot in the
    last 24 hours (meaning they were part of a recent scan). This avoids
    wasting quota on stale/old videos nobody is looking at.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    # Find video IDs that have recent snapshots (recently scanned)
    recent_video_ids = (
        db.query(VideoSnapshot.video_id)
        .filter(VideoSnapshot.captured_at >= cutoff)
        .distinct()
        .limit(MAX_VIDEOS_PER_RUN)
        .all()
    )
    video_ids = [row[0] for row in recent_video_ids]

    if not video_ids:
        logger.info("Snapshot update: no recently-tracked videos to refresh.")
        return

    logger.info(f"Snapshot update: refreshing {len(video_ids)} tracked videos")

    client = _get_client()

    # Batch-fetch in groups of 50
    updated_count = 0
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            videos_data = client.get_videos_details_batch(batch)
            for vdata in videos_data:
                video = upsert_video(db, vdata)
                if video.view_count is not None:
                    add_snapshot(
                        db, video.id,
                        video.view_count,
                        video.like_count,
                        video.comment_count,
                    )
                    updated_count += 1
        except Exception as e:
            logger.error(f"Snapshot batch update failed: {e}")
            continue

    logger.info(f"Snapshot update complete: {updated_count} videos refreshed")


def update_specific_videos(db: Session, video_ids: List[str]):
    """
    Manually trigger a snapshot update for specific videos.
    Used by the channel analysis endpoint for on-demand refresh.
    """
    if not video_ids:
        return

    client = _get_client()

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            videos_data = client.get_videos_details_batch(batch)
            for vdata in videos_data:
                video = upsert_video(db, vdata)
                if video.view_count is not None:
                    add_snapshot(
                        db, video.id,
                        video.view_count,
                        video.like_count,
                        video.comment_count,
                    )
        except Exception as e:
            logger.error(f"Manual snapshot update failed: {e}")
            continue


def get_snapshot_stats(db: Session) -> dict:
    """
    Return stats about the snapshot collection system.
    Useful for the health/status endpoint.
    """
    total_snapshots = db.query(VideoSnapshot).count()
    total_tracked_videos = db.query(VideoSnapshot.video_id).distinct().count()

    cutoff_1h = datetime.now(timezone.utc) - timedelta(hours=1)
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    recent_1h = (
        db.query(VideoSnapshot)
        .filter(VideoSnapshot.captured_at >= cutoff_1h)
        .count()
    )
    recent_24h = (
        db.query(VideoSnapshot)
        .filter(VideoSnapshot.captured_at >= cutoff_24h)
        .count()
    )

    return {
        "total_snapshots": total_snapshots,
        "total_tracked_videos": total_tracked_videos,
        "snapshots_last_1h": recent_1h,
        "snapshots_last_24h": recent_24h,
    }
