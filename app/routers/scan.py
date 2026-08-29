"""
Scan endpoints — the primary interface for trend discovery.

POST /scan/general   — General Scan: find anything blowing up from small channels
POST /scan/keyword   — Keyword Scan: find proven topics in a specific niche
POST /scan/channel   — Channel Scan: analyze a specific channel's videos

All three return a ScanResponse with ranked videos, computed metrics,
and scan metadata.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.scan import ScanFilters, ScanResponse
from app.services.trend_scanner import general_scan, keyword_scan, channel_scan

router = APIRouter(prefix="/scan", tags=["scanning"])


@router.post("/general", response_model=ScanResponse)
def run_general_scan(
    filters: ScanFilters,
    db: Session = Depends(get_db),
):
    """
    General Scan — "Find me ANYTHING blowing up from small English channels."

    Discovers channels from recent popular videos, filters by subscriber
    band / language / country, fetches their recent videos, and ranks
    by Breakout Score with VPH tiebreak.

    Send an empty body `{}` to use all defaults (5K-100K subs, English,
    last 7 days, all formats, 2x minimum breakout).
    """
    result = general_scan(db, filters)
    return ScanResponse(**result)


@router.post("/keyword", response_model=ScanResponse)
def run_keyword_scan(
    filters: ScanFilters,
    db: Session = Depends(get_db),
):
    """
    Keyword Scan — "Find me a proven topic for my niche."

    Searches YouTube for videos matching the query, then filters
    by channel size and computes ranking metrics.

    Requires `query` in the request body (e.g. "funny clips",
    "try not to laugh", "meme compilation").
    """
    result = keyword_scan(db, filters)
    return ScanResponse(**result)


@router.post("/channel/{channel_id:path}", response_model=ScanResponse)
def run_channel_scan(
    channel_id: str,
    filters: ScanFilters,
    db: Session = Depends(get_db),
):
    """
    Channel Scan — "Analyze THIS specific channel."

    Fetches a channel's recent videos, scores each one against the
    channel's own average, and returns ranked results.

    The channel_id is the YouTube channel ID, a handle (@name), or a full URL.
    Subscriber/language filters are skipped for direct channel scans.
    """
    # Remove leading slash if path param captured it
    channel_id = channel_id.strip("/")
    result = channel_scan(db, channel_id, filters)
    return ScanResponse(**result)
