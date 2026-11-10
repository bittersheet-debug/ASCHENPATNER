"""
Database repository for users, posters, activity logs, settings, and statistics.
"""

from typing import List, Optional, Tuple, Dict, Any
import aiosqlite
import logging
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

