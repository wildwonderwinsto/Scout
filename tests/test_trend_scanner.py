"""
Tests for the trend scanning and ranking engine (Step 2).

Covers:
- Metric computation: breakout score, engagement rate, average VPH
- Channel filter logic
- Video filter logic
- Sorting / ranking
- Scan schemas validation
- API endpoint smoke tests
"""

import pytest
from datetime import datetime, timedelta, timezone

import os
os.environ.setdefault("YOUTUBE_API_KEY", "test_dummy_key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_youtube_trend_scout.db")

from app.services.trend_scanner import (
    compute_channel_avg_views,
    compute_breakout_score,
    compute_engagement_rate,
    compute_average_vph,
    compute_published_days_ago,
    _channel_matches_filters,
    _video_matches_filters,
    _sort_results,
)
from app.schemas.scan import ScanFilters, RankedVideo, ScanResponse
from app.models.channel import Channel
from app.models.video import Video


# ══════════════════════════════════════════════════════════════════════════
#  METRIC COMPUTATION TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestComputeChannelAvgViews:
    def test_normal(self):
        ch = Channel(id="test", title="Test", view_count=100000, video_count=10)
        assert compute_channel_avg_views(ch) == 10000.0

    def test_zero_videos(self):
        ch = Channel(id="test", title="Test", view_count=100000, video_count=0)
        assert compute_channel_avg_views(ch) == 0.0

    def test_none_views(self):
        ch = Channel(id="test", title="Test", view_count=None, video_count=10)
        assert compute_channel_avg_views(ch) == 0.0

    def test_none_count(self):
        ch = Channel(id="test", title="Test", view_count=100000, video_count=None)
        assert compute_channel_avg_views(ch) == 0.0


class TestComputeBreakoutScore:
    def test_10x_outlier(self):
        assert compute_breakout_score(100000, 10000) == 10.0

    def test_average_performance(self):
        assert compute_breakout_score(10000, 10000) == 1.0

    def test_underperformance(self):
        assert compute_breakout_score(5000, 10000) == 0.5

    def test_zero_avg_returns_zero(self):
        assert compute_breakout_score(50000, 0) == 0.0

    def test_high_breakout(self):
        """A 40K video on a 3K-average channel = 13.33x"""
        score = compute_breakout_score(40000, 3000)
        assert score == 13.33


class TestComputeEngagementRate:
    def test_normal(self):
        v = Video(id="v1", channel_id="c1", title="T", published_at=datetime.now(),
                  view_count=10000, like_count=500, comment_count=50)
        rate = compute_engagement_rate(v)
        assert rate == 0.055

    def test_zero_views(self):
        v = Video(id="v1", channel_id="c1", title="T", published_at=datetime.now(),
                  view_count=0, like_count=10, comment_count=5)
        assert compute_engagement_rate(v) == 0.0

    def test_none_likes(self):
        v = Video(id="v1", channel_id="c1", title="T", published_at=datetime.now(),
                  view_count=1000, like_count=None, comment_count=10)
        rate = compute_engagement_rate(v)
        assert rate == 0.01

    def test_none_views(self):
        v = Video(id="v1", channel_id="c1", title="T", published_at=datetime.now(),
                  view_count=None, like_count=10, comment_count=5)
        assert compute_engagement_rate(v) == 0.0


class TestComputeAverageVPH:
    def test_recent_video(self):
        """A video published 10 hours ago with 10000 views = 1000 vph"""
        pub = datetime.now(timezone.utc) - timedelta(hours=10)
        v = Video(id="v1", channel_id="c1", title="T",
                  published_at=pub, view_count=10000)
        vph = compute_average_vph(v)
        assert 990.0 <= vph <= 1010.0  # Allow small time drift

    def test_old_video(self):
        """A video published 30 days ago with 100000 views = ~139 vph"""
        pub = datetime.now(timezone.utc) - timedelta(days=30)
        v = Video(id="v1", channel_id="c1", title="T",
                  published_at=pub, view_count=100000)
        vph = compute_average_vph(v)
        assert 130.0 <= vph <= 145.0

    def test_no_published_at(self):
        v = Video(id="v1", channel_id="c1", title="T",
                  published_at=None, view_count=10000)
        assert compute_average_vph(v) == 0.0

    def test_no_views(self):
        v = Video(id="v1", channel_id="c1", title="T",
                  published_at=datetime.now(timezone.utc), view_count=None)
        assert compute_average_vph(v) == 0.0


