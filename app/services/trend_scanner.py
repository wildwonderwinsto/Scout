"""
Trend scanning and ranking engine.

This is the core intelligence of the application.  It orchestrates:
1. Channel discovery — find candidate channels via YouTube search
2. Video ingestion — fetch recent videos from discovered channels
3. Metric computation — breakout score, VPH, engagement rate
4. Filtering — subscriber band, language, recency, format, quality gates
5. Ranking — sort by breakout score (default) with VPH tiebreak

Two entry points:
  general_scan(db, filters)  — "Find me ANYTHING blowing up from small English channels"
  keyword_scan(db, filters)  — "Find me a proven topic for my niche"

Both return a list of RankedVideo dicts ready for the API response.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import logging
import random

from app.services.youtube_client import YouTubeClient
from app.services.data_fetcher import (
    upsert_channel,
    upsert_video,
    add_snapshot,
    fetch_and_store_channel_videos,
    _get_client,
)
from app.utils.channel_utils import resolve_channel_id
from app.models.channel import Channel
from app.models.video import Video
from app.models.snapshot import VideoSnapshot
from app.schemas.scan import ScanFilters, RankedVideo

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
#  METRIC COMPUTATION
# ══════════════════════════════════════════════════════════════════════════

# Broad keywords used by general_scan to bypass the megachannel bias
BROAD_NICHES = [
    "vlog", "gaming", "tech review", "finance", "tutorial", "unboxing",
    "fitness", "cooking", "travel", "setup tour", "reaction", "day in the life",
    "podcast clips", "make money online", "study with me", "indie game",
    "street food", "budget setup", "car review", "coding", "software engineering",
    "productivity", "desk setup", "minimalist", "sneaker review", "true crime",
    "mystery", "documentary", "asmr", "funny compilation"
]

def compute_channel_avg_views(channel: Channel) -> float:
    """
    Average views per video = total views / video count.
    This is the baseline denominator for Breakout Score.
    """
    if channel.video_count and channel.video_count > 0 and channel.view_count:
        return channel.view_count / channel.video_count
    return 0.0


def compute_channel_median_views(db: Session, channel_id: str) -> float:
    """
    Calculate the median views for a channel's videos in our database.
    Median is more robust to outlier mega-viral videos than average.
    """
    views_query = db.query(Video.view_count).filter(
        Video.channel_id == channel_id,
        Video.view_count != None,
        Video.view_count > 0
    ).order_by(Video.view_count).all()
    
    if not views_query:
        return 0.0
        
    counts = [v[0] for v in views_query]
    n = len(counts)
    mid = n // 2
    if n % 2 == 0:
        return (counts[mid - 1] + counts[mid]) / 2.0
    else:
        return float(counts[mid])


def compute_breakout_score(video_views: int, baseline_views: float) -> float:
    """
    Breakout Score = Video Views / Channel Average Views.

    A 100K video on a 10K-average channel = 10x breakout.
    A 2M video on a 1.5M-average channel = 1.3x — not impressive.

    The whole point: a 50K video on a 5K channel outranks a 2M video
    on a 1.5M channel because it's a bigger signal you can learn from.
    """
    if baseline_views > 0:
        return round(video_views / baseline_views, 2)
    return 0.0


def compute_engagement_rate(video: Video) -> float:
    """
    Engagement Rate = (Likes + Comments) / Views.
    Used as a quality gate to filter out bought/viewbait views.
    Videos below 2% may indicate fake traffic.
    """
    if video.view_count and video.view_count > 0:
        likes = video.like_count or 0
        comments = video.comment_count or 0
        return round((likes + comments) / video.view_count, 4)
    return 0.0


def compute_vph_from_snapshots(db: Session, video_id: str, window_hours: float = 2.0) -> float:
    """
    Compute Views Per Hour from the two most recent snapshots.

    If we have at least 2 snapshots separated in time within the window,
    we compute the actual velocity.

    Returns 0.0 if insufficient snapshot data.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    snapshots = (
        db.query(VideoSnapshot)
        .filter(
            VideoSnapshot.video_id == video_id,
            VideoSnapshot.captured_at >= since
        )
        .order_by(VideoSnapshot.captured_at.desc())
        .limit(2)
        .all()
    )
    if len(snapshots) < 2:
        return 0.0

    latest = snapshots[0]
    previous = snapshots[1]

    time_diff_seconds = (latest.captured_at - previous.captured_at).total_seconds()
    if time_diff_seconds <= 0:
        return 0.0

    view_diff = latest.view_count - previous.view_count
    if view_diff < 0:
        return 0.0

    vph = (view_diff / time_diff_seconds) * 3600
    return round(vph, 2)


