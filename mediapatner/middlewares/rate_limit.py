"""
Spam detection and violation tracking middleware for MEDIAPATNER BOT.
Replaces annoying delay messages with a true spam violation detector.
Normal usage operates with ZERO delays; genuine spam bursts trigger formal violations.
"""

from typing import Any, Awaitable, Callable, Dict, List
import time
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from mediapatner.config import Settings
from mediapatner.database.repository import Repository
from mediapatner.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

# SPAM DETECTION THRESHOLDS:
# Trigger violation if more than 5 messages are sent within 3 seconds
SPAM_WINDOW_SECONDS = 3.0
SPAM_MAX_MESSAGES_IN_WINDOW = 5
SPAM_COOLDOWN_SECONDS = 15.0


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: int = 5):
        super().__init__()
        # History of message timestamps per user: {user_id: [t1, t2, ...]}
        self._user_timestamps: Dict[int, List[float]] = {}
        # Cooldown end timestamp per user: {user_id: expire_time}
        self._user_cooldowns: Dict[int, float] = {}
        # Count of spam violations per user: {user_id: violation_count}
        self._user_violations: Dict[int, int] = {}
        # Track last warning sent to avoid repeating warning messages in a flood
        self._user_last_warned: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        if not user:
            return await handler(event, data)

        settings: Settings = data.get("settings")
        # Admins are exempt from spam throttling
        if settings and settings.is_admin(user.id):
            return await handler(event, data)

        now = time.time()
        user_id = user.id

        # 1. Check if user is currently under a spam violation cooldown
        cooldown_end = self._user_cooldowns.get(user_id, 0.0)
        if now < cooldown_end:
            # Drop spammed messages during cooldown
            time_left = int(cooldown_end - now)
            # Only send warning message once every 5 seconds during cooldown to avoid spamming the user back
            last_warn = self._user_last_warned.get(user_id, 0.0)
            if now - last_warn > 5.0 and isinstance(event, Message):
                self._user_last_warned[user_id] = now
                await event.reply(
                    "𓄲 MEDIAPATNER — PELANGGARAN SPAM 𓈒\n\n"
                    "⚠️ Akses Anda sedang dibatasi sementara karena pelanggaran spam.\n"
                    f"➤ Masa Pembatasan: {time_left} detik lagi.\n\n"
                    "Mohon gunakan layanan dengan tertib dan wajar.",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Akses dibatasi sementara karena spam.", show_alert=True)
            return

        # 2. Track message timestamps for sliding window spam detection
        timestamps = self._user_timestamps.setdefault(user_id, [])
        # Prune timestamps older than window
        self._user_timestamps[user_id] = [t for t in timestamps if now - t < SPAM_WINDOW_SECONDS]
        self._user_timestamps[user_id].append(now)

        # 3. Check if message burst exceeds spam threshold
        if len(self._user_timestamps[user_id]) > SPAM_MAX_MESSAGES_IN_WINDOW:
            # SPAM VIOLATION DETECTED!
            self._user_violations[user_id] = self._user_violations.get(user_id, 0) + 1
            violation_count = self._user_violations[user_id]
            self._user_cooldowns[user_id] = now + SPAM_COOLDOWN_SECONDS
            self._user_last_warned[user_id] = now

            logger.warning(
                f"SPAM VIOLATION: User {user.full_name} ({user_id}) exceeded spam limit. "
                f"Violation #{violation_count}."
            )

            # Log to database if repository is available
            repository: Repository = data.get("repository")
            if repository:
                await repository.log_activity(
                    action="SPAM_VIOLATION",
                    user_id=user_id,
                    details=f"Spam burst detected. Violation #{violation_count}. Cooldown {SPAM_COOLDOWN_SECONDS}s.",
                )

            # Send violation warning to user
            if isinstance(event, Message):
                await event.reply(
                    "𓄲 MEDIAPATNER — PERINGATAN PELANGGARAN SPAM 𓈒\n\n"
                    "⚠️ *Terdeteksi Pelanggaran Spam!*\n"
                    "Aktivitas pengiriman pesan Anda dinilai berlebihan dan melanggar ketentuan sistem.\n\n"
                    f"➤ Status: *PELANGGARAN SPAM (Peringatan ke-{violation_count})*\n"
                    f"➤ Sanksi: *Pembatasan sementara ({int(SPAM_COOLDOWN_SECONDS)} detik)*\n\n"
                    "Mohon hentikan pengiriman beruntun agar akun Anda tidak dibatasi secara permanen oleh sistem ASCHEN.",
                    parse_mode="Markdown",
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    f"⚠️ PELANGGARAN SPAM: Terlalu banyak klik. Dibatasi {int(SPAM_COOLDOWN_SECONDS)} detik.",
                    show_alert=True,
                )

            # Report spam violation to Permanent Notification Channel (-1004479248551)
            notification_service: NotificationService = data.get("notification_service")
            if notification_service:
                username_str = f"@{user.username}" if user.username else "(Tanpa username)"
                try:
                    await notification_service.bot.send_message(
                        chat_id=notification_service.notification_channel_id,
                        text=(
                            "𓄲 MEDIAPATNER — LAPORAN PELANGGARAN SPAM!\n\n"
                            "Terdeteksi pelanggaran spam pengiriman beruntun pada sistem bot.\n\n"
                            f"➤ Pengguna: {user.full_name}\n"
                            f"➤ Username: {username_str}\n"
                            f"➤ User ID: `{user_id}`\n"
                            f"➤ Status: PERINGATAN PELANGGARAN KE-{violation_count}\n"
                            f"➤ Sanksi: Cooldown {int(SPAM_COOLDOWN_SECONDS)} detik\n\n"
                            "© MEDIAPATNER SECURITY SYSTEM"
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.error(f"Failed to report spam violation to channel: {e}")

            return

        # Normal usage passes through instantly without delay!
        return await handler(event, data)