class TestComputePublishedDaysAgo:
    def test_today(self):
        assert compute_published_days_ago(datetime.now(timezone.utc)) == 0

    def test_three_days(self):
        pub = datetime.now(timezone.utc) - timedelta(days=3)
        assert compute_published_days_ago(pub) == 3

    def test_none(self):
        assert compute_published_days_ago(None) is None


# ══════════════════════════════════════════════════════════════════════════
#  FILTER TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestChannelMatchesFilters:
    def _make_channel(self, subs=10000, lang="en", country="US", hidden=False):
        return Channel(
            id="test", title="Test",
            subscriber_count=subs,
            language=lang,
            country=country,
            hidden_subscriber_count=hidden,
            view_count=100000,
            video_count=10,
        )

    def test_passes_default_filters(self):
        ch = self._make_channel(subs=10000)
        filters = ScanFilters()
        assert _channel_matches_filters(ch, filters) is True

    def test_too_few_subs(self):
        ch = self._make_channel(subs=500)
        filters = ScanFilters(subscriber_min=1000)
        assert _channel_matches_filters(ch, filters) is False

    def test_too_many_subs(self):
        ch = self._make_channel(subs=200000)
        filters = ScanFilters(subscriber_max=100000)
        assert _channel_matches_filters(ch, filters) is False

    def test_hidden_subs_rejected(self):
        ch = self._make_channel(subs=10000, hidden=True)
        filters = ScanFilters()
        assert _channel_matches_filters(ch, filters) is False

    def test_wrong_language_rejected(self):
        ch = self._make_channel(lang="es")
        filters = ScanFilters(languages=["en"])
        assert _channel_matches_filters(ch, filters) is False

    def test_no_language_passes(self):
        """Channels with no language set pass (can't verify)."""
        ch = self._make_channel(lang=None)
        filters = ScanFilters(languages=["en"])
        assert _channel_matches_filters(ch, filters) is True

    def test_country_filter(self):
        ch = self._make_channel(country="IN")
        filters = ScanFilters(countries=["US", "GB", "CA", "AU"])
        assert _channel_matches_filters(ch, filters) is False

    def test_country_passes(self):
        ch = self._make_channel(country="US")
        filters = ScanFilters(countries=["US", "GB", "CA", "AU"])
        assert _channel_matches_filters(ch, filters) is True

    def test_no_country_filter(self):
        """If no countries specified, all pass."""
        ch = self._make_channel(country="IN")
        filters = ScanFilters(countries=None)
        assert _channel_matches_filters(ch, filters) is True

    def test_none_subs_rejected(self):
        ch = self._make_channel()
        ch.subscriber_count = None
        filters = ScanFilters()
        assert _channel_matches_filters(ch, filters) is False


