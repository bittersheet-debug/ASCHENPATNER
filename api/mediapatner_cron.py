"""
Vercel Cron Publishing Handler for MEDIAPATNER BOT.
Triggered at official publishing slots (Selasa/Kamis 09.00 WIB, Rabu/Jumat 12.00 WIB, Sabtu 20.00 WIB).
Queries due posters in KEEP/SCHEDULED queue and publishes to Main Channel @ASCHENEO.
"""

from http.server import BaseHTTPRequestHandler
import json
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mediapatner.config import get_settings
from mediapatner.bot import MediaPatnerApplication
from mediapatner.services.scheduler_service import get_current_wib
from mediapatner.database.blob_sync import save_to_blob


async def run_cron_publishing() -> dict:
    settings = get_settings()
    app = MediaPatnerApplication(settings)
    await app.db.init()

    # Calculate cutoff in WIB
    now_wib = get_current_wib()
    cutoff_iso = now_wib.strftime("%Y-%m-%dT%H:%M:%S")

    # Get posters due
    due_posters = await app.repository.get_posters_due(cutoff_iso)
    published_count = 0
    failed_count = 0

    for poster in due_posters:
        await app.repository.mark_publishing(poster.id)
        success = await app.publisher_service.publish_poster(poster)
        if success:
            published_count += 1
        else:
            failed_count += 1
        await asyncio.sleep(settings.post_interval_seconds)

    # Persist SQLite to Vercel Blob
    if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
        try:
            save_to_blob(app.db.db_path)
        except Exception:
            pass

    return {
        "success": True,
        "due_count": len(due_posters),
        "published": published_count,
        "failed": failed_count,
        "timestamp_wib": now_wib.strftime("%Y-%m-%d %H:%M:%S"),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = asyncio.run(run_cron_publishing())
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