def compute_average_vph(video: Video) -> float:
    """
    Fallback VPH: overall average views per hour since publication.

    This is used when we don't have multiple snapshots (first scan).
    Formula: total_views / hours_since_published.

    Less accurate than snapshot-based VPH but still useful for ranking —
    a 3-day-old video with 100K views (1389 vph) outranks a 30-day-old
    video with 100K views (139 vph).
    """
    if video.published_at and video.view_count and video.view_count > 0:
        now = datetime.now(timezone.utc)
        published = video.published_at
        # Make published timezone-aware if it isn't already
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        hours = (now - published).total_seconds() / 3600
        if hours > 0:
            return round(video.view_count / hours, 2)
    return 0.0


def compute_published_days_ago(published_at: Optional[datetime]) -> Optional[int]:
    """How many days ago was this video published?"""
    if not published_at:
        return None
    now = datetime.now(timezone.utc)
    pub = published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    return max(0, (now - pub).days)


# ══════════════════════════════════════════════════════════════════════════
#  FILTERING
# ══════════════════════════════════════════════════════════════════════════

def _channel_matches_filters(channel: Channel, filters: ScanFilters, db: Optional[Session] = None) -> bool:
    """
    Check if a channel passes all filter criteria.

    Filters applied:
    - Subscriber band (subscriber_min to subscriber_max)
    - Language (must match one of filters.languages)
    - Country (must match one of filters.countries, if specified)
    - Hidden subscribers are excluded
    - Activity: min_recent_videos in last 7 days (if db is provided)
    """
    # Subscriber band
    subs = channel.subscriber_count
    if subs is None:
        return False
    if subs < filters.subscriber_min or subs > filters.subscriber_max:
        return False

    # Skip channels that hide their subscriber count
    if channel.hidden_subscriber_count:
        return False

    # Max channel videos filter (for finding new/early channels)
    if filters.channel_video_max is not None:
        vid_count = channel.video_count
        if vid_count is not None and vid_count > filters.channel_video_max:
            return False

    # Language filter
    if filters.languages:
        channel_lang = (channel.language or "").lower()
        if channel_lang and channel_lang not in [l.lower() for l in filters.languages]:
            return False
        # If channel has no language set, we let it through (can't verify)

    # Country filter (optional — for high-RPM targeting)
    if filters.countries:
        channel_country = (channel.country or "").upper()
        if not channel_country or channel_country not in [c.upper() for c in filters.countries]:
            return False

    # Activity filter (min recent videos)
    if filters.min_recent_videos > 0 and db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_count = (
            db.query(Video)
            .filter(
                Video.channel_id == channel.id,
                Video.published_at >= cutoff
            )
            .count()
        )
        if recent_count < filters.min_recent_videos:
            return False

    return True


def _video_matches_filters(
    video: Video,
    filters: ScanFilters,
    cutoff_date: datetime,
) -> bool:
    """
    Check if a video passes all filter criteria.

    Filters applied:
    - Recency (published after cutoff_date)
    - Format (short / long / all)
    - Has views (skip zero-view videos)
    """
    # Must have views
    if not video.view_count or video.view_count <= 0:
        return False

    if filters.min_views is not None and video.view_count < filters.min_views:
        return False
        
    if filters.max_views is not None and video.view_count > filters.max_views:
        return False

    # Recency
    if video.published_at:
        pub = video.published_at
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub < cutoff_date:
            return False

    # Format filter
    if filters.video_format == "short" and not video.is_short:
        return False
    if filters.video_format == "long" and video.is_short:
        return False

    return True


# ══════════════════════════════════════════════════════════════════════════
#  RANKING: Build a RankedVideo from raw data
# ══════════════════════════════════════════════════════════════════════════

