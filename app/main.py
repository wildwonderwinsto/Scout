"""
YouTube Trend Scout — FastAPI application entry point.

Initializes logging, creates database tables, and mounts all routers.
Run with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.utils.logger import setup_logging
from app.database import Base, engine
from app.routers import health, channels, videos, scan
from app.services.snapshot_service import update_tracked_snapshots

# Ensure all models are imported so Base.metadata knows about them
from app.models import Channel, Video, VideoSnapshot  # noqa: F401


# ── Logging ───────────────────────────────────────────────────────────────
setup_logging()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────
scheduler = BackgroundScheduler()

def start_scheduler():
    scheduler.add_job(
        update_tracked_snapshots,
        trigger=IntervalTrigger(minutes=60),
        id='snapshot_updater',
        replace_existing=True
    )
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and start background jobs."""
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    stop_scheduler()


# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="YouTube Trend Scout",
    description=(
        "Discover trending YouTube videos and channels using data-driven "
        "ranking: Breakout Score, VPH velocity, and outlier detection."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the future frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(channels.router)
app.include_router(videos.router)
app.include_router(scan.router)


@app.get("/")
def root():
    """Root endpoint — directs users to the interactive API docs."""
    return {
        "message": "YouTube Trend Scout API",
        "docs": "/docs",
        "version": "0.1.0",
    }

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon():
    return Response(status_code=204)
