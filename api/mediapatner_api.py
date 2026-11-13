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
from mediapatner.services.scheduler_service import (
    get_current_wib,
    get_next_official_slot,
    calculate_next_wib_slot,
)
from mediapatner.database.blob_sync import save_to_blob


async def handle_get_request(action: str, query_params: dict) -> dict:
    settings = get_settings()
    db = Database(settings.database_path)
    await db.init()
    repo = Repository(db)

    now_wib = get_current_wib()
    is_sunday = now_wib.weekday() == 6
    is_open = not is_sunday and now_wib.hour >= 6
    next_slot, slot_day, slot_date, slot_time = calculate_next_wib_slot(now_wib)

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
                "display": f"{slot_day}, {slot_date} pukul {slot_time} WIB",
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

    elif action == "ping_channel":
        import time
        import urllib.request
        token = settings.get_token_plain()
        main_channel = settings.channel_username
        start_t = time.perf_counter()
        try:
            url = f"https://api.telegram.org/bot{token}/getChat?chat_id={urllib.parse.quote(main_channel)}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            chat_info = data.get("result", {})
            return {
                "success": True,
                "channel": main_channel,
                "chat_title": chat_info.get("title", main_channel),
                "chat_type": chat_info.get("type", "channel"),
                "latency_ms": elapsed_ms,
                "health_status": "SEHAT & SIAP PUBLIKASI ✅",
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            return {
                "success": False,
                "channel": main_channel,
                "latency_ms": elapsed_ms,
                "error": str(e),
                "health_status": "TERPUTUS / GAGAL ❌",
            }

    elif action == "channel_control":
        channels = await repo.get_channel_settings()
        bots = await repo.get_all_broadcast_bots()
        hist_count = await repo.get_broadcast_history_count()
        return {
            "success": True,
            "channels": {
                "main_id": channels.main_id,
                "main_enabled": channels.main_enabled,
                "poster_id": channels.poster_id,
                "poster_enabled": channels.poster_enabled,
                "channel_1_id": channels.channel_1_id,
                "channel_1_enabled": channels.channel_1_enabled,
                "channel_2_id": channels.channel_2_id,
                "channel_2_enabled": channels.channel_2_enabled,
            },
            "bots": [
                {
                    "bot_id": b.bot_id,
                    "username": b.bot_username,
                    "first_name": b.bot_first_name,
                    "masked_token": b.get_masked_token(),
                    "role": b.role,
                    "is_active": b.is_active,
                    "is_verified": b.is_verified,
                    "last_status": b.last_status,
                }
                for b in bots
            ],
            "stats": {
                "history_count": hist_count,
                "active_bots": len([b for b in bots if b.is_active]),
            },
        }

    elif action == "broadcast_history":
        limit = int(query_params.get("limit", ["20"])[0])
        offset = int(query_params.get("offset", ["0"])[0])
        history_items = await repo.get_broadcast_history(limit=limit, offset=offset)
        total_count = await repo.get_broadcast_history_count()
        return {
            "success": True,
            "total_count": total_count,
            "items": [
                {
                    "job_id": h.job_id,
                    "bot_name": h.bot_name,
                    "target_channel_id": h.target_channel_id,
                    "target_channel_name": h.target_channel_name,
                    "content_type": h.content_type,
                    "content_preview": h.content_preview,
                    "sent_at": h.sent_at,
                    "status": h.status,
                    "error_message": h.error_message,
                    "retry_count": h.retry_count,
                    "published_message_id": h.published_message_id,
                }
                for h in history_items
            ],
        }

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

    elif action == "publish_now":
        poster_id = body_data.get("poster_id")
        if not poster_id:
            return {"success": False, "error": "poster_id wajib disertakan."}

        poster = await repo.get_poster(int(poster_id))
        if not poster:
            return {"success": False, "error": f"Poster #{poster_id} tidak ditemukan."}

        if poster.status == "PUBLISHED":
            return {"success": False, "error": f"Poster #{poster_id} sudah pernah diterbitkan sebelumnya."}

        from mediapatner.bot import MediaPatnerApplication
        app = MediaPatnerApplication(settings)
        await app.db.init()
        await app.repository.mark_publishing(poster.id)
        pub_ok = await app.publisher_service.publish_poster(poster)
        await app.bot.session.close()

        if pub_ok:
            report = await repo.get_poster_report_by_poster_id(poster.id)
            if report:
                await repo.update_poster_report_status(
                    report_id=report.id,
                    status="🚀 Selesai (Sebar Duluan)",
                    processed_by_id=0,
                    processed_by_name="Web Admin",
                    action_note="Sebar duluan via Web Dashboard",
                )

            if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
                try:
                    save_to_blob(db.db_path)
                except Exception:
                    pass

            return {
                "success": True,
                "message": f"Poster #{poster_id} berhasil disebar duluan ke channel {settings.channel_username}!",
            }
        else:
            return {
                "success": False,
                "error": f"Gagal menyebarkan poster #{poster_id}. Silakan periksa izin bot di channel {settings.channel_username}.",
            }

    elif action == "toggle_channel":
        channel_key = body_data.get("channel_key")  # 'ch1', 'ch2', 'poster'
        enabled = bool(body_data.get("enabled"))
        channels = await repo.get_channel_settings()

        if enabled:
            if channel_key == "ch1" and not channels.channel_1_id:
                return {"success": False, "error": "ID Channel 1 belum dikonfigurasi. Atur ID terlebih dahulu."}
            elif channel_key == "ch2" and not channels.channel_2_id:
                return {"success": False, "error": "ID Channel 2 belum dikonfigurasi. Atur ID terlebih dahulu."}

        await repo.set_channel_enabled(channel_key, enabled)
        if not enabled:
            target_cid = (
                channels.channel_1_id if channel_key == "ch1"
                else (channels.channel_2_id if channel_key == "ch2" else channels.poster_id)
            )
            if target_cid:
                await repo.cancel_pending_jobs_for_channel(target_cid)

        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass
        return {"success": True, "message": f"Channel {channel_key} berhasil diubah statusnya."}

    elif action == "set_channel_id":
        channel_key = body_data.get("channel_key")  # '1' or '2'
        channel_id = str(body_data.get("channel_id", "")).strip()
        if not channel_id:
            return {"success": False, "error": "channel_id tidak boleh kosong."}

        await repo.set_channel_id(channel_key, channel_id)
        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass
        return {"success": True, "message": f"ID Channel {channel_key} berhasil diperbarui menjadi {channel_id}."}

    elif action == "set_bot_role":
        bot_id = int(body_data.get("bot_id", 0))
        role = body_data.get("role")
        if not bot_id or not role:
            return {"success": False, "error": "bot_id dan role wajib disertakan."}

        await repo.set_broadcast_bot_role(bot_id, role)
        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass
        return {"success": True, "message": f"Peran bot {bot_id} berhasil diubah menjadi {role}."}

    elif action == "add_bot":
        token = str(body_data.get("token", "")).strip()
        if not token or ":" not in token:
            return {"success": False, "error": "Token bot tidak valid."}

        from mediapatner.services.multi_bot_service import MultiBotService
        from mediapatner.database.models import BroadcastBotRecord

        mbs = MultiBotService(repo, settings)
        is_valid, me_info, err = await mbs.verify_bot_token(token)
        if not is_valid or not me_info:
            return {"success": False, "error": f"Verifikasi bot gagal: {err}"}

        bot_record = BroadcastBotRecord(
            id=None,
            token=token,
            bot_id=me_info["id"],
            bot_username=me_info["username"],
            bot_first_name=me_info.get("first_name"),
            role="cadangan",
            is_active=True,
            is_verified=False,
            last_status="BARU_DIDAFTARKAN",
        )
        await repo.upsert_broadcast_bot(bot_record)
        await mbs.sync_all_bots()

        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass

        return {
            "success": True,
            "message": f"Bot @{me_info['username']} berhasil didaftarkan.",
            "bot": {
                "bot_id": me_info["id"],
                "username": me_info["username"],
                "first_name": me_info.get("first_name"),
            },
        }

    elif action == "sync_bots":
        from mediapatner.services.multi_bot_service import MultiBotService
        mbs = MultiBotService(repo, settings)
        audit_results = await mbs.sync_all_bots()

        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                save_to_blob(db.db_path)
            except Exception:
                pass

        return {"success": True, "results": audit_results}

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