def _build_ranked_video(
    video: Video,
    channel: Channel,
    channel_avg: float,
    channel_median: float,
    vph: float,
    vph_source: str,
    engagement: float,
    breakout: float,
    engagement_flag: bool = False,
    channel_recent_videos_7d: int = 0,
) -> RankedVideo:
    """Assemble a RankedVideo response object from computed metrics."""
    return RankedVideo(
        video_id=video.id,
        title=video.title,
        thumbnail_url=video.thumbnail_url,
        published_at=video.published_at,
        published_days_ago=compute_published_days_ago(video.published_at),
        is_short=video.is_short or False,
        duration_seconds=video.duration_seconds,
        view_count=video.view_count or 0,
        like_count=video.like_count,
        comment_count=video.comment_count,
        channel_id=channel.id,
        channel_title=channel.title,
        subscriber_count=channel.subscriber_count,
        channel_avg_views=round(channel_avg, 2),
        channel_country=channel.country,
        channel_language=channel.language,
        channel_median_views=round(channel_median, 2),
        breakout_score=breakout,
        vph=vph,
        engagement_rate=engagement,
        engagement_flag=engagement_flag,
        channel_recent_videos_7d=channel_recent_videos_7d,
        vph_source=vph_source,
    )


# ══════════════════════════════════════════════════════════════════════════
#  SORTING
# ══════════════════════════════════════════════════════════════════════════

def _sort_results(
    results: List[RankedVideo],
    sort_by: str = "breakout",
    deduplicate: bool = True,
) -> List[RankedVideo]:
    """
    Sort results by the requested metric.

    Default ranking logic from the spec:
    - 1st sort by breakout_score (proven format)
    - 2nd tiebreak by vph (hot right now)
    - 3rd filter by published_days_ago <= 3 for velocity, <= 14 for outlier

    For "vph" sort, we reverse the priority.

    If deduplicate is True, keep only the best video per channel.
    Set to False for single-channel scans where you want all videos.
    """
    if sort_by == "breakout":
        # Primary: breakout desc, tiebreak: vph desc
        results.sort(key=lambda r: (r.breakout_score, r.vph), reverse=True)
    elif sort_by == "vph":
        # Primary: vph desc, tiebreak: breakout desc
        results.sort(key=lambda r: (r.vph, r.breakout_score), reverse=True)
    elif sort_by == "views":
        results.sort(key=lambda r: r.view_count, reverse=True)
    elif sort_by == "date":
        results.sort(key=lambda r: r.published_at or datetime.min, reverse=True)

    if not deduplicate:
        return results

    # Channel-level deduplication: keep only the best video per channel
    seen_channels = set()
    deduped = []
    for r in results:
        if r.channel_id not in seen_channels:
            deduped.append(r)
            seen_channels.add(r.channel_id)

    return deduped


# ══════════════════════════════════════════════════════════════════════════
#  CORE: Process a channel's videos through the ranking pipeline
# ══════════════════════════════════════════════════════════════════════════

def _score_channel_videos(
    db: Session,
    channel: Channel,
    videos: List[Video],
    filters: ScanFilters,
    cutoff_date: datetime,
) -> List[RankedVideo]:
    """
    Take a channel + its videos, apply all filters, compute all metrics,
    and return the qualifying RankedVideo objects.

    This is the inner scoring loop used by both general_scan and keyword_scan.
    """
    channel_avg = compute_channel_avg_views(channel)
    channel_median = compute_channel_median_views(db, channel.id)
    # Fallback to average if median is 0
    baseline_views = channel_median if channel_median > 0 else channel_avg
    results = []

    # Calculate channel's recent video count (last 7 days) and average engagement
    now = datetime.now(timezone.utc)
    recent_7d_cutoff = now - timedelta(days=7)
    channel_recent_videos_7d = sum(
        1 for v in videos
        if v.published_at and (
            v.published_at.replace(tzinfo=timezone.utc) if v.published_at.tzinfo is None else v.published_at
        ) >= recent_7d_cutoff
    )

    all_engagements = [compute_engagement_rate(v) for v in videos if v.view_count and v.view_count > 0]
    avg_channel_engagement = sum(all_engagements) / len(all_engagements) if all_engagements else 0.0

    for video in videos:
        # ── Video-level filters ───────────────────────────────────────
        if not _video_matches_filters(video, filters, cutoff_date):
            continue

        # ── Compute metrics ───────────────────────────────────────────
        engagement = compute_engagement_rate(video)
        
        # Fake view detection flag (if engagement < 0.5% or suspiciously below channel average)
        engagement_flag = False
        if engagement < 0.005 or (avg_channel_engagement > 0 and engagement < (avg_channel_engagement * filters.engagement_ratio_threshold)):
            engagement_flag = True

        if filters.min_engagement_rate and engagement < filters.min_engagement_rate:
            continue

        breakout = compute_breakout_score(video.view_count, baseline_views)
        if filters.min_breakout and breakout < filters.min_breakout:
            continue

        # VPH: try snapshot-based first, fall back to lifetime average
        vph = compute_vph_from_snapshots(db, video.id)
        vph_source = "snapshot" if vph > 0 else "average"
        if vph == 0:
            vph = compute_average_vph(video)

        if filters.min_vph and vph < filters.min_vph:
            continue

        # ── Build result ──────────────────────────────────────────────
        ranked = _build_ranked_video(
            video=video,
            channel=channel,
            channel_avg=channel_avg,
            channel_median=channel_median,
            vph=vph,
            vph_source=vph_source,
            engagement=engagement,
            breakout=breakout,
            engagement_flag=engagement_flag,
            channel_recent_videos_7d=channel_recent_videos_7d,
        )
        results.append(ranked)

    return results


