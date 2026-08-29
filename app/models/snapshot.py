"""
SQLAlchemy model for video view-count snapshots.

Each snapshot records a video's statistics at a point in time.  By comparing
two snapshots we can compute Views Per Hour (VPH) — the core velocity metric
for the Trending engine.

Example VPH calculation:
    vph = (snapshot_new.view_count - snapshot_old.view_count) /
          hours_between(snapshot_old.captured_at, snapshot_new.captured_at)
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class VideoSnapshot(Base):
    __tablename__ = "video_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False, index=True)
    view_count = Column(Integer, nullable=False)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    captured_at = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    # ── Relationships ─────────────────────────────────────────────────────
    video = relationship("Video", back_populates="snapshots")

    def __repr__(self) -> str:
        return (
            f"<VideoSnapshot video_id={self.video_id} "
            f"views={self.view_count} at={self.captured_at}>"
        )
