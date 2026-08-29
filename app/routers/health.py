"""
Health check endpoint.
"""

from fastapi import APIRouter
from app.schemas.common import StatusResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=StatusResponse)
def health_check():
    """Returns service status. Use for uptime monitoring and readiness probes."""
    return StatusResponse(status="ok", service="youtube-trend-scout")