# ══════════════════════════════════════════════════════════════════════════
#  DISCOVERY: Find candidate channels from YouTube search
# ══════════════════════════════════════════════════════════════════════════

def discover_channels_from_recent_videos(
    db: Session,
    filters: ScanFilters,
    max_channels: int = 20,
    keyword_override: Optional[str] = None,
) -> List[Channel]:
    """
    Discover channels by searching for recent popular videos and then
    filtering the parent channels by subscriber band / language / country.

    Strategy:
    1. Use search_videos_advanced to find recent high-view videos.
    2. Extract unique channel IDs from the results.
    3. Batch-fetch channel details.
    4. Filter channels by subscriber range, language, country.
    5. Return qualifying channels (up to max_channels).
    """
    client = _get_client()
    cutoff = datetime.now(timezone.utc) - timedelta(days=filters.published_days_ago + 1)
    published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Map video_format to YouTube's videoDuration parameter
    video_duration = None
    if filters.video_format == "short":
        video_duration = "short"  # YouTube: < 4 minutes
    elif filters.video_format == "long":
        video_duration = "long"   # YouTube: > 20 minutes

    query_to_use = keyword_override if keyword_override is not None else filters.query

    # Search for recent popular videos
    search_results = client.search_videos_advanced(
        query=query_to_use,
        order="relevance",
        max_results=50,
        published_after=published_after,
        video_duration=video_duration,
        relevance_language=filters.languages[0] if filters.languages else None,
        region_code=filters.countries[0] if filters.countries else None,
    )

    # Extract unique channel IDs
    channel_ids = list(set(
        item["snippet"]["channelId"]
        for item in search_results
        if "snippet" in item and "channelId" in item["snippet"]
    ))

    if not channel_ids:
        logger.info("No channels discovered from video search")
        return []

    logger.info(f"Discovered {len(channel_ids)} candidate channels from {len(search_results)} videos")

    # Batch-fetch channel details
    channels_data = client.get_channels_details_batch(channel_ids)

    # Filter and upsert channels
    discovered = []
    for ch_data in channels_data:
        channel = upsert_channel(db, ch_data)
        if _channel_matches_filters(channel, filters, db):
            discovered.append(channel)
            if len(discovered) >= max_channels:
                break

    logger.info(
        f"After filtering: {len(discovered)} channels match criteria "
        f"(subs {filters.subscriber_min}-{filters.subscriber_max}, "
        f"lang={filters.languages})"
    )
    return discovered


# ══════════════════════════════════════════════════════════════════════════
#  SCAN ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════

