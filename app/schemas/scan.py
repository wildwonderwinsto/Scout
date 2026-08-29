"""
Pydantic schemas for the scanning and ranking system.

ScanFilters: Input model for both General Scan and Keyword Scan.
RankedVideo: Output model for each ranked result row.
ScanResponse: Wrapper for the full scan response with metadata.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ScanFilters(BaseModel):
    """
    Filter parameters for trend scanning.

    These map directly to the filtering logic described in the ranking doc:
    - Subscriber band: subscriber_min / subscriber_max
    - Language + Country: languages / countries (separate filters for RPM)
    - Recency: published_days_ago (converted to published_after internally)
    - Format: video_format ("short" / "long" / "all")
    - Quality gates: min_vph, min_breakout, min_engagement_rate
    - Sorting: sort_by controls final ranking order
    """

    # ── Subscriber Band ───────────────────────────────────────────────────
    subscriber_min: int = Field(
        default=1000, ge=0,
        description="Minimum subscriber count (default 1K, sweet spot starts at 3K)"
    )
    subscriber_max: int = Field(
        default=100000, ge=0,
        description="Maximum subscriber count (default 100K)"
    )
    channel_video_max: Optional[int] = Field(
        default=None, ge=1,
        description="Maximum total videos published by the channel (for finding early channels)"
    )

    # ── Language & Country ────────────────────────────────────────────────
    languages: List[str] = Field(
        default=["en"],
        description="Language codes to filter by (e.g. ['en']). Filters channel language."
    )
    countries: Optional[List[str]] = Field(
        default=["US", "GB", "CA", "AU", "NZ", "IE"],
        description="Country codes for high-RPM markets (e.g. ['US','GB','CA','AU'])"
    )

    # ── Recency ───────────────────────────────────────────────────────────
    published_days_ago: int = Field(
        default=7, ge=1, le=90,
        description="Only include videos published within this many days"
    )

    # ── Format ────────────────────────────────────────────────────────────
    video_format: str = Field(
        default="all",
        description="'short' (<=60s), 'long' (>60s), or 'all'"
    )

    # ── Quality Gates ─────────────────────────────────────────────────────
    min_vph: float = Field(
        default=0.0, ge=0.0,
        description="Minimum Views Per Hour to include (0 = no filter)"
    )
    min_breakout: float = Field(
        default=2.0, ge=0.0,
        description="Minimum Breakout Score (video views / channel avg). 2x = default gate."
    )
    min_engagement_rate: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Minimum engagement rate (likes+comments)/views. 0.02 = 2% fake-view gate."
    )
    engagement_ratio_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Flag videos with engagement below this ratio of the channel average"
    )
    min_recent_videos: int = Field(
        default=0, ge=0,
        description="Channel must have at least this many videos in the last 7 days to be considered active"
    )
    min_views: Optional[int] = Field(
        default=None, ge=0,
        description="Minimum view count for a video to be ranked"
    )
    max_views: Optional[int] = Field(
        default=None, ge=0,
        description="Maximum view count for a video to be ranked"
    )

    # ── Results ───────────────────────────────────────────────────────────
    max_results: int = Field(
        default=50, ge=1, le=200,
        description="Maximum number of ranked results to return"
    )

    # ── Query (for keyword scan) ──────────────────────────────────────────
    query: Optional[str] = Field(
        default=None,
        description="Search query for keyword scan (e.g. 'funny clips', 'try not to laugh')"
    )

    # ── Sorting ───────────────────────────────────────────────────────────
    sort_by: str = Field(
        default="breakout",
        description="Primary sort: 'breakout' (default), 'vph', 'views', 'date'"
    )


class RankedVideo(BaseModel):
    """
    A single ranked result row.

    Contains the video metadata, its channel context, and all computed
    ranking metrics so the frontend can display the full data table.
    """
    model_config = ConfigDict(from_attributes=True)

    # ── Video Identity ────────────────────────────────────────────────────
    video_id: str
    title: str
    thumbnail_url: Optional[str] = None
    published_at: Optional[datetime] = None
    published_days_ago: Optional[int] = None
    is_short: bool = False
    duration_seconds: Optional[int] = None

    # ── Video Stats ───────────────────────────────────────────────────────
    view_count: int = 0
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    # ── Channel Context ───────────────────────────────────────────────────
    channel_id: str
    channel_title: str
    subscriber_count: Optional[int] = None
    channel_avg_views: float = 0.0
    channel_median_views: float = 0.0
    channel_country: Optional[str] = None
    channel_language: Optional[str] = None

    # ── Computed Ranking Metrics ──────────────────────────────────────────
    breakout_score: float = 0.0
    vph: float = 0.0
    engagement_rate: float = 0.0
    engagement_flag: bool = False
    channel_recent_videos_7d: int = 0

    # ── Source ────────────────────────────────────────────────────────────
    vph_source: str = "average"  # "snapshot" if computed from real snapshot diffs, "average" if lifetime avg


class ScanResponse(BaseModel):
    """Full response from a scan endpoint."""
    scan_type: str  # "general" or "keyword"
    query: Optional[str] = None
    filters_applied: ScanFilters
    total_channels_scanned: int = 0
    total_videos_evaluated: int = 0
    results: List[RankedVideo]
    sort_by: str = "breakout"
    scanned_at: datetime


class ChannelAnalysis(BaseModel):
    """Comprehensive analysis report for a single channel."""
    channel: dict
    average_views: float
    total_videos_analyzed: int
    recent_videos: List[dict]
    top_outliers: List[dict]
    outlier_count: int
    health: dict
    engagement_analysis: dict
    analyzed_at: datetime
