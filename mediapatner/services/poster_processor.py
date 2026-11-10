"""
Poster processor module.
Parses Telegram links, scrapes public telegram message embeds,
handles forwarded messages, detects duplicates, and extracts poster media.
"""

import re
import json
import logging
from typing import Optional, Dict, Any, Tuple
import aiohttp
from bs4 import BeautifulSoup
from mediapatner.database.repository import Repository
from mediapatner.database.models import PosterRecord

logger = logging.getLogger(__name__)

# Supported Telegram message link regex
# Matches:
# https://t.me/username/123
# https://telegram.me/username/123
# https://t.me/c/123456789/123
TELEGRAM_LINK_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/(?:(c)/(\d+)|([a-zA-Z0-9_]{4,}))/(\d+)",
    re.IGNORECASE,
)


def extract_telegram_link_info(text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts Telegram channel/chat and message ID from text.
    Returns dict with:
        is_private_c: bool
        channel: str (username or internal id)
        message_id: int
        raw_url: str
    """
    match = TELEGRAM_LINK_PATTERN.search(text)
    if not match:
        return None

    is_c = match.group(1) == "c"
    if is_c:
        channel_id = match.group(2)
        message_id = int(match.group(4))
        raw_url = f"https://t.me/c/{channel_id}/{message_id}"
        return {
            "is_private_c": True,
            "channel": f"-100{channel_id}",
            "message_id": message_id,
            "raw_url": raw_url,
        }
    else:
        channel_username = match.group(3)
        message_id = int(match.group(4))
        raw_url = f"https://t.me/{channel_username}/{message_id}"
        return {
            "is_private_c": False,
            "channel": f"@{channel_username}",
            "username": channel_username,
            "message_id": message_id,
            "raw_url": raw_url,
        }


async def scrape_telegram_embed(username: str, message_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches and parses the public Telegram embed widget:
    https://t.me/<username>/<message_id>?embed=1
    Extracts text, photo URLs, video URLs, and author info.
    """
    embed_url = f"https://t.me/{username}/{message_id}?embed=1"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(embed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning(f"Telegram embed responded with status {resp.status} for {embed_url}")
                    return None

                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")

        # Check for error or not found
        error_elem = soup.find("div", class_="tgme_widget_message_error")
        if error_elem:
            error_text = error_elem.get_text(strip=True)
            logger.info(f"Telegram embed error: {error_text}")
            return None

        # Extract caption / text
        text_elem = soup.find("div", class_="tgme_widget_message_text")
        caption = text_elem.get_text(separator="\n", strip=True) if text_elem else ""

        # Extract photo (background-image in tgme_widget_message_photo_wrap)
        photo_url = None
        photo_wrap = soup.find("a", class_="tgme_widget_message_photo_wrap")
        if photo_wrap and photo_wrap.has_attr("style"):
            style = photo_wrap["style"]
            match = re.search(r"background-image:\s*url\('([^']+)'\)", style)
            if match:
                photo_url = match.group(1)

        # Extract video
        video_url = None
        video_elem = soup.find("video")
        if video_elem and video_elem.has_attr("src"):
            video_url = video_elem["src"]

        # Extract author / channel title
        author_elem = soup.find("div", class_="tgme_widget_message_owner_name")
        channel_title = author_elem.get_text(strip=True) if author_elem else username

        media_type = "photo" if photo_url else ("video" if video_url else "text")

        return {
            "caption": caption,
            "photo_url": photo_url,
            "video_url": video_url,
            "media_type": media_type,
            "channel_title": channel_title,
            "embed_url": embed_url,
        }

    except Exception as e:
        logger.error(f"Error scraping telegram embed for {username}/{message_id}: {e}")
        return None


class PosterProcessor:
    def __init__(self, repository: Repository):
        self.repository = repository

    async def check_duplicate(
        self,
        source_link: Optional[str] = None,
        source_chat_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
    ) -> Optional[PosterRecord]:
        """Checks whether the poster has already been submitted and is currently active."""
        return await self.repository.find_duplicate_poster(
            source_link=source_link,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
        )
