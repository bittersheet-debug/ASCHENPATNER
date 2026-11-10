"""
Unit tests for Telegram link extraction and parsing.
Verifies Section 3: Format link yang didukung:
- https://t.me/username/123
- https://t.me/channelname/123
- https://telegram.me/channelname/123
"""

import pytest
from mediapatner.services.poster_processor import extract_telegram_link_info


class TestLinkExtraction:
    def test_standard_tme_link(self):
        text = "Halo min, mau share poster: https://t.me/eventinfo/4589 makasih!"
        info = extract_telegram_link_info(text)
        assert info is not None
        assert info["username"] == "eventinfo"
        assert info["channel"] == "@eventinfo"
        assert info["message_id"] == 4589
        assert info["raw_url"] == "https://t.me/eventinfo/4589"
        assert not info["is_private_c"]

    def test_telegram_me_link(self):
        text = "https://telegram.me/aschen_partner/789"
        info = extract_telegram_link_info(text)
        assert info is not None
        assert info["username"] == "aschen_partner"
        assert info["message_id"] == 789

    def test_private_c_link(self):
        text = "https://t.me/c/1847291823/102"
        info = extract_telegram_link_info(text)
        assert info is not None
        assert info["is_private_c"]
        assert info["channel"] == "-1001847291823"
        assert info["message_id"] == 102

    def test_invalid_text(self):
        text = "Ini pesan biasa tanpa tautan telegram."
        assert extract_telegram_link_info(text) is None

        text_google = "https://google.com/search?q=event"
        assert extract_telegram_link_info(text_google) is None
