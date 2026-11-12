"""
Vercel Serverless Webhook Handler for MEDIAPATNER BOT.
Receives incoming updates from Telegram, processes via aiogram 3,
and persists SQLite snapshot to Vercel Blob.
"""

from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mediapatner.config import get_settings
from mediapatner.bot import MediaPatnerApplication
from mediapatner.database.blob_sync import save_to_blob

import logging

logger = logging.getLogger(__name__)


async def process_telegram_update(update_data: dict) -> bool:
    settings = get_settings()
    # Create fresh application instance bound to the current event loop
    app = MediaPatnerApplication(settings)
    try:
        # Ensure database is initialized
        await app.db.init()

        # Feed update to aiogram dispatcher
        await app.dp.feed_raw_update(app.bot, update_data)

        # Persist SQLite to Vercel Blob
        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(app.db.db_path)
            except Exception:
                pass

        return True
    finally:
        # Crucial: Always close aiohttp session and database connection for this loop
        try:
            await app.bot.session.close()
        except Exception:
            pass


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode("utf-8")) if body else {}

            if update_data:
                # Run async processing on a clean event loop
                asyncio.run(process_telegram_update(update_data))

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
        except Exception as e:
            logger.exception(f"Error handling Telegram webhook update: {e}")
            # CRITICAL: Always return 200 OK to Telegram API so failed updates are not stuck in retry queue
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode("utf-8"))

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        resp = {
            "status": "online",
            "service": "MEDIAPATNER BOT — ASCHEN EVENT ORGANIZER",
            "mode": "Vercel Serverless Webhook",
        }
        self.wfile.write(json.dumps(resp).encode("utf-8"))
