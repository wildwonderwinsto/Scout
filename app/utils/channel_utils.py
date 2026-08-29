"""
Channel URL/ID parsing utilities.

Handles all the ways a user might reference a YouTube channel:
- Direct channel ID: UCX6OQ3DkcsbYNE6H8uQQuVA
- Channel URL: https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA
- Handle URL: https://www.youtube.com/@MrBeast
- Custom URL: https://www.youtube.com/c/MrBeast
- Legacy user URL: https://www.youtube.com/user/MrBeast6000
- Just the handle: @MrBeast
"""

from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)

# Regex patterns for YouTube channel URL formats
_PATTERNS = [
    # https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxx
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/channel/(UC[\w-]{22})", re.IGNORECASE),
    # https://www.youtube.com/@handle
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/@([\w.-]+)", re.IGNORECASE),
    # https://www.youtube.com/c/CustomName
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/c/([\w.-]+)", re.IGNORECASE),
    # https://www.youtube.com/user/Username
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/user/([\w.-]+)", re.IGNORECASE),
]


def parse_channel_input(input_str: str) -> dict:
    """
    Parse a channel input string and determine what type it is.

    Returns a dict with:
      - "type": "channel_id" | "handle" | "custom_url" | "username" | "search"
      - "value": the extracted value

    Examples:
      "UCX6OQ3DkcsbYNE6H8uQQuVA"
          -> {"type": "channel_id", "value": "UCX6OQ3DkcsbYNE6H8uQQuVA"}
      "https://www.youtube.com/@MrBeast"
          -> {"type": "handle", "value": "MrBeast"}
      "@MrBeast"
          -> {"type": "handle", "value": "MrBeast"}
    """
    input_str = input_str.strip()

    # Direct channel ID (starts with UC, 24 chars)
    if re.match(r"^UC[\w-]{22}$", input_str):
        return {"type": "channel_id", "value": input_str}

    # Handle without URL (starts with @)
    if input_str.startswith("@"):
        return {"type": "handle", "value": input_str.lstrip("@")}

    # Try URL patterns
    for i, pattern in enumerate(_PATTERNS):
        match = pattern.match(input_str)
        if match:
            value = match.group(1)
            if i == 0:
                return {"type": "channel_id", "value": value}
            elif i == 1:
                return {"type": "handle", "value": value}
            elif i == 2:
                return {"type": "custom_url", "value": value}
            elif i == 3:
                return {"type": "username", "value": value}

    # Fallback: treat as a search query to find the channel
    return {"type": "search", "value": input_str}


def resolve_channel_id(input_str: str, youtube_client) -> Optional[str]:
    """
    Resolve any channel input (URL, handle, ID) to a YouTube channel ID.

    Uses the YouTube API to resolve handles, custom URLs, and usernames
    to their actual channel IDs.

    Args:
        input_str: The raw user input (URL, handle, channel ID, etc.)
        youtube_client: A YouTubeClient instance for API calls.

    Returns:
        The resolved channel ID string, or None if not found.
    """
    parsed = parse_channel_input(input_str)
    logger.info(f"Parsed channel input: {parsed}")

    if parsed["type"] == "channel_id":
        return parsed["value"]

    if parsed["type"] == "handle":
        # Use forHandle parameter (YouTube API v3 supports this)
        try:
            request = youtube_client.service.channels().list(
                part="id",
                forHandle=parsed["value"],
            )
            response = request.execute()
            items = response.get("items", [])
            if items:
                return items[0]["id"]
        except Exception as e:
            logger.warning(f"forHandle lookup failed for '{parsed['value']}': {e}")

        # Fallback: search
        results = youtube_client.search_channels(f"@{parsed['value']}", max_results=1)
        if results:
            return results[0]["snippet"]["channelId"]

    elif parsed["type"] in ("custom_url", "username"):
        # Search by name
        results = youtube_client.search_channels(parsed["value"], max_results=5)
        for result in results:
            # Try to match by custom URL
            channel_id = result["snippet"]["channelId"]
            details = youtube_client.get_channel_details(channel_id)
            if details:
                snippet = details.get("snippet", {})
                custom_url = (snippet.get("customUrl") or "").lstrip("@").lower()
                if custom_url == parsed["value"].lower():
                    return channel_id
        # If no exact match, return first result
        if results:
            return results[0]["snippet"]["channelId"]

    elif parsed["type"] == "search":
        results = youtube_client.search_channels(parsed["value"], max_results=1)
        if results:
            return results[0]["snippet"]["channelId"]

    logger.warning(f"Could not resolve channel from input: '{input_str}'")
    return None
