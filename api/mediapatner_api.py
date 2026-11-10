"""
Vercel Serverless REST API for MEDIAPATNER Web Dashboard & Website.
Provides real-time statistics, poster queue management, device management,
and operational status for ASCHEN EVENT ORGANIZER.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import asyncio
import urllib.parse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mediapatner.config import get_settings
from mediapatner.database.db import Database
from mediapatner.database.repository import Repository
from mediapatner.services.scheduler_service import get_current_wib, get_next_official_slot
from mediapatner.database.blob_sync import save_to_blob


async def handle_get_request(action: str, query_params: dict) -> dict:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()
    repo = Repository(db)

    now_wib = get_current_wib()
    is_sunday = now_wib.weekday() == 6
    is_open = not is_sunday and now_wib.hour >= 6
    next_slot = get_next_official_slot(now_wib)

    if action == "status" or not action:
        stats = await repo.get_system_stats()
        report_chat = await repo.get_report_chat_id()
        active_devices = await repo.get_active_devices()
        return {
            "success": True,
            "status": "online",
            "bot_username": "@PATNERASCHENBOT",
            "channel_username": settings.channel_username,
            "channel_link": settings.channel_link,
            "report_chat_id": report_chat,
            "active_devices_count": len(active_devices),
            "current_time_wib": now_wib.strftime("%Y-%m-%d %H:%M:%S WIB"),
            "operational": {
                "is_open": is_open,
                "note": "Operasional: Senin–Sabtu mulai 06.00 WIB. Minggu TUTUP.",
                "today": now_wib.strftime("%A"),
            },
            "next_slot": {
                "iso": next_slot.isoformat(),
                "display": next_slot.strftime("%A, %d %B %Y pukul %H.%M WIB"),
            },
            "stats": {
                "total_received": stats.total_links_received,
                "total_accepted": stats.total_posters_accepted,
                "total_keep": stats.total_posters_keep,
                "total_published": stats.total_posters_published,
                "total_failed": stats.total_posters_failed,
                "total_users": stats.total_users,
            },
        }

    elif action == "posters":
        limit = int(query_params.get("limit", ["50"])[0])
        posters = await repo.get_all_posters(limit=limit, offset=0)
        results = []
        for p in posters:
            results.append({
                "id": p.id,
                "sender_id": p.sender_id,
                "sender_name": p.sender_name,
                "sender_username": p.sender_username,
                "source_link": p.source_link,
                "media_type": p.media_type,
                "caption": p.caption,
                "status": p.status,
                "scheduled_slot": p.scheduled_slot,
                "slot_day": p.slot_day,
                "slot_date": p.slot_date,
                "slot_time": p.slot_time,
                "published_at": p.published_at,
                "created_at": p.created_at,
            })
        return {"success": True, "count": len(results), "posters": results}

    elif action == "reports":
        limit = int(query_params.get("limit", ["50"])[0])
        status = query_params.get("status", [None])[0]
        reports = await repo.get_poster_reports(limit=limit, offset=0, status=status)
        results = []
        for r in reports:
            results.append({
                "id": r.id,
                "poster_id": r.poster_id,
                "report_chat_id": r.report_chat_id,
                "sender_id": r.sender_id,
                "sender_name": r.sender_name,
                "sender_username": r.sender_username,
                "institution_name": r.institution_name,
                "status": r.status,
                "processed_by_name": r.processed_by_name,
                "processed_at": r.processed_at,
                "action_note": r.action_note,
                "created_at": r.created_at,
            })
        return {"success": True, "count": len(results), "reports": results}

    elif action == "devices":
        devices = await repo.get_active_devices()
        results = []
        for d in devices:
            results.append({
                "device_id": d.device_id,
                "admin_id": d.admin_id,
                "admin_name": d.admin_name,
                "phone_number": d.phone_number,
                "device_model": d.device_model,
                "status": d.status,
                "login_at": d.login_at,
                "last_active": d.last_active,
            })
        return {"success": True, "count": len(results), "devices": results}

    return {"success": False, "error": f"Unknown action: {action}"}


async def handle_post_request(body_data: dict) -> dict:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()
    repo = Repository(db)

    action = body_data.get("action")

    if action == "login":
        password = body_data.get("password", "").strip()
        if password == settings.admin_password:
            return {
                "success": True,
                "message": "Login berhasil.",
                "token": "aschen-admin-authenticated",
                "role": "admin",
            }
        return {"success": False, "error": "Kata sandi salah. Silakan coba lagi."}

    elif action == "update_report_status":
        report_id = body_data.get("report_id")
        new_status = body_data.get("status")  # 'Diterima', 'Ditolak', 'Selesai'
        admin_name = body_data.get("admin_name", "Web Admin")
        admin_id = int(body_data.get("admin_id", 0))

        if not report_id or not new_status:
            return {"success": False, "error": "report_id dan status wajib disertakan."}

        success = await repo.update_poster_report_status(
            report_id=int(report_id),
            status=new_status,
            processed_by_id=admin_id,
            processed_by_name=admin_name,
            action_note="Diperbarui melalui Web Dashboard",
        )

        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass

        return {
            "success": success,
            "message": f"Status laporan #{report_id} berhasil diubah menjadi: {new_status}",
        }

    elif action == "set_report_chat":
        new_chat_id = str(body_data.get("chat_id", "")).strip()
        if not new_chat_id:
            return {"success": False, "error": "chat_id tidak boleh kosong."}

        await repo.set_report_chat_id(new_chat_id, "CUSTOM_WEB")
        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass

        return {
            "success": True,
            "message": f"Chat tujuan pelaporan berhasil diperbarui ke: {new_chat_id}",
        }

    return {"success": False, "error": f"Unknown post action: {action}"}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed.query)
            action = query_params.get("action", ["status"])[0]

            result = asyncio.run(handle_get_request(action, query_params))
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length).decode("utf-8")
            body_data = json.loads(raw_body) if raw_body else {}

            result = asyncio.run(handle_post_request(body_data))
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