class TestVideoMatchesFilters:
    def _make_video(self, views=10000, published_days_ago=3, is_short=True):
        pub = datetime.now(timezone.utc) - timedelta(days=published_days_ago)
        return Video(
            id="v1", channel_id="c1", title="Test",
            published_at=pub,
            view_count=views,
            is_short=is_short,
        )

    def test_passes_default(self):
        v = self._make_video()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        filters = ScanFilters()
        assert _video_matches_filters(v, filters, cutoff) is True

    def test_zero_views_rejected(self):
        v = self._make_video(views=0)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        filters = ScanFilters()
        assert _video_matches_filters(v, filters, cutoff) is False

    def test_too_old_rejected(self):
        v = self._make_video(published_days_ago=30)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        filters = ScanFilters()
        assert _video_matches_filters(v, filters, cutoff) is False

    def test_short_filter_rejects_long(self):
        v = self._make_video(is_short=False)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        filters = ScanFilters(video_format="short")
        assert _video_matches_filters(v, filters, cutoff) is False

    def test_long_filter_rejects_short(self):
        v = self._make_video(is_short=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        filters = ScanFilters(video_format="long")
        assert _video_matches_filters(v, filters, cutoff) is False

    def test_all_format_passes_both(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        filters = ScanFilters(video_format="all")
        v_short = self._make_video(is_short=True)
        v_long = self._make_video(is_short=False)
        assert _video_matches_filters(v_short, filters, cutoff) is True
        assert _video_matches_filters(v_long, filters, cutoff) is True


# ══════════════════════════════════════════════════════════════════════════
#  SORTING TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestSortResults:
    def _make_ranked(self, breakout=1.0, vph=100.0, views=1000, days_ago=1):
        pub = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return RankedVideo(
            video_id="v1", title="T", channel_id="c1", channel_title="C",
            breakout_score=breakout, vph=vph, view_count=views,
            published_at=pub, engagement_rate=0.05,
        )

    def test_breakout_sort(self):
        r1 = self._make_ranked(breakout=10.0, vph=100)
        r2 = self._make_ranked(breakout=5.0, vph=200)
        r3 = self._make_ranked(breakout=20.0, vph=50)
        results = _sort_results([r1, r2, r3], "breakout")
        assert results[0].breakout_score == 20.0
        assert results[1].breakout_score == 10.0
        assert results[2].breakout_score == 5.0

    def test_vph_sort(self):
        r1 = self._make_ranked(vph=5000)
        r2 = self._make_ranked(vph=100)
        r3 = self._make_ranked(vph=2000)
        results = _sort_results([r1, r2, r3], "vph")
        assert results[0].vph == 5000
        assert results[1].vph == 2000
        assert results[2].vph == 100

    def test_views_sort(self):
        r1 = self._make_ranked(views=50000)
        r2 = self._make_ranked(views=200000)
        r3 = self._make_ranked(views=10000)
        results = _sort_results([r1, r2, r3], "views")
        assert results[0].view_count == 200000

    def test_breakout_tiebreak_by_vph(self):
        """Same breakout → higher VPH wins."""
        r1 = self._make_ranked(breakout=5.0, vph=100)
        r2 = self._make_ranked(breakout=5.0, vph=500)
        results = _sort_results([r1, r2], "breakout")
        assert results[0].vph == 500


# ══════════════════════════════════════════════════════════════════════════
#  SCHEMA VALIDATION TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestScanFiltersSchema:
    def test_defaults(self):
        f = ScanFilters()
        assert f.subscriber_min == 1000
        assert f.subscriber_max == 100000
        assert f.languages == ["en"]
        assert f.published_days_ago == 7
        assert f.video_format == "all"
        assert f.min_breakout == 2.0
        assert f.sort_by == "breakout"

    def test_custom_values(self):
        f = ScanFilters(
            subscriber_min=5000,
            subscriber_max=50000,
            languages=["en", "es"],
            countries=["US", "GB"],
            published_days_ago=3,
            video_format="short",
            min_vph=1000,
            min_breakout=3.0,
            min_engagement_rate=0.02,
            query="funny clips",
            sort_by="vph",
        )
        assert f.subscriber_min == 5000
        assert f.query == "funny clips"
        assert f.min_engagement_rate == 0.02


class TestRankedVideoSchema:
    def test_creation(self):
        rv = RankedVideo(
            video_id="abc123",
            title="Test Video",
            channel_id="ch123",
            channel_title="Test Channel",
            view_count=50000,
            breakout_score=8.5,
            vph=2500.0,
            engagement_rate=0.045,
        )
        assert rv.video_id == "abc123"
        assert rv.breakout_score == 8.5


# ══════════════════════════════════════════════════════════════════════════
#  API ENDPOINT SMOKE TESTS
# ══════════════════════════════════════════════════════════════════════════

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestScanEndpoints:
    def test_scan_endpoints_exist(self):
        """Verify the scan endpoints are registered (they'll fail with dummy API key but return proper errors)."""
        # Check that the routes exist by looking at the OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert "/scan/general" in paths
        assert "/scan/keyword" in paths


# ── Cleanup ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def cleanup_test_db():
    yield
    try:
        os.remove("test_youtube_trend_scout.db")
    except FileNotFoundError:
        pass
