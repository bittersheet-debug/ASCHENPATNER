"""
Database repository for users, posters, activity logs, settings, and statistics.
"""

from typing import List, Optional, Tuple, Dict, Any
import aiosqlite
import logging
import json
from datetime import datetime
from mediapatner.database.db import Database
from mediapatner.database.models import (
    UserRecord,
    PosterRecord,
    ActivityLogRecord,
    SystemStats,
    AdminDeviceRecord,
    PosterReportRecord,
    OperationalHoursConfig,
    BroadcastBotRecord,
    BroadcastQueueRecord,
    BroadcastHistoryRecord,
    ChannelSettings,
)

logger = logging.getLogger(__name__)


class Repository:
    def __init__(self, db: Database):
        self.db = db

    # ------------------ USERS ------------------
    async def upsert_user(self, user_id: int, username: Optional[str], full_name: str) -> None:
        async with self.db.connection() as conn:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await conn.execute(
                """
                INSERT INTO users (user_id, username, full_name, first_seen, last_seen, total_submissions)
                VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    last_seen = excluded.last_seen
                """,
                (user_id, username, full_name, now_str, now_str),
            )
            await conn.commit()

    async def increment_user_submissions(self, user_id: int) -> None:
        async with self.db.connection() as conn:
            await conn.execute(
                "UPDATE users SET total_submissions = total_submissions + 1 WHERE user_id = ?",
                (user_id,),
            )
            await conn.commit()

    async def get_user(self, user_id: int) -> Optional[UserRecord]:
        async with self.db.connection() as conn:
            async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return UserRecord(
                        user_id=row["user_id"],
                        username=row["username"],
                        full_name=row["full_name"],
                        first_seen=row["first_seen"],
                        last_seen=row["last_seen"],
                        total_submissions=row["total_submissions"],
                    )
        return None

    async def get_all_users(self, limit: int = 50, offset: int = 0) -> List[UserRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM users ORDER BY last_seen DESC LIMIT ? OFFSET ?", (limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    UserRecord(
                        user_id=r["user_id"],
                        username=r["username"],
                        full_name=r["full_name"],
                        first_seen=r["first_seen"],
                        last_seen=r["last_seen"],
                        total_submissions=r["total_submissions"],
                    )
                    for r in rows
                ]

    # ------------------ POSTERS ------------------
    async def create_poster(self, poster: PosterRecord) -> int:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO posters (
                    sender_id, sender_name, sender_username, source_link,
                    source_chat_id, source_message_id, media_type, file_id,
                    caption, raw_data, status, scheduled_slot,
                    slot_day, slot_date, slot_time, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    poster.sender_id,
                    poster.sender_name,
                    poster.sender_username,
                    poster.source_link,
                    poster.source_chat_id,
                    poster.source_message_id,
                    poster.media_type,
                    poster.file_id,
                    poster.caption,
                    poster.raw_data,
                    poster.status,
                    poster.scheduled_slot,
                    poster.slot_day,
                    poster.slot_date,
                    poster.slot_time,
                    poster.retry_count,
                ),
            )
            await conn.commit()
            poster_id = cursor.lastrowid
            return poster_id

    async def get_poster(self, poster_id: int) -> Optional[PosterRecord]:
        async with self.db.connection() as conn:
            async with conn.execute("SELECT * FROM posters WHERE id = ?", (poster_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_poster(row)
        return None

    async def find_duplicate_poster(
        self,
        source_link: Optional[str] = None,
        source_chat_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
    ) -> Optional[PosterRecord]:
        """
        Checks if a poster with the same link or chat+message_id is already active or published.
        Ignores CANCELLED or FAILED posters so they can be re-submitted if needed.
        """
        async with self.db.connection() as conn:
            active_statuses = ("KEEP", "SCHEDULED", "PUBLISHING", "PUBLISHED")
            placeholders = ",".join(["?"] * len(active_statuses))

            if source_link:
                query = f"""
                    SELECT * FROM posters 
                    WHERE source_link = ? AND status IN ({placeholders})
                    ORDER BY id DESC LIMIT 1
                """
                async with conn.execute(query, (source_link, *active_statuses)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return self._row_to_poster(row)

            if source_chat_id and source_message_id:
                query = f"""
                    SELECT * FROM posters 
                    WHERE source_chat_id = ? AND source_message_id = ? AND status IN ({placeholders})
                    ORDER BY id DESC LIMIT 1
                """
                async with conn.execute(query, (source_chat_id, source_message_id, *active_statuses)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return self._row_to_poster(row)

        return None

    async def get_posters_due(self, current_slot_cutoff: str) -> List[PosterRecord]:
        """
        Gets posters with status KEEP or SCHEDULED whose scheduled_slot <= current_slot_cutoff.
        Ordered chronologically so older posters publish first.
        """
        async with self.db.connection() as conn:
            query = """
                SELECT * FROM posters
                WHERE status IN ('KEEP', 'SCHEDULED') AND scheduled_slot <= ?
                ORDER BY scheduled_slot ASC, id ASC
            """
            async with conn.execute(query, (current_slot_cutoff,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_poster(r) for r in rows]

    async def get_all_pending_posters(self) -> List[PosterRecord]:
        """Returns all KEEP and SCHEDULED posters for queue recovery on startup."""
        async with self.db.connection() as conn:
            query = """
                SELECT * FROM posters
                WHERE status IN ('KEEP', 'SCHEDULED')
                ORDER BY scheduled_slot ASC, id ASC
            """
            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_poster(r) for r in rows]

    async def get_posters_by_status(
        self, status: str, limit: int = 10, offset: int = 0
    ) -> List[PosterRecord]:
        async with self.db.connection() as conn:
            query = """
                SELECT * FROM posters
                WHERE status = ?
                ORDER BY scheduled_slot DESC, id DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(query, (status, limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_poster(r) for r in rows]

    async def get_posters_count_by_status(self, status: str) -> int:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT COUNT(*) as count FROM posters WHERE status = ?", (status,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["count"] if row else 0

    async def get_all_posters(self, limit: int = 10, offset: int = 0) -> List[PosterRecord]:
        async with self.db.connection() as conn:
            query = """
                SELECT * FROM posters
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(query, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_poster(r) for r in rows]

    async def get_total_posters_count(self) -> int:
        async with self.db.connection() as conn:
            async with conn.execute("SELECT COUNT(*) as count FROM posters") as cursor:
                row = await cursor.fetchone()
                return row["count"] if row else 0

    async def mark_publishing(self, poster_id: int) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE posters
                SET status = 'PUBLISHING', updated_at = datetime('now', 'localtime')
                WHERE id = ? AND status IN ('KEEP', 'SCHEDULED')
                """,
                (poster_id,),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def mark_published(
        self, poster_id: int, published_message_id: Optional[int] = None
    ) -> bool:
        async with self.db.connection() as conn:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = await conn.execute(
                """
                UPDATE posters
                SET status = 'PUBLISHED',
                    published_at = ?,
                    published_message_id = ?,
                    failure_reason = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (now_str, published_message_id, poster_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def mark_failed(self, poster_id: int, reason: str, increment_retry: bool = True) -> None:
        async with self.db.connection() as conn:
            if increment_retry:
                await conn.execute(
                    """
                    UPDATE posters
                    SET status = 'FAILED',
                        failure_reason = ?,
                        retry_count = retry_count + 1,
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    (reason, poster_id),
                )
            else:
                await conn.execute(
                    """
                    UPDATE posters
                    SET status = 'FAILED',
                        failure_reason = ?,
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    (reason, poster_id),
                )
            await conn.commit()

    async def reschedule_poster(
        self, poster_id: int, scheduled_slot: str, slot_day: str, slot_date: str, slot_time: str
    ) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE posters
                SET status = 'SCHEDULED',
                    scheduled_slot = ?,
                    slot_day = ?,
                    slot_date = ?,
                    slot_time = ?,
                    failure_reason = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (scheduled_slot, slot_day, slot_date, slot_time, poster_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def cancel_poster(self, poster_id: int) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE posters
                SET status = 'CANCELLED', updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (poster_id,),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def delete_poster(self, poster_id: int) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute("DELETE FROM posters WHERE id = ?", (poster_id,))
            await conn.commit()
            return cursor.rowcount > 0

    # ------------------ SETTINGS ------------------
    async def get_setting(self, key: str, default: str = "") -> str:
        async with self.db.connection() as conn:
            async with conn.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        async with self.db.connection() as conn:
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            await conn.commit()

    async def is_auto_forward_enabled(self) -> bool:
        val = await self.get_setting("auto_forward_enabled", "true")
        return val.lower() in ("true", "1", "yes", "on")

    async def toggle_auto_forward(self) -> bool:
        current = await self.is_auto_forward_enabled()
        new_val = not current
        await self.set_setting("auto_forward_enabled", "true" if new_val else "false")
        return new_val

    # ------------------ ACTIVITY LOGS ------------------
    async def log_activity(
        self, action: str, poster_id: Optional[int] = None, user_id: Optional[int] = None, details: Optional[str] = None
    ) -> None:
        async with self.db.connection() as conn:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await conn.execute(
                """
                INSERT INTO activity_logs (poster_id, user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (poster_id, user_id, action, details, now_str),
            )
            await conn.commit()

    async def get_recent_activity(self, limit: int = 15, offset: int = 0) -> List[ActivityLogRecord]:
        async with self.db.connection() as conn:
            query = """
                SELECT * FROM activity_logs
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            async with conn.execute(query, (limit, offset)) as cursor:
                rows = await cursor.fetchall()
                return [
                    ActivityLogRecord(
                        id=r["id"],
                        poster_id=r["poster_id"],
                        user_id=r["user_id"],
                        action=r["action"],
                        details=r["details"],
                        timestamp=r["timestamp"],
                    )
                    for r in rows
                ]

    # ------------------ STATISTICS ------------------
    async def get_system_stats(self) -> SystemStats:
        async with self.db.connection() as conn:
            # Total links received
            async with conn.execute(
                "SELECT COUNT(*) as c FROM posters WHERE source_link IS NOT NULL"
            ) as cur:
                links_count = (await cur.fetchone())["c"]

            # Total posters accepted
            async with conn.execute("SELECT COUNT(*) as c FROM posters") as cur:
                accepted_count = (await cur.fetchone())["c"]

            # Total posters KEEP / SCHEDULED
            async with conn.execute(
                "SELECT COUNT(*) as c FROM posters WHERE status IN ('KEEP', 'SCHEDULED')"
            ) as cur:
                keep_count = (await cur.fetchone())["c"]

            # Total published
            async with conn.execute(
                "SELECT COUNT(*) as c FROM posters WHERE status = 'PUBLISHED'"
            ) as cur:
                published_count = (await cur.fetchone())["c"]

            # Total failed
            async with conn.execute(
                "SELECT COUNT(*) as c FROM posters WHERE status = 'FAILED'"
            ) as cur:
                failed_count = (await cur.fetchone())["c"]

            # Total users
            async with conn.execute("SELECT COUNT(*) as c FROM users") as cur:
                users_count = (await cur.fetchone())["c"]

            # Total activity today
            today_prefix = datetime.now().strftime("%Y-%m-%d") + "%"
            async with conn.execute(
                "SELECT COUNT(*) as c FROM activity_logs WHERE timestamp LIKE ?", (today_prefix,)
            ) as cur:
                today_act = (await cur.fetchone())["c"]

            return SystemStats(
                total_links_received=links_count,
                total_posters_accepted=accepted_count,
                total_posters_keep=keep_count,
                total_posters_published=published_count,
                total_posters_failed=failed_count,
                total_users=users_count,
                total_activity_today=today_act,
            )

    def _row_to_poster(self, r: aiosqlite.Row) -> PosterRecord:
        return PosterRecord(
            id=r["id"],
            sender_id=r["sender_id"],
            sender_name=r["sender_name"],
            sender_username=r["sender_username"],
            source_link=r["source_link"],
            source_chat_id=r["source_chat_id"],
            source_message_id=r["source_message_id"],
            media_type=r["media_type"],
            file_id=r["file_id"],
            caption=r["caption"],
            raw_data=r["raw_data"],
            status=r["status"],
            scheduled_slot=r["scheduled_slot"],
            slot_day=r["slot_day"],
            slot_date=r["slot_date"],
            slot_time=r["slot_time"],
            published_at=r["published_at"],
            published_message_id=r["published_message_id"],
            failure_reason=r["failure_reason"],
            retry_count=r["retry_count"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    # ------------------ ADMIN DEVICES ------------------
    async def register_device(self, device: AdminDeviceRecord) -> None:
        async with self.db.connection() as conn:
            await conn.execute(
                """
                INSERT INTO admin_devices (
                    device_id, admin_id, admin_name, admin_username, phone_number,
                    device_model, session_token, status, login_at, last_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    admin_id = excluded.admin_id,
                    admin_name = excluded.admin_name,
                    admin_username = excluded.admin_username,
                    phone_number = excluded.phone_number,
                    device_model = excluded.device_model,
                    session_token = excluded.session_token,
                    status = excluded.status,
                    login_at = excluded.login_at,
                    last_active = excluded.last_active
                """,
                (
                    device.device_id,
                    device.admin_id,
                    device.admin_name,
                    device.admin_username,
                    device.phone_number,
                    device.device_model,
                    device.session_token,
                    device.status,
                    device.login_at,
                    device.last_active,
                ),
            )
            await conn.commit()

    async def get_active_devices(self) -> List[AdminDeviceRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM admin_devices WHERE status = 'Active' ORDER BY login_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_device(r) for r in rows]

    async def get_device(self, device_id: str) -> Optional[AdminDeviceRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM admin_devices WHERE device_id = ?", (device_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_device(row)
        return None

    async def revoke_device(self, device_id: str) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "UPDATE admin_devices SET status = 'Revoked' WHERE device_id = ?",
                (device_id,),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def revoke_all_devices(self) -> int:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "UPDATE admin_devices SET status = 'Revoked' WHERE status = 'Active'"
            )
            await conn.commit()
            return cursor.rowcount

    def _row_to_device(self, r: aiosqlite.Row) -> AdminDeviceRecord:
        return AdminDeviceRecord(
            device_id=r["device_id"],
            admin_id=r["admin_id"],
            admin_name=r["admin_name"],
            admin_username=r["admin_username"],
            phone_number=r["phone_number"],
            device_model=r["device_model"],
            session_token=r["session_token"],
            status=r["status"],
            login_at=r["login_at"],
            last_active=r["last_active"],
        )

    # ------------------ POSTER REPORTS ------------------
    async def create_poster_report(self, report: PosterReportRecord) -> int:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO poster_reports (
                    poster_id, report_chat_id, report_message_id, sender_id,
                    sender_name, sender_username, institution_name, status,
                    processed_by_id, processed_by_name, processed_at, action_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.poster_id,
                    report.report_chat_id,
                    report.report_message_id,
                    report.sender_id,
                    report.sender_name,
                    report.sender_username,
                    report.institution_name,
                    report.status,
                    report.processed_by_id,
                    report.processed_by_name,
                    report.processed_at,
                    report.action_note,
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def update_report_message_id(self, report_id: int, message_id: int) -> None:
        async with self.db.connection() as conn:
            await conn.execute(
                "UPDATE poster_reports SET report_message_id = ? WHERE id = ?",
                (message_id, report_id),
            )
            await conn.commit()

    async def get_poster_report(self, report_id: int) -> Optional[PosterReportRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM poster_reports WHERE id = ?", (report_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_report(row)
        return None

    async def get_poster_report_by_poster_id(self, poster_id: int) -> Optional[PosterReportRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM poster_reports WHERE poster_id = ? ORDER BY id DESC LIMIT 1",
                (poster_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return self._row_to_report(row)
        return None

    async def update_poster_report_status(
        self,
        report_id: int,
        status: str,
        admin_id: int,
        admin_name: str,
        action_note: Optional[str] = None,
    ) -> bool:
        async with self.db.connection() as conn:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = await conn.execute(
                """
                UPDATE poster_reports
                SET status = ?,
                    processed_by_id = ?,
                    processed_by_name = ?,
                    processed_at = ?,
                    action_note = ?
                WHERE id = ? AND status = 'Menunggu Diproses'
                """,
                (status, admin_id, admin_name, now_str, action_note, report_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def get_poster_reports(
        self, status: Optional[str] = None, limit: int = 10, offset: int = 0
    ) -> List[PosterReportRecord]:
        async with self.db.connection() as conn:
            if status:
                query = "SELECT * FROM poster_reports WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?"
                params = (status, limit, offset)
            else:
                query = "SELECT * FROM poster_reports ORDER BY id DESC LIMIT ? OFFSET ?"
                params = (limit, offset)
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_report(r) for r in rows]

    async def get_poster_reports_count(self, status: Optional[str] = None) -> int:
        async with self.db.connection() as conn:
            if status:
                query = "SELECT COUNT(*) as c FROM poster_reports WHERE status = ?"
                params = (status,)
            else:
                query = "SELECT COUNT(*) as c FROM poster_reports"
                params = ()
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row["c"] if row else 0

    def _row_to_report(self, r: aiosqlite.Row) -> PosterReportRecord:
        return PosterReportRecord(
            id=r["id"],
            poster_id=r["poster_id"],
            report_chat_id=r["report_chat_id"],
            report_message_id=r["report_message_id"],
            sender_id=r["sender_id"],
            sender_name=r["sender_name"],
            sender_username=r["sender_username"],
            institution_name=r["institution_name"],
            status=r["status"],
            processed_by_id=r["processed_by_id"],
            processed_by_name=r["processed_by_name"],
            processed_at=r["processed_at"],
            action_note=r["action_note"],
            created_at=r["created_at"],
        )

    # ------------------ REPORT CHAT & OPERATIONAL SETTINGS ------------------
    async def get_report_chat_id(self) -> str:
        return await self.get_setting("report_chat_id", "-1004479248551")

    async def get_report_chat_type(self) -> str:
        return await self.get_setting("report_chat_type", "PERMANENT_CHANNEL")

    async def set_report_chat_id(self, chat_id: str, chat_type: str = "CUSTOM") -> None:
        await self.set_setting("report_chat_id", str(chat_id).strip())
        await self.set_setting("report_chat_type", chat_type)

    async def get_operational_config(self) -> OperationalHoursConfig:
        open_h = int(await self.get_setting("operational_open_hour", "6"))
        close_h = int(await self.get_setting("operational_close_hour", "22"))
        sun_closed_str = await self.get_setting("operational_sunday_closed", "true")
        sun_closed = sun_closed_str.lower() in ("true", "1", "yes")
        return OperationalHoursConfig(
            open_hour=open_h,
            close_hour=close_h,
            sunday_closed=sun_closed,
        )

    async def set_operational_config(
        self, open_hour: int, close_hour: int, sunday_closed: bool
    ) -> None:
        await self.set_setting("operational_open_hour", str(open_hour))
        await self.set_setting("operational_close_hour", str(close_hour))
        await self.set_setting("operational_sunday_closed", "true" if sunday_closed else "false")

    # ------------------ CHANNEL CONFIGURATION & ON/OFF CONTROL ------------------
    async def get_channel_settings(self) -> ChannelSettings:
        main_id = await self.get_setting("channel_main_id", "-1002123283346")
        main_en = (await self.get_setting("channel_main_enabled", "true")).lower() in ("true", "1", "yes", "on")
        poster_id = await self.get_setting("channel_poster_id", "-1003512801822")
        poster_en = (await self.get_setting("channel_poster_enabled", "true")).lower() in ("true", "1", "yes", "on")
        ch1_id = await self.get_setting("channel_1_id", "")
        ch1_en = (await self.get_setting("channel_1_enabled", "false")).lower() in ("true", "1", "yes", "on")
        ch2_id = await self.get_setting("channel_2_id", "")
        ch2_en = (await self.get_setting("channel_2_enabled", "false")).lower() in ("true", "1", "yes", "on")
        target_mode = await self.get_setting("auto_publish_target", "both")
        return ChannelSettings(
            main_id=main_id,
            main_enabled=main_en,
            poster_id=poster_id,
            poster_enabled=poster_en,
            channel_1_id=ch1_id,
            channel_1_enabled=ch1_en,
            channel_2_id=ch2_id,
            channel_2_enabled=ch2_en,
            auto_publish_target=target_mode,
        )

    async def set_channel_enabled(self, channel_key: str, enabled: bool) -> None:
        ck = str(channel_key).strip().lower()
        if ck in ("ch1", "1"):
            norm_key = "1"
        elif ck in ("ch2", "2"):
            norm_key = "2"
        elif ck in ("main", "channel_main", "utama"):
            norm_key = "main"
        elif ck in ("poster", "channel_poster", "sebar"):
            norm_key = "poster"
        else:
            norm_key = ck
        key = f"channel_{norm_key}_enabled"
        await self.set_setting(key, "true" if enabled else "false")

    async def set_channel_id(self, channel_key: str, channel_id: str) -> None:
        key = f"channel_{channel_key}_id"
        await self.set_setting(key, str(channel_id).strip())

    async def get_auto_publish_target(self) -> str:
        return await self.get_setting("auto_publish_target", "both")

    async def set_auto_publish_target(self, target: str) -> None:
        await self.set_setting("auto_publish_target", str(target).strip().lower())

    async def set_poster_target(self, poster_id: int, target: str) -> bool:
        """Stores specific target destination ('main', 'poster', 'both', 'all') in poster raw_data."""
        poster = await self.get_poster(poster_id)
        if not poster:
            return False
        raw = poster.get_parsed_raw()
        raw["target_destination"] = target.strip().lower()
        new_raw_str = json.dumps(raw)
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "UPDATE posters SET raw_data = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (new_raw_str, poster_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    # ------------------ MULTI-BOT MANAGEMENT ------------------
    async def upsert_broadcast_bot(self, bot: BroadcastBotRecord) -> int:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO broadcast_bots (
                    token, bot_id, bot_username, bot_first_name, role,
                    is_active, is_verified, verified_at, permissions, last_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(token) DO UPDATE SET
                    bot_id = excluded.bot_id,
                    bot_username = excluded.bot_username,
                    bot_first_name = excluded.bot_first_name,
                    role = excluded.role,
                    is_active = excluded.is_active,
                    is_verified = excluded.is_verified,
                    verified_at = excluded.verified_at,
                    permissions = excluded.permissions,
                    last_status = excluded.last_status,
                    updated_at = datetime('now', 'localtime')
                """,
                (
                    bot.token,
                    bot.bot_id,
                    bot.bot_username,
                    bot.bot_first_name,
                    bot.role,
                    1 if bot.is_active else 0,
                    1 if bot.is_verified else 0,
                    bot.verified_at,
                    bot.permissions,
                    bot.last_status,
                ),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    async def get_all_broadcast_bots(self) -> List[BroadcastBotRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM broadcast_bots ORDER BY id ASC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_bot_record(r) for r in rows]

    async def get_broadcast_bot_by_id(self, bot_id: int) -> Optional[BroadcastBotRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM broadcast_bots WHERE bot_id = ?", (bot_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_bot_record(row) if row else None

    async def get_broadcast_bot_by_role(self, role: str) -> Optional[BroadcastBotRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM broadcast_bots WHERE role = ? AND is_active = 1 LIMIT 1", (role,)
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_bot_record(row) if row else None

    async def get_backup_bots(self) -> List[BroadcastBotRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT * FROM broadcast_bots WHERE role = 'cadangan' AND is_active = 1 AND is_verified = 1"
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_bot_record(r) for r in rows]

    async def set_broadcast_bot_role(self, bot_id: int, role: str) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "UPDATE broadcast_bots SET role = ?, updated_at = datetime('now', 'localtime') WHERE bot_id = ?",
                (role, bot_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def update_broadcast_bot_status(
        self, bot_id: int, is_verified: bool, permissions_json: str, last_status: str
    ) -> bool:
        async with self.db.connection() as conn:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = await conn.execute(
                """
                UPDATE broadcast_bots
                SET is_verified = ?,
                    verified_at = ?,
                    permissions = ?,
                    last_status = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE bot_id = ?
                """,
                (1 if is_verified else 0, now_str if is_verified else None, permissions_json, last_status, bot_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def delete_broadcast_bot(self, bot_id: int) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute("DELETE FROM broadcast_bots WHERE bot_id = ?", (bot_id,))
            await conn.commit()
            return cursor.rowcount > 0

    def _row_to_bot_record(self, r: aiosqlite.Row) -> BroadcastBotRecord:
        return BroadcastBotRecord(
            id=r["id"],
            token=r["token"],
            bot_id=r["bot_id"],
            bot_username=r["bot_username"],
            bot_first_name=r["bot_first_name"],
            role=r["role"],
            is_active=bool(r["is_active"]),
            is_verified=bool(r["is_verified"]),
            verified_at=r["verified_at"],
            permissions=r["permissions"],
            last_status=r["last_status"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    # ------------------ BROADCAST QUEUE & ATOMIC LOCK ------------------
    async def enqueue_broadcast_job(self, job: BroadcastQueueRecord) -> Optional[int]:
        """Enqueues a broadcast job using idempotency key to prevent duplication."""
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT OR IGNORE INTO broadcast_queue (
                    job_id, idempotency_key, job_type, payload_id,
                    target_channel_id, target_channel_name, assigned_bot_id,
                    assigned_role, status, retry_count, max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.idempotency_key,
                    job.job_type,
                    job.payload_id,
                    job.target_channel_id,
                    job.target_channel_name,
                    job.assigned_bot_id,
                    job.assigned_role,
                    job.status or "PENDING",
                    job.retry_count,
                    job.max_retries,
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_pending_broadcast_jobs(self, limit: int = 10) -> List[BroadcastQueueRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                """
                SELECT * FROM broadcast_queue
                WHERE status = 'PENDING'
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_queue_record(r) for r in rows]

    async def lock_broadcast_job(self, job_id: str, worker_id: str) -> bool:
        """Atomically locks a pending broadcast job for execution."""
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE broadcast_queue
                SET status = 'PROCESSING',
                    locked_at = datetime('now', 'localtime'),
                    locked_by = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE job_id = ? AND status = 'PENDING'
                """,
                (worker_id, job_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def mark_broadcast_job_success(self, job_id: str) -> bool:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE broadcast_queue
                SET status = 'SUCCESS',
                    locked_at = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE job_id = ?
                """,
                (job_id,),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def mark_broadcast_job_failed(
        self, job_id: str, error_msg: str, increment_retry: bool = True
    ) -> bool:
        async with self.db.connection() as conn:
            async with conn.execute(
                "SELECT retry_count, max_retries FROM broadcast_queue WHERE job_id = ?", (job_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                current_retries = row["retry_count"]
                max_retries = row["max_retries"]

            new_retries = current_retries + 1 if increment_retry else current_retries
            new_status = "FAILED" if new_retries >= max_retries else "PENDING"

            cursor = await conn.execute(
                """
                UPDATE broadcast_queue
                SET status = ?,
                    retry_count = ?,
                    last_error = ?,
                    locked_at = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE job_id = ?
                """,
                (new_status, new_retries, error_msg, job_id),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def cancel_pending_jobs_for_channel(self, channel_id: str) -> int:
        """Immediately halts any pending or queued jobs for a channel when turned OFF."""
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                UPDATE broadcast_queue
                SET status = 'CANCELLED',
                    last_error = 'Channel was turned OFF by administrator',
                    locked_at = NULL,
                    updated_at = datetime('now', 'localtime')
                WHERE target_channel_id = ? AND status IN ('PENDING', 'PROCESSING')
                """,
                (channel_id,),
            )
            await conn.commit()
            return cursor.rowcount

    def _row_to_queue_record(self, r: aiosqlite.Row) -> BroadcastQueueRecord:
        return BroadcastQueueRecord(
            id=r["id"],
            job_id=r["job_id"],
            idempotency_key=r["idempotency_key"],
            job_type=r["job_type"],
            payload_id=r["payload_id"],
            target_channel_id=r["target_channel_id"],
            target_channel_name=r["target_channel_name"],
            assigned_bot_id=r["assigned_bot_id"],
            assigned_role=r["assigned_role"],
            status=r["status"],
            retry_count=r["retry_count"],
            max_retries=r["max_retries"],
            locked_at=r["locked_at"],
            locked_by=r["locked_by"],
            last_error=r["last_error"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    # ------------------ BROADCAST HISTORY & MONITORING ------------------
    async def record_broadcast_history(self, entry: BroadcastHistoryRecord) -> int:
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO broadcast_history (
                    job_id, bot_name, target_channel_id, target_channel_name,
                    content_type, content_preview, sent_at, status,
                    error_message, retry_count, published_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.job_id,
                    entry.bot_name,
                    entry.target_channel_id,
                    entry.target_channel_name,
                    entry.content_type,
                    entry.content_preview,
                    entry.sent_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    entry.status,
                    entry.error_message,
                    entry.retry_count,
                    entry.published_message_id,
                ),
            )
            await conn.commit()
            return cursor.lastrowid or 0

    async def get_broadcast_history(
        self, limit: int = 10, offset: int = 0
    ) -> List[BroadcastHistoryRecord]:
        async with self.db.connection() as conn:
            async with conn.execute(
                """
                SELECT * FROM broadcast_history
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    BroadcastHistoryRecord(
                        id=r["id"],
                        job_id=r["job_id"],
                        bot_name=r["bot_name"],
                        target_channel_id=r["target_channel_id"],
                        target_channel_name=r["target_channel_name"],
                        content_type=r["content_type"],
                        content_preview=r["content_preview"],
                        sent_at=r["sent_at"],
                        status=r["status"],
                        error_message=r["error_message"],
                        retry_count=r["retry_count"],
                        published_message_id=r["published_message_id"],
                        created_at=r["created_at"],
                    )
                    for r in rows
                ]

    async def get_broadcast_history_count(self) -> int:
        async with self.db.connection() as conn:
            async with conn.execute("SELECT COUNT(*) as count FROM broadcast_history") as cursor:
                row = await cursor.fetchone()
                return row["count"] if row else 0