def general_scan(
    db: Session,
    filters: ScanFilters,
) -> Dict[str, Any]:
    """
    General Scan — "Find me ANYTHING blowing up from small English channels."

    Process:
    1. Discover channels from recent popular videos (filtered by criteria).
    2. For each qualifying channel, fetch its recent videos.
    3. Score each video (breakout, VPH, engagement).
    4. Apply quality gates.
    5. Rank by breakout score (tiebreak: VPH).
    6. Return top N results.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=filters.published_days_ago + 1)

    # Step 1: Discover channels
    # Instead of doing a blank query (which returns massive global channels),
    # we pick 3 random broad niches to force the search into specific topics
    # where small channels can actually rank in the top 50.
    channels_found = []
    niches_to_scan = random.sample(BROAD_NICHES, min(3, len(BROAD_NICHES)))
    
    for niche in niches_to_scan:
        logger.info(f"General scan keyword roulette: checking niche '{niche}'")
        found = discover_channels_from_recent_videos(
            db, filters, max_channels=10, keyword_override=niche
        )
        channels_found.extend(found)

    # Deduplicate by ID
    channels_dict = {c.id: c for c in channels_found}
    channels = list(channels_dict.values())

    all_results: List[RankedVideo] = []
    total_videos_evaluated = 0

    # Step 2-4: For each channel, fetch videos and score them
    for channel in channels:
        try:
            videos = fetch_and_store_channel_videos(db, channel.id, max_results=30)
            total_videos_evaluated += len(videos)
            scored = _score_channel_videos(db, channel, videos, filters, cutoff)
            all_results.extend(scored)
        except Exception as e:
            logger.warning(f"Error scanning channel {channel.id} ({channel.title}): {e}")
            continue

    # Step 5: Sort combined results
    all_results = _sort_results(all_results, filters.sort_by)

    # Step 6: Trim to max_results
    all_results = all_results[:filters.max_results]

    return {
        "scan_type": "general",
        "query": filters.query,
        "filters_applied": filters,
        "total_channels_scanned": len(channels),
        "total_videos_evaluated": total_videos_evaluated,
        "results": all_results,
        "sort_by": filters.sort_by,
        "scanned_at": datetime.now(timezone.utc),
    }


def keyword_scan(
    db: Session,
    filters: ScanFilters,
) -> Dict[str, Any]:
    """
    Keyword Scan — "Find me a proven topic for my niche."

    Process:
    1. Search YouTube for videos matching the query with high views.
    2. Fetch full video details (stats, duration, etc.).
    3. Fetch channel details for each video's parent channel.
    4. Filter channels by subscriber band / language / country.
    5. Score each video (breakout, VPH, engagement).
    6. Apply quality gates.
    7. Rank and return.

    This is more targeted than general_scan — it finds outliers within
    a specific topic/niche rather than across all of YouTube.
    """
    if not filters.query:
        return {
            "scan_type": "keyword",
            "query": None,
            "filters_applied": filters,
            "total_channels_scanned": 0,
            "total_videos_evaluated": 0,
            "results": [],
            "sort_by": filters.sort_by,
            "scanned_at": datetime.now(timezone.utc),
        }

    client = _get_client()
    cutoff = datetime.now(timezone.utc) - timedelta(days=filters.published_days_ago + 1)
    published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Map format filter
    video_duration = None
    if filters.video_format == "short":
        video_duration = "short"
    elif filters.video_format == "long":
        video_duration = "long"

    # Step 1: Search for videos matching the keyword
    search_results = client.search_videos_advanced(
        query=filters.query,
        order="relevance",
        max_results=50,
        published_after=published_after,
        video_duration=video_duration,
        relevance_language=filters.languages[0] if filters.languages else None,
        region_code=filters.countries[0] if filters.countries else None,
    )

    # Extract video IDs
    video_ids = [
        item["id"]["videoId"]
        for item in search_results
        if "id" in item and "videoId" in item.get("id", {})
    ]

    if not video_ids:
        logger.info(f"No videos found for keyword '{filters.query}'")
        return {
            "scan_type": "keyword",
            "query": filters.query,
            "filters_applied": filters,
            "total_channels_scanned": 0,
            "total_videos_evaluated": 0,
            "results": [],
            "sort_by": filters.sort_by,
            "scanned_at": datetime.now(timezone.utc),
        }

    # Step 2: Fetch full video details
    videos_data = client.get_videos_details_batch(video_ids)

    # Step 3: Collect unique channel IDs and fetch their details
    channel_ids = list(set(
        vdata["snippet"]["channelId"]
        for vdata in videos_data
        if "snippet" in vdata and "channelId" in vdata["snippet"]
    ))
    channels_data = client.get_channels_details_batch(channel_ids)

    # Build channel map (upsert each into DB)
    channel_map: Dict[str, Channel] = {}
    for ch_data in channels_data:
        channel = upsert_channel(db, ch_data)
        channel_map[channel.id] = channel

    # Step 4-6: Score each video
    all_results: List[RankedVideo] = []
    channels_that_qualified = set()

    for vdata in videos_data:
        video = upsert_video(db, vdata)

        # Create snapshot for VPH tracking
        if video.view_count is not None:
            add_snapshot(db, video.id, video.view_count, video.like_count, video.comment_count)

        channel = channel_map.get(video.channel_id)
        if not channel:
            continue

        # Channel-level filter
        if not _channel_matches_filters(channel, filters, db):
            continue
        channels_that_qualified.add(channel.id)

        # Score this video
        scored = _score_channel_videos(db, channel, [video], filters, cutoff)
        all_results.extend(scored)

    # Step 7: Sort and trim
    all_results = _sort_results(all_results, filters.sort_by)
    all_results = all_results[:filters.max_results]

    return {
        "scan_type": "keyword",
        "query": filters.query,
        "filters_applied": filters,
        "total_channels_scanned": len(channels_that_qualified),
        "total_videos_evaluated": len(videos_data),
        "results": all_results,
        "sort_by": filters.sort_by,
        "scanned_at": datetime.now(timezone.utc),
    }


def channel_scan(
    db: Session,
    channel_id: str,
    filters: ScanFilters,
) -> Dict[str, Any]:
    """
    Channel Scan — "Analyze THIS specific channel."

    Fetches the channel's recent videos, scores them all against the
    channel's own average, and returns ranked results.

    This is for when the user pastes a channel URL directly.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=filters.published_days_ago + 1)
    client = _get_client()
    
    # Convert handles or URLs to raw UC... ID
    real_channel_id = resolve_channel_id(channel_id, client)
    if not real_channel_id:
        # Fallback to the input if it fails to resolve
        real_channel_id = channel_id

    # Fetch channel + videos
    videos = fetch_and_store_channel_videos(db, real_channel_id, max_results=50)
    channel = db.query(Channel).filter(Channel.id == real_channel_id).first()

    if not channel:
        return {
            "scan_type": "channel",
            "query": channel_id,
            "filters_applied": filters,
            "total_channels_scanned": 0,
            "total_videos_evaluated": 0,
            "results": [],
            "sort_by": filters.sort_by,
            "scanned_at": datetime.now(timezone.utc),
        }

    # Score videos (skip channel-level subscriber/language filters for direct channel scan)
    channel_avg = compute_channel_avg_views(channel)
    channel_median = compute_channel_median_views(db, channel.id)
    baseline_views = channel_median if channel_median > 0 else channel_avg
    all_results: List[RankedVideo] = []

    for video in videos:
        if not _video_matches_filters(video, filters, cutoff):
            continue

        engagement = compute_engagement_rate(video)
        breakout = compute_breakout_score(video.view_count, baseline_views)

        vph = compute_vph_from_snapshots(db, video.id)
        vph_source = "snapshot" if vph > 0 else "average"
        if vph == 0:
            vph = compute_average_vph(video)

        # Direct channel scan doesn't have a channel average to compare against yet, 
        # but we still apply the hard 0.5% flag
        engagement_flag = True if engagement < 0.005 else False

        ranked = _build_ranked_video(
            video=video,
            channel=channel,
            channel_avg=channel_avg,
            channel_median=channel_median,
            vph=vph,
            vph_source=vph_source,
            engagement=engagement,
            breakout=breakout,
            engagement_flag=engagement_flag,
        )
        all_results.append(ranked)

    all_results = _sort_results(all_results, filters.sort_by, deduplicate=False)
    all_results = all_results[:filters.max_results]

    return {
        "scan_type": "channel",
        "query": channel_id,
        "filters_applied": filters,
        "total_channels_scanned": 1,
        "total_videos_evaluated": len(videos),
        "results": all_results,
        "sort_by": filters.sort_by,
        "scanned_at": datetime.now(timezone.utc),
    }
