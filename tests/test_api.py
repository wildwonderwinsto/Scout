"""
Smoke tests for the YouTube Trend Scout API.

These tests verify:
1. Health endpoint returns 200 with expected payload
2. Root endpoint returns service info
3. Calculations module produces correct results
4. Duration parser handles edge cases
5. Short detection logic works

Tests that hit the real YouTube API are marked with a comment —
they require a valid YOUTUBE_API_KEY in .env to pass.
"""

import pytest
from fastapi.testclient import TestClient

# We need to set a dummy API key before importing the app,
# otherwise pydantic-settings will fail validation on import.
import os
os.environ.setdefault("YOUTUBE_API_KEY", "test_dummy_key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_youtube_trend_scout.db")

from app.main import app
from app.services.calculations import (
    calculate_breakout_score,
    calculate_engagement_rate,
    calculate_vph,
)
from app.services.data_fetcher import parse_duration_to_seconds, detect_is_short

client = TestClient(app)


# ── Health & Root ─────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "youtube-trend-scout"

    def test_root_returns_info(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "YouTube Trend Scout" in data["message"]
        assert data["docs"] == "/docs"


# ── Duration Parsing ─────────────────────────────────────────────────────

class TestDurationParser:
    def test_full_duration(self):
        assert parse_duration_to_seconds("PT1H2M10S") == 3730

    def test_minutes_and_seconds(self):
        assert parse_duration_to_seconds("PT5M30S") == 330

    def test_seconds_only(self):
        assert parse_duration_to_seconds("PT45S") == 45

    def test_hours_only(self):
        assert parse_duration_to_seconds("PT2H") == 7200

    def test_zero_duration(self):
        assert parse_duration_to_seconds("PT0S") == 0

    def test_invalid_string_returns_none(self):
        assert parse_duration_to_seconds("not_a_duration") is None

    def test_empty_string_returns_none(self):
        assert parse_duration_to_seconds("") is None


# ── Short Detection ───────────────────────────────────────────────────────

class TestShortDetection:
    def test_60_seconds_is_short(self):
        assert detect_is_short(60) is True

    def test_59_seconds_is_short(self):
        assert detect_is_short(59) is True

    def test_61_seconds_is_not_short(self):
        assert detect_is_short(61) is False

    def test_none_is_not_short(self):
        assert detect_is_short(None) is False

    def test_zero_is_short(self):
        assert detect_is_short(0) is True


# ── Breakout Score ────────────────────────────────────────────────────────

class TestBreakoutScore:
    def test_10x_outlier(self):
        """A 100K video on a 10K-average channel = 10x breakout."""
        score = calculate_breakout_score(100_000, 10_000)
        assert score == 10.0

    def test_average_performance(self):
        score = calculate_breakout_score(10_000, 10_000)
        assert score == 1.0

    def test_underperformance(self):
        score = calculate_breakout_score(5_000, 10_000)
        assert score == 0.5

    def test_zero_channel_avg_returns_none(self):
        assert calculate_breakout_score(50_000, 0) is None

    def test_negative_channel_avg_returns_none(self):
        assert calculate_breakout_score(50_000, -100) is None


# ── Engagement Rate ───────────────────────────────────────────────────────

class TestEngagementRate:
    def test_normal_engagement(self):
        rate = calculate_engagement_rate(likes=500, comments=50, views=10_000)
        assert rate == 0.055

    def test_zero_views_returns_none(self):
        assert calculate_engagement_rate(likes=100, comments=10, views=0) is None

    def test_none_views_returns_none(self):
        assert calculate_engagement_rate(likes=100, comments=10, views=None) is None

    def test_none_likes_treated_as_zero(self):
        rate = calculate_engagement_rate(likes=None, comments=10, views=1000)
        assert rate == 0.01


# ── VPH ───────────────────────────────────────────────────────────────────

class TestVPH:
    def test_vph_calculation(self):
        from app.models.snapshot import VideoSnapshot
        from datetime import datetime, timedelta

        old = VideoSnapshot(
            video_id="test",
            view_count=10_000,
            captured_at=datetime(2026, 1, 1, 12, 0, 0),
        )
        new = VideoSnapshot(
            video_id="test",
            view_count=14_000,
            captured_at=datetime(2026, 1, 1, 14, 0, 0),  # 2 hours later
        )
        vph = calculate_vph(old, new)
        assert vph == 2000.0  # 4000 views / 2 hours

    def test_vph_none_on_same_timestamp(self):
        from app.models.snapshot import VideoSnapshot
        from datetime import datetime

        ts = datetime(2026, 1, 1, 12, 0, 0)
        old = VideoSnapshot(video_id="test", view_count=100, captured_at=ts)
        new = VideoSnapshot(video_id="test", view_count=200, captured_at=ts)
        assert calculate_vph(old, new) is None

    def test_vph_none_on_missing_snapshot(self):
        assert calculate_vph(None, None) is None


# ── API Endpoint Tests (require real API key) ─────────────────────────────
# Uncomment these when you have a valid YOUTUBE_API_KEY in .env

# class TestRealAPI:
#     def test_get_mrbeast_channel(self):
#         """Fetch MrBeast's channel — requires real API key."""
#         response = client.get("/channels/UCX6OQ3DkcsbYNE6H8uQQuVA")
#         assert response.status_code == 200
#         data = response.json()
#         assert data["id"] == "UCX6OQ3DkcsbYNE6H8uQQuVA"
#         assert data["subscriber_count"] > 0
#
#     def test_get_nonexistent_channel(self):
#         response = client.get("/channels/UC_TOTALLY_FAKE_ID_12345")
#         assert response.status_code == 404


# ── Cleanup ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def cleanup_test_db():
    """Remove the test database after the test session."""
    yield
    import os
    try:
        os.remove("test_youtube_trend_scout.db")
    except FileNotFoundError:
        pass
