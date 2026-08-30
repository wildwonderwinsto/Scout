"""
Channel analysis service.

Provides comprehensive analysis of a single YouTube channel:
- Channel metadata and stats
- Average views per video
- All recent videos ranked by breakout score
- Top outlier videos (breakout >= 2x)
- Channel health metrics (posting frequency, format ratio, activity)
- Engagement anomaly detection (fake view flagging)
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging

from app.services.data_fetcher import (
    fetch_and_store_channel,
    fetch_and_store_channel_videos,
    _get_client,
)
from app.services.trend_scanner import (
    compute_channel_avg_views,
    compute_channel_median_views,
    compute_breakout_score,
    compute_engagement_rate,
    compute_vph_from_snapshots,
    compute_average_vph,
    compute_published_days_ago,
    _build_ranked_video,
    _sort_results,
)
from app.utils.channel_utils import resolve_channel_id
from app.models.channel import Channel
from app.models.video import Video
from app.schemas.scan import RankedVideo

logger = logging.getLogger(__name__)


def analyze_channel(
    db: Session,
    channel_input: str,
    max_videos: int = 50,
    outlier_threshold: float = 2.0,
) -> Dict[str, Any]:
    """
    Comprehensive channel analysis.

    Args:
        db: Database session.
        channel_input: Channel ID, URL, or handle.
        max_videos: Number of recent videos to analyze.
        outlier_threshold: Minimum breakout score to qualify as an outlier.

    Returns a dict with:
        - channel: Channel metadata + stats
        - average_views: Lifetime avg views per video
        - recent_videos: All recent videos ranked by breakout
        - top_outliers: Videos with breakout >= threshold
        - health: Channel health metrics
        - engagement_analysis: Engagement distribution info
    """
    # ── Resolve channel ID ────────────────────────────────────────────
    client = _get_client()
    channel_id = resolve_channel_id(channel_input, client)
    if not channel_id:
        return {
            "error": f"Could not resolve channel from input: '{channel_input}'",
            "channel": None,
            "average_views": 0,
            "recent_videos": [],
            "top_outliers": [],
            "health": {},
            "engagement_analysis": {},
            "analyzed_at": datetime.now(timezone.utc),
        }

    # ── Fetch channel + videos ────────────────────────────────────────
    channel = fetch_and_store_channel(db, channel_id)
    if not channel:
        return {
            "error": f"Channel {channel_id} not found on YouTube",
            "channel": None,
            "average_views": 0,
            "recent_videos": [],
            "top_outliers": [],
            "health": {},
            "engagement_analysis": {},
            "analyzed_at": datetime.now(timezone.utc),
        }

    videos = fetch_and_store_channel_videos(db, channel_id, max_results=max_videos)
    channel_avg = compute_channel_avg_views(channel)
    channel_median = compute_channel_median_views(db, channel.id)
    baseline_views = channel_median if channel_median > 0 else channel_avg

    # ── Score every video ─────────────────────────────────────────────
    ranked_videos: List[RankedVideo] = []
    engagement_rates: List[float] = []

    for video in videos:
        if not video.view_count or video.view_count <= 0:
            continue

        engagement = compute_engagement_rate(video)
        breakout = compute_breakout_score(video.view_count, baseline_views)

        vph = compute_vph_from_snapshots(db, video.id)
        vph_source = "snapshot" if vph > 0 else "average"
        if vph == 0:
            vph = compute_average_vph(video)

        ranked = _build_ranked_video(
            video=video,
            channel=channel,
            channel_avg=channel_avg,
            channel_median=channel_median,
            vph=vph,
            vph_source=vph_source,
            engagement=engagement,
            breakout=breakout,
        )
        ranked_videos.append(ranked)
        engagement_rates.append(engagement)

    # Sort by breakout score (highest outliers first)
    ranked_videos = _sort_results(ranked_videos, "breakout")

    # ── Extract outliers ──────────────────────────────────────────────
    top_outliers = [rv for rv in ranked_videos if rv.breakout_score >= outlier_threshold]

    # ── Compute health metrics ────────────────────────────────────────
    health = _compute_channel_health(videos)

    # ── Engagement analysis ───────────────────────────────────────────
    engagement_analysis = _compute_engagement_analysis(engagement_rates, ranked_videos)

    # ── Build channel summary ─────────────────────────────────────────
    channel_summary = {
        "id": channel.id,
        "title": channel.title,
        "handle": channel.handle,
        "description": channel.description,
        "country": channel.country,
        "language": channel.language,
        "created_at": channel.created_at.isoformat() if channel.created_at else None,
        "subscriber_count": channel.subscriber_count,
        "video_count": channel.video_count,
        "view_count": channel.view_count,
        "profile_image_url": channel.profile_image_url,
        "banner_url": channel.banner_url,
        "topics": channel.topics,
    }

    return {
        "channel": channel_summary,
        "average_views": round(channel_avg, 2),
        "total_videos_analyzed": len(ranked_videos),
        "recent_videos": [rv.dict() for rv in ranked_videos],
        "top_outliers": [rv.dict() for rv in top_outliers],
        "outlier_count": len(top_outliers),
        "health": health,
        "engagement_analysis": engagement_analysis,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def _compute_channel_health(videos: List[Video]) -> Dict[str, Any]:
    """
    Compute channel health metrics from video data.

    Returns:
        - videos_last_7d: Number of videos published in last 7 days
        - videos_last_30d: Number of videos published in last 30 days
        - shorts_count: Total shorts in the set
        - long_count: Total long-form videos
        - shorts_ratio: Fraction of videos that are shorts
        - avg_days_between_uploads: Average gap between uploads
        - last_upload_days_ago: Days since most recent upload
        - is_active: True if at least 1 video in last 14 days
        - posting_consistency: "high" / "medium" / "low" / "inactive"
    """
    now = datetime.now(timezone.utc)

    # Separate by format
    shorts = [v for v in videos if v.is_short]
    longs = [v for v in videos if not v.is_short]

    # Recency buckets
    videos_with_dates = [
        v for v in videos
        if v.published_at is not None
    ]

    # Make all dates timezone-aware
    def _aware(dt):
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    videos_7d = [
        v for v in videos_with_dates
        if _aware(v.published_at) >= now - timedelta(days=7)
    ]
    videos_30d = [
        v for v in videos_with_dates
        if _aware(v.published_at) >= now - timedelta(days=30)
    ]

    # Upload gaps
    sorted_dates = sorted(
        [_aware(v.published_at) for v in videos_with_dates],
        reverse=True,
    )

    last_upload_days_ago = None
    avg_days_between = None

    if sorted_dates:
        last_upload_days_ago = (now - sorted_dates[0]).days
        if len(sorted_dates) >= 2:
            gaps = [
                (sorted_dates[i] - sorted_dates[i + 1]).days
                for i in range(len(sorted_dates) - 1)
            ]
            avg_days_between = round(sum(gaps) / len(gaps), 1) if gaps else None

    # Posting consistency
    is_active = last_upload_days_ago is not None and last_upload_days_ago <= 14
    if len(videos_7d) >= 3:
        consistency = "high"
    elif len(videos_30d) >= 4:
        consistency = "medium"
    elif len(videos_30d) >= 1:
        consistency = "low"
    else:
        consistency = "inactive"

    return {
        "videos_last_7d": len(videos_7d),
        "videos_last_30d": len(videos_30d),
        "shorts_count": len(shorts),
        "long_count": len(longs),
        "shorts_ratio": round(len(shorts) / len(videos), 2) if videos else 0,
        "avg_days_between_uploads": avg_days_between,
        "last_upload_days_ago": last_upload_days_ago,
        "is_active": is_active,
        "posting_consistency": consistency,
    }


def _compute_engagement_analysis(
    engagement_rates: List[float],
    ranked_videos: List[RankedVideo],
) -> Dict[str, Any]:
    """
    Analyze engagement patterns to detect anomalies.

    Flags videos with suspiciously low engagement compared to the
    channel's average — a potential sign of bought views.
    """
    if not engagement_rates:
        return {
            "avg_engagement_rate": 0,
            "median_engagement_rate": 0,
            "low_engagement_videos": 0,
            "suspicious_videos": [],
        }

    sorted_rates = sorted(engagement_rates)
    avg_eng = sum(sorted_rates) / len(sorted_rates)
    median_eng = sorted_rates[len(sorted_rates) // 2]

    # Flag videos with engagement < 50% of channel average
    threshold = avg_eng * 0.5
    suspicious = [
        {
            "video_id": rv.video_id,
            "title": rv.title,
            "engagement_rate": rv.engagement_rate,
            "view_count": rv.view_count,
            "reason": "engagement_below_half_avg",
        }
        for rv in ranked_videos
        if rv.engagement_rate < threshold and rv.view_count > 0
    ]

    return {
        "avg_engagement_rate": round(avg_eng, 4),
        "median_engagement_rate": round(median_eng, 4),
        "low_engagement_videos": len([r for r in engagement_rates if r < 0.02]),
        "suspicious_videos": suspicious,
    }
