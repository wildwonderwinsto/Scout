"""
Tests for channel URL parsing and resolution.
"""

from app.utils.channel_utils import parse_channel_input

class TestParseChannelInput:
    def test_direct_id(self):
        res = parse_channel_input("UCX6OQ3DkcsbYNE6H8uQQuVA")
        assert res["type"] == "channel_id"
        assert res["value"] == "UCX6OQ3DkcsbYNE6H8uQQuVA"

    def test_full_url_id(self):
        res = parse_channel_input("https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA")
        assert res["type"] == "channel_id"
        assert res["value"] == "UCX6OQ3DkcsbYNE6H8uQQuVA"

    def test_handle_url(self):
        res = parse_channel_input("https://www.youtube.com/@MrBeast")
        assert res["type"] == "handle"
        assert res["value"] == "MrBeast"

    def test_bare_handle(self):
        res = parse_channel_input("@MrBeast")
        assert res["type"] == "handle"
        assert res["value"] == "MrBeast"

    def test_custom_url(self):
        res = parse_channel_input("https://www.youtube.com/c/mkbhd")
        assert res["type"] == "custom_url"
        assert res["value"] == "mkbhd"

    def test_legacy_user(self):
        res = parse_channel_input("youtube.com/user/pewdiepie")
        assert res["type"] == "username"
        assert res["value"] == "pewdiepie"

    def test_search_fallback(self):
        res = parse_channel_input("Just some random name")
        assert res["type"] == "search"
        assert res["value"] == "Just some random name"
