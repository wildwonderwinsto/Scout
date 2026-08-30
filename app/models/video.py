"""
SQLAlchemy model for YouTube videos.

Stores video metadata, statistics, and derived fields (is_short, duration_seconds)
needed for the ranking engines.  Each video belongs to a Channel and has zero or
more VideoSnapshots for historical VPH tracking.
"""

from typing import Optional
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    # ── Identity ──────────────────────────────────────────────────────────
    id = Column(String, primary_key=True)                          # YouTube video ID
    channel_id = Column(String, ForeignKey("channels.id"), nullable=False, index=True)

    # ── Metadata ──────────────────────────────────────────────────────────
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)                             # JSON-encoded list or comma-separated
    published_at = Column(DateTime, nullable=False, index=True)    # Indexed for recency queries
    duration = Column(String, nullable=True)                       # ISO 8601 (e.g. "PT1M30S")
    duration_seconds = Column(Integer, nullable=True)              # Parsed numeric seconds
    category_id = Column(String, nullable=True)                    # YouTube category ID
    made_for_kids = Column(Boolean, nullable=True)

    # ── Format ────────────────────────────────────────────────────────────
    is_short = Column(Boolean, nullable=True, default=False)       # True if <= 60s (Shorts)

    # ── Statistics ────────────────────────────────────────────────────────
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(BigInteger, nullable=True)
    comment_count = Column(BigInteger, nullable=True)

    # ── Assets ────────────────────────────────────────────────────────────
    thumbnail_url = Column(String, nullable=True)                  # Highest-res thumbnail URL

    # ── Housekeeping ──────────────────────────────────────────────────────
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────────────
    channel = relationship("Channel", back_populates="videos")
    snapshots = relationship("VideoSnapshot", back_populates="video", lazy="dynamic",
                             order_by="VideoSnapshot.captured_at.desc()")

    def __repr__(self) -> str:
        return (
            f"<Video id={self.id} title={self.title!r} "
            f"views={self.view_count} short={self.is_short}>"
        )

    @property
    def engagement_rate(self) -> Optional[float]:
        """
        Engagement rate = (likes + comments) / views.
        Returns None if data is missing.  Used as a quality gate to filter
        out bought/viewbait traffic.
        """
        if (
            self.view_count
            and self.view_count > 0
            and self.like_count is not None
            and self.comment_count is not None
        ):
            return (self.like_count + self.comment_count) / self.view_count
        return None
