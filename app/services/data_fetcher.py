"""
High-level data-fetching orchestration.

Uses YouTubeClient to pull data from the API, parses responses into
SQLAlchemy model instances, and persists them.  Also creates VideoSnapshot
records on every fetch so VPH can be computed later.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from app.services.youtube_client import YouTubeClient
from app.models.channel import Channel
from app.models.video import Video
from app.models.snapshot import VideoSnapshot
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

# Module-level client instance (will be replaced with DI in later steps)
_client: Optional[YouTubeClient] = None


def _get_client() -> YouTubeClient:
    """Lazy-init the YouTube client so import-time errors don't break tests."""
    global _client
    if _client is None:
        _client = YouTubeClient()
    return _client


# ── Helpers ───────────────────────────────────────────────────────────────

def parse_duration_to_seconds(duration_iso: str) -> Optional[int]:
    """
    Convert an ISO 8601 duration string (e.g. 'PT1H2M10S') to total seconds.
    Returns None if the string doesn't match the expected pattern.
    """
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    match = pattern.match(duration_iso)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def detect_is_short(duration_seconds: Optional[int]) -> bool:
    """
    Determine whether a video is a YouTube Short.

    Current heuristic: duration <= 60 seconds.
    Could be refined later with aspect-ratio data or the #Shorts hashtag
    in the title/description.
    """
    if duration_seconds is not None and duration_seconds <= 60:
        return True
    return False


