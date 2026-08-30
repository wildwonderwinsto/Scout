"""
SQLAlchemy model for YouTube channels.

Stores channel identity, statistics, and metadata fetched from the YouTube
Data API v3.  The `view_count` / `video_count` / `subscriber_count` triple
is the basis for computing channel-level averages used in Breakout Score
calculations later.
"""

from typing import Optional
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    # ── Identity ──────────────────────────────────────────────────────────
    id = Column(String, primary_key=True)                 # YouTube channel ID (e.g. UCxxx)
    title = Column(String, nullable=False)                # Display name
    handle = Column(String, nullable=True)                # @handle / customUrl
    description = Column(Text, nullable=True)             # Channel about text

    # ── Locale ────────────────────────────────────────────────────────────
    country = Column(String(5), nullable=True)            # ISO 3166-1 alpha-2 (e.g. "US")
    language = Column(String(10), nullable=True)          # Primary language code (e.g. "en")

    # ── Dates ─────────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=True)          # Channel creation date (snippet.publishedAt)

    # ── Statistics ────────────────────────────────────────────────────────
    subscriber_count = Column(BigInteger, nullable=True)     # Public sub count (may be hidden)
    video_count = Column(BigInteger, nullable=True)          # Total public videos
    view_count = Column(BigInteger, nullable=True)           # Lifetime total views

    # ── Classification ────────────────────────────────────────────────────
    topics = Column(Text, nullable=True)                  # Comma-separated topicCategory URLs
    category = Column(String, nullable=True)              # YouTube category label (if available)

    # ── Branding ──────────────────────────────────────────────────────────
    banner_url = Column(String, nullable=True)            # Channel banner image URL
    profile_image_url = Column(String, nullable=True)     # Channel avatar URL

    # ── Flags ─────────────────────────────────────────────────────────────
    hidden_subscriber_count = Column(Boolean, nullable=True)
    made_for_kids = Column(Boolean, nullable=True)

    # ── Housekeeping ──────────────────────────────────────────────────────
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────
    videos = relationship("Video", back_populates="channel", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Channel id={self.id} title={self.title!r} subs={self.subscriber_count}>"

    @property
    def avg_views_per_video(self) -> Optional[float]:
        """Lifetime average views per video (rough baseline for breakout calc)."""
        if self.view_count and self.video_count and self.video_count > 0:
            return self.view_count / self.video_count
        return None
