"""
Wrapper around the YouTube Data API v3 using google-api-python-client.

All API calls go through this class so we have a single place to handle
rate-limit retries, batching (max 50 IDs per request), and error logging.
"""

from typing import Optional, List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────
_CHANNEL_PARTS = "snippet,statistics,contentDetails,topicDetails,brandingSettings"
_VIDEO_PARTS = "snippet,statistics,contentDetails,topicDetails,status"
_MAX_BATCH = 50  # YouTube API max IDs per request


class YouTubeClient:
    """
    Thin wrapper that builds a YouTube service object once and exposes
    methods matching the data-fetching patterns we need:

    • Single / batch channel details
    • Single / batch video details
    • Channel uploads (via playlistItems)
    • Search for channels or videos
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.youtube_api_key
        self.service = build("youtube", "v3", developerKey=self.api_key)

    # ── Channel Details ───────────────────────────────────────────────────

    def get_channel_details(self, channel_id: str) -> Optional[dict]:
        """
        Fetch full channel data (snippet, statistics, contentDetails,
        topicDetails, brandingSettings) for a single channel ID.

        Returns the first item dict, or None if the channel doesn't exist.
        """
        try:
            request = self.service.channels().list(
                part=_CHANNEL_PARTS,
                id=channel_id,
            )
            response = request.execute()
            items = response.get("items", [])
            return items[0] if items else None
        except HttpError as e:
            logger.error(f"YouTube API error fetching channel {channel_id}: {e}")
            raise

    def get_channels_details_batch(self, channel_ids: List[str]) -> List[dict]:
        """
        Fetch details for multiple channels.  Automatically chunks into
        groups of 50 to stay within API limits.
        """
        results: List[dict] = []
        for i in range(0, len(channel_ids), _MAX_BATCH):
            chunk = channel_ids[i : i + _MAX_BATCH]
            results.extend(self._get_channels_chunk(chunk))
        return results

    def _get_channels_chunk(self, channel_ids: List[str]) -> List[dict]:
        try:
            request = self.service.channels().list(
                part=_CHANNEL_PARTS,
                id=",".join(channel_ids),
            )
            response = request.execute()
            return response.get("items", [])
        except HttpError as e:
            logger.error(f"YouTube API error batch-fetching channels: {e}")
            raise

    # ── Video Details ─────────────────────────────────────────────────────

    def get_video_details(self, video_id: str) -> Optional[dict]:
        """
        Fetch full video data for a single video ID.
        Returns the first item dict, or None if the video doesn't exist.
        """
        try:
            request = self.service.videos().list(
                part=_VIDEO_PARTS,
                id=video_id,
            )
            response = request.execute()
            items = response.get("items", [])
            return items[0] if items else None
        except HttpError as e:
            logger.error(f"YouTube API error fetching video {video_id}: {e}")
            raise

    def get_videos_details_batch(self, video_ids: List[str]) -> List[dict]:
        """
        Fetch details for multiple videos.  Automatically chunks into
        groups of 50.
        """
        results: List[dict] = []
        for i in range(0, len(video_ids), _MAX_BATCH):
            chunk = video_ids[i : i + _MAX_BATCH]
            results.extend(self._get_videos_chunk(chunk))
        return results

    def _get_videos_chunk(self, video_ids: List[str]) -> List[dict]:
        try:
            request = self.service.videos().list(
                part=_VIDEO_PARTS,
                id=",".join(video_ids),
            )
            response = request.execute()
            return response.get("items", [])
        except HttpError as e:
            logger.error(f"YouTube API error batch-fetching videos: {e}")
            raise

    # ── Channel Uploads ───────────────────────────────────────────────────

    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[dict]:
        """
        Fetch the most recent videos from a channel's uploads playlist.

        Uses playlistItems.list (costs 1 quota unit per page) rather than
        search.list (costs 100 units) — much more quota-efficient.

        Returns a list of playlistItem dicts.  Each item's
        `contentDetails.videoId` gives the video ID for further lookup.
        """
        # Step 1: Resolve the uploads playlist ID from the channel
        channel_data = self.get_channel_details(channel_id)
        if not channel_data:
            logger.warning(f"Channel {channel_id} not found; can't fetch uploads.")
            return []

        uploads_playlist_id = (
            channel_data
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_playlist_id:
            logger.warning(f"No uploads playlist for channel {channel_id}.")
            return []

        # Step 2: Page through the uploads playlist
        video_items: List[dict] = []
        next_page_token: Optional[str] = None

        while len(video_items) < max_results:
            try:
                request = self.service.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=min(max_results - len(video_items), _MAX_BATCH),
                    pageToken=next_page_token,
                )
                response = request.execute()
                video_items.extend(response.get("items", []))
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
            except HttpError as e:
                logger.error(f"YouTube API error listing uploads for {channel_id}: {e}")
                break

        return video_items[:max_results]

    # ── Search ────────────────────────────────────────────────────────────

    def search_channels(
        self,
        query: str,
        max_results: int = 50,
        **kwargs,
    ) -> List[dict]:
        """
        Search YouTube for channels matching `query`.

        Costs 100 quota units per call — use sparingly.
        Extra kwargs are forwarded to search().list (e.g. regionCode,
        relevanceLanguage, publishedAfter).
        """
        try:
            request = self.service.search().list(
                part="snippet",
                q=query,
                type="channel",
                maxResults=min(max_results, _MAX_BATCH),
                **kwargs,
            )
            response = request.execute()
            return response.get("items", [])
        except HttpError as e:
            logger.error(f"YouTube API error searching channels for '{query}': {e}")
            raise

    def search_videos(
        self,
        query: str,
        max_results: int = 50,
        **kwargs,
    ) -> List[dict]:
        """
        Search YouTube for videos matching `query`.

        Costs 100 quota units per call.  Extra kwargs are forwarded to
        search().list (e.g. order, videoDuration, publishedAfter,
        regionCode, relevanceLanguage).
        """
        try:
            request = self.service.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=min(max_results, _MAX_BATCH),
                **kwargs,
            )
            response = request.execute()
            return response.get("items", [])
        except HttpError as e:
            logger.error(f"YouTube API error searching videos for '{query}': {e}")
            raise

    def search_videos_advanced(
        self,
        query: Optional[str] = None,
        max_results: int = 50,
        order: str = "viewCount",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        video_duration: Optional[str] = None,
        region_code: Optional[str] = None,
        relevance_language: Optional[str] = None,
        page_token: Optional[str] = None,
    ) -> List[dict]:
        """
        Advanced video search with granular filter control.

        This is the primary search method for trend discovery — it lets us
        find recent high-view videos that we then cross-reference against
        channel size to compute breakout scores.

        Args:
            query: Search term (optional for general scan).
            max_results: Max results per page (capped at 50 by API).
            order: Sort order — "viewCount", "date", "relevance", "rating".
            published_after: RFC 3339 datetime string (e.g. "2026-08-22T00:00:00Z").
            published_before: RFC 3339 datetime string.
            video_duration: "short" (<4min), "medium" (4-20min), "long" (>20min), or None for any.
            region_code: ISO 3166-1 alpha-2 country code (e.g. "US").
            relevance_language: ISO 639-1 language code (e.g. "en").
            page_token: Pagination token for next page of results.

        Returns:
            List of search result dicts (snippet only).  Each item has
            item["id"]["videoId"] for further lookup.

        Costs 100 quota units per call.
        """
        params = {
            "part": "snippet",
            "type": "video",
            "maxResults": min(max_results, _MAX_BATCH),
            "order": order,
            "safeSearch": "none",
        }
        if query:
            params["q"] = query
        if published_after:
            params["publishedAfter"] = published_after
        if published_before:
            params["publishedBefore"] = published_before
        if video_duration and video_duration != "any":
            params["videoDuration"] = video_duration
        if region_code:
            params["regionCode"] = region_code
        if relevance_language:
            params["relevanceLanguage"] = relevance_language
        if page_token:
            params["pageToken"] = page_token

        try:
            request = self.service.search().list(**params)
            response = request.execute()
            return response.get("items", [])
        except HttpError as e:
            logger.error(f"YouTube API error in search_videos_advanced: {e}")
            raise