def _safe_int(value) -> Optional[int]:
    """Safely parse a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_datetime(iso_string: Optional[str]) -> Optional[datetime]:
    """Parse a YouTube ISO datetime string to a Python datetime."""
    if not iso_string:
        return None
    try:
        return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ── Channel Operations ────────────────────────────────────────────────────

def upsert_channel(db: Session, api_data: dict) -> Channel:
    """
    Insert or update a Channel record from a YouTube API channel response.
    Returns the persisted Channel instance.
    """
    channel_id = api_data["id"]
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        channel = Channel(id=channel_id)

    snippet = api_data.get("snippet", {})
    statistics = api_data.get("statistics", {})
    topic_details = api_data.get("topicDetails", {})
    branding = api_data.get("brandingSettings", {})

    channel.title = snippet.get("title", "Unknown")
    channel.handle = snippet.get("customUrl") or snippet.get("handle")
    channel.description = snippet.get("description")
    channel.country = snippet.get("country")
    channel.language = (
        snippet.get("defaultLanguage")
        or branding.get("channel", {}).get("defaultLanguage")
    )
    channel.created_at = _parse_datetime(snippet.get("publishedAt"))

    channel.subscriber_count = _safe_int(statistics.get("subscriberCount"))
    channel.video_count = _safe_int(statistics.get("videoCount"))
    channel.view_count = _safe_int(statistics.get("viewCount"))

    if "topicCategories" in topic_details:
        channel.topics = ",".join(topic_details["topicCategories"])

    channel.banner_url = branding.get("image", {}).get("bannerExternalUrl")
    channel.profile_image_url = (
        snippet.get("thumbnails", {}).get("default", {}).get("url")
    )
    channel.hidden_subscriber_count = statistics.get("hiddenSubscriberCount")

    db.add(channel)
    db.commit()
    db.refresh(channel)
    logger.info(f"Upserted channel: {channel}")
    return channel


# ── Video Operations ──────────────────────────────────────────────────────

def upsert_video(db: Session, api_data: dict) -> Video:
    """
    Insert or update a Video record from a YouTube API video response.
    Returns the persisted Video instance.
    """
    video_id = api_data["id"]
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        video = Video(id=video_id)

    snippet = api_data.get("snippet", {})
    statistics = api_data.get("statistics", {})
    content_details = api_data.get("contentDetails", {})
    status = api_data.get("status", {})

    video.channel_id = snippet.get("channelId")
    video.title = snippet.get("title", "Untitled")
    video.description = snippet.get("description")
    video.tags = ",".join(snippet.get("tags", [])) if snippet.get("tags") else None
    video.published_at = _parse_datetime(snippet.get("publishedAt"))
    video.duration = content_details.get("duration")
    video.duration_seconds = (
        parse_duration_to_seconds(video.duration) if video.duration else None
    )
    video.category_id = snippet.get("categoryId")
    video.made_for_kids = status.get("madeForKids")
    video.is_short = detect_is_short(video.duration_seconds)

    video.view_count = _safe_int(statistics.get("viewCount"))
    video.like_count = _safe_int(statistics.get("likeCount"))
    video.comment_count = _safe_int(statistics.get("commentCount"))

    video.thumbnail_url = (
        snippet.get("thumbnails", {}).get("high", {}).get("url")
        or snippet.get("thumbnails", {}).get("default", {}).get("url")
    )

    db.add(video)
    db.commit()
    db.refresh(video)
    return video


# ── Snapshot Operations ───────────────────────────────────────────────────

def add_snapshot(
    db: Session,
    video_id: str,
    view_count: int,
    like_count: Optional[int] = None,
    comment_count: Optional[int] = None,
) -> VideoSnapshot:
    """
    Record a point-in-time snapshot of a video's statistics.
    These snapshots are the raw data for computing VPH later.
    """
    snapshot = VideoSnapshot(
        video_id=video_id,
        view_count=view_count,
        like_count=like_count,
        comment_count=comment_count,
    )
    db.add(snapshot)
    db.commit()
    return snapshot


# ── Orchestration ─────────────────────────────────────────────────────────

def fetch_and_store_channel(db: Session, channel_id: str) -> Optional[Channel]:
    """
    Fetch a channel from the YouTube API and upsert it into the database.
    Returns the Channel, or None if the channel doesn't exist on YouTube.
    """
    client = _get_client()
    api_data = client.get_channel_details(channel_id)
    if not api_data:
        return None
    return upsert_channel(db, api_data)


def fetch_and_store_video(db: Session, video_id: str) -> Optional[Video]:
    """
    Fetch a single video from YouTube, upsert it, and create a snapshot.
    Returns the Video, or None if the video doesn't exist.
    """
    client = _get_client()
    api_data = client.get_video_details(video_id)
    if not api_data:
        return None

    video = upsert_video(db, api_data)

    # Record snapshot for VPH tracking
    if video.view_count is not None:
        add_snapshot(db, video.id, video.view_count, video.like_count, video.comment_count)

    return video


def fetch_and_store_channel_videos(
    db: Session,
    channel_id: str,
    max_results: int = 50,
) -> List[Video]:
    """
    Fetch a channel's recent uploads, store the channel + all videos,
    and create snapshots for each video.

    This is the main "ingest" function used when analyzing a channel.

    Steps:
    1. Ensure the channel record exists (upsert from API).
    2. List the channel's uploads playlist (cheap: 1 quota unit/page).
    3. Batch-fetch full video details for all listed videos.
    4. Upsert each video + create a snapshot.
    """
    client = _get_client()

    # Step 1: Upsert channel
    fetch_and_store_channel(db, channel_id)

    # Step 2: Get upload list (video IDs only)
    playlist_items = client.get_channel_videos(channel_id, max_results)
    video_ids = [
        item["contentDetails"]["videoId"]
        for item in playlist_items
        if "contentDetails" in item and "videoId" in item["contentDetails"]
    ]
    if not video_ids:
        logger.info(f"No videos found for channel {channel_id}")
        return []

    logger.info(f"Fetching details for {len(video_ids)} videos from channel {channel_id}")

    # Step 3: Batch-fetch full video details
    videos_data = client.get_videos_details_batch(video_ids)

    # Step 4: Upsert each video + snapshot
    videos: List[Video] = []
    for vdata in videos_data:
        video = upsert_video(db, vdata)
        if video.view_count is not None:
            add_snapshot(db, video.id, video.view_count, video.like_count, video.comment_count)
        videos.append(video)

    logger.info(f"Stored {len(videos)} videos for channel {channel_id}")
    return videos
