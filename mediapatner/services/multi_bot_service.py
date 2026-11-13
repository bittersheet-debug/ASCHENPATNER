"""
Multi-Bot Coordination, Queue Dispatcher, Channel Control & Administrator Permission Service.
Manages:
- Dynamic multi-bot registration & automated verification
- Channel-specific task assignment (Bot Channel 1, Bot Channel 2, Bot Poster, Bot Cadangan)
- Failover system: switches tasks to Bot Cadangan if primary bot fails or lacks permissions
- Independent channel dispatch logic (C.1 - C.7)
- Poster dispatch directed exclusively to Channel Poster (D.1 - D.8)
- Anti-duplication, atomic queue locking, and broadcast history recording
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import URLInputFile
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

from mediapatner.config import Settings
from mediapatner.database.models import (
    BroadcastBotRecord,
    BroadcastQueueRecord,
    BroadcastHistoryRecord,
    ChannelSettings,
    PosterRecord,
)
from mediapatner.database.repository import Repository

logger = logging.getLogger(__name__)


class MultiBotService:
    def __init__(self, repository: Repository, settings: Settings, default_bot: Optional[Bot] = None):
        self.repository = repository
        self.settings = settings
        self.default_bot = default_bot
        # Cached Bot instances by token string
        self._bot_cache: Dict[str, Bot] = {}

    def get_bot_instance(self, token: str) -> Bot:
        """Returns or creates a cached Bot API client for the provided token."""
        clean_token = token.strip()
        if clean_token not in self._bot_cache:
            self._bot_cache[clean_token] = Bot(
                token=clean_token,
                default=DefaultBotProperties(parse_mode=None),
            )
        return self._bot_cache[clean_token]

    async def close_all_sessions(self) -> None:
        """Closes all active aiohttp sessions for cached bot instances."""
        for token, bot in list(self._bot_cache.items()):
            try:
                await bot.session.close()
                if hasattr(bot.session, "_session"):
                    bot.session._session = None
            except Exception as e:
                logger.warning(f"Error closing bot session: {e}")
        self._bot_cache.clear()

    # ------------------ BOT VERIFICATION & SYNCHRONIZATION ------------------
    async def verify_bot_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Validates token with getMe() API call.
        Returns: (is_valid, me_dict, error_message)
        """
        try:
            bot = Bot(token=token.strip())
            try:
                me = await bot.get_me()
                return (
                    True,
                    {
                        "id": me.id,
                        "username": me.username or "",
                        "first_name": me.first_name or "",
                        "can_join_groups": me.can_join_groups,
                        "can_read_all_group_messages": me.can_read_all_group_messages,
                        "supports_inline_queries": me.supports_inline_queries,
                    },
                    "OK",
                )
            finally:
                await bot.session.close()
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False, None, str(e)

    async def check_channel_permissions(
        self, bot: Bot, channel_id: str
    ) -> Tuple[bool, Dict[str, Any], str]:
        """
        Checks whether the bot has administrator status and sending rights in a given channel.
        Returns: (has_rights, details, status_label)
        """
        if not channel_id or not str(channel_id).strip():
            return False, {}, "CHANNEL_UNSET"

        target_id = str(channel_id).strip()
        try:
            me = await bot.get_me()
            member = await bot.get_chat_member(chat_id=target_id, user_id=me.id)

            status = getattr(member, "status", None)
            is_admin = status in ("creator", "administrator")

            can_post = getattr(member, "can_post_messages", True) if is_admin else False
            can_edit = getattr(member, "can_edit_messages", True) if is_admin else False

            details = {
                "channel_id": target_id,
                "status": status,
                "is_admin": is_admin,
                "can_post_messages": can_post,
                "can_edit_messages": can_edit,
            }

            if is_admin and (can_post or status == "creator"):
                return True, details, "ADMIN_OK"
            elif is_admin:
                return False, details, "ADMIN_NO_POST_PERMISSION"
            else:
                return False, details, "NOT_AN_ADMINISTRATOR"
        except TelegramForbiddenError:
            return False, {"channel_id": target_id}, "BOT_FORBIDDEN"
        except TelegramBadRequest as e:
            return False, {"channel_id": target_id, "error": str(e)}, "BAD_REQUEST_OR_NOT_FOUND"
        except Exception as e:
            return False, {"channel_id": target_id, "error": str(e)}, f"ERROR: {e}"

    async def sync_all_bots(self) -> List[Dict[str, Any]]:
        """
        Section E: Automated Multi-Bot Detection & Synchronization.
        Audits every registered bot across all active channels:
        - Channel Utama (-1002123283346)
        - Channel Poster (-1003512801822)
        - Channel 1 (if configured)
        - Channel 2 (if configured)
        Updates permissions, authorization status, and logs changes.
        """
        bots = await self.repository.get_all_broadcast_bots()
        channels = await self.repository.get_channel_settings()

        audit_results = []
        for b in bots:
            if not b.is_active:
                audit_results.append({
                    "bot_id": b.bot_id,
                    "username": b.bot_username,
                    "role": b.role,
                    "status": "NONAKTIF",
                    "permissions": {},
                })
                continue

            bot_instance = self.get_bot_instance(b.token)
            perm_dict: Dict[str, Any] = {}
            is_overall_verified = False

            # 1. Test Channel Poster
            if channels.poster_id:
                ok, det, lbl = await self.check_channel_permissions(bot_instance, channels.poster_id)
                perm_dict["channel_poster"] = {"ok": ok, "label": lbl, "details": det}
                if ok:
                    is_overall_verified = True

            # 2. Test Channel Utama
            if channels.main_id:
                ok, det, lbl = await self.check_channel_permissions(bot_instance, channels.main_id)
                perm_dict["channel_main"] = {"ok": ok, "label": lbl, "details": det}
                if ok:
                    is_overall_verified = True

            # 3. Test Channel 1 (if set)
            if channels.channel_1_id:
                ok, det, lbl = await self.check_channel_permissions(bot_instance, channels.channel_1_id)
                perm_dict["channel_1"] = {"ok": ok, "label": lbl, "details": det}
                if ok:
                    is_overall_verified = True

            # 4. Test Channel 2 (if set)
            if channels.channel_2_id:
                ok, det, lbl = await self.check_channel_permissions(bot_instance, channels.channel_2_id)
                perm_dict["channel_2"] = {"ok": ok, "label": lbl, "details": det}
                if ok:
                    is_overall_verified = True

            status_str = "VERIFIED_OK" if is_overall_verified else "NEEDS_ADMIN_RIGHTS"

            await self.repository.update_broadcast_bot_status(
                bot_id=b.bot_id,
                is_verified=is_overall_verified,
                permissions_json=json.dumps(perm_dict),
                last_status=status_str,
            )

            audit_results.append({
                "bot_id": b.bot_id,
                "username": b.bot_username,
                "role": b.role,
                "status": status_str,
                "permissions": perm_dict,
            })

        return audit_results

    # ------------------ TASK DISTRIBUTION & FAILOVER RESOLVER ------------------
    async def resolve_bot_for_target(
        self, target_role: str, target_channel_id: str
    ) -> Tuple[Optional[Bot], str, Optional[str]]:
        """
        Resolves the appropriate authorized bot for a specific role and channel.
        If the primary assigned bot is missing, unverified, or encounters errors,
        transparently fails over to an authorized Bot Cadangan (Backup Bot).
        Returns: (bot_instance, bot_identifier_name, failover_note)
        """
        # 1. Attempt primary assigned bot for the role
        primary = await self.repository.get_broadcast_bot_by_role(target_role)
        if primary and primary.is_active:
            bot_obj = self.get_bot_instance(primary.token)
            return bot_obj, f"@{primary.bot_username}", None

        # 2. Primary bot unavailable or unset -> Attempt Bot Cadangan
        backup_bots = await self.repository.get_backup_bots()
        for backup in backup_bots:
            if backup.is_active:
                bot_obj = self.get_bot_instance(backup.token)
                note = f"Failover: Bot Cadangan (@{backup.bot_username}) menggantikan role '{target_role}'"
                logger.warning(note)
                return bot_obj, f"@{backup.bot_username} (Cadangan)", note

        # 3. Fallback to default bot if available
        if self.default_bot:
            note = f"Fallback: Default bot digunakan untuk role '{target_role}'"
            return self.default_bot, "@PATNERASCHENBOT (Default)", note

        return None, "NO_AUTHORIZED_BOT", "Tidak ada bot yang diotorisasi untuk tugas ini"

    # ------------------ POSTER DISPATCH (SECTION D) ------------------
    async def dispatch_poster_publication(self, poster: PosterRecord) -> Tuple[bool, Optional[int], str]:
        """
        Section D: Directed exclusively to Channel Poster ("-1003512801822").
        Enforces:
        - Must be sent only to Channel Poster, never automatically to Channel 1 or 2.
        - Checks if Channel Poster is ON. If OFF, stops delivery immediately.
        - Prevents duplicate sending using idempotency key: poster:{id}:-1003512801822.
        - Uses Bot Poster, with automatic failover to Bot Cadangan on error.
        - Records complete dispatch history in broadcast_history.
        """
        channels = await self.repository.get_channel_settings()

        # D.6 / D.7: If Channel Poster is OFF, immediately halt all poster publishing
        if not channels.poster_enabled:
            reason = "Channel Poster sedang NONAKTIF (OFF). Seluruh pengiriman poster dihentikan."
            logger.warning(f"Poster #{poster.id} blocked: {reason}")
            await self.repository.log_activity(
                action="POSTER_BLOCKED",
                poster_id=poster.id,
                user_id=poster.sender_id,
                details=reason,
            )
            return False, None, reason

        poster_channel_id = channels.poster_id or "-1003512801822"
        idempotency_key = f"poster:{poster.id}:{poster_channel_id}"
        job_id = f"JOB-POSTER-{poster.id}-{uuid.uuid4().hex[:6].upper()}"

        # Enqueue with atomic duplicate prevention
        queue_job = BroadcastQueueRecord(
            id=None,
            job_id=job_id,
            idempotency_key=idempotency_key,
            job_type="poster",
            payload_id=poster.id,
            target_channel_id=poster_channel_id,
            target_channel_name="Channel Poster",
            assigned_bot_id=None,
            assigned_role="poster",
            status="PENDING",
            retry_count=0,
            max_retries=3,
        )
        await self.repository.enqueue_broadcast_job(queue_job)

        # Atomic lock
        worker_id = f"worker-{uuid.uuid4().hex[:4]}"
        locked = await self.repository.lock_broadcast_job(job_id, worker_id)
        if not locked:
            # Another worker already locked or processed this job
            return False, None, "Pekerjaan poster ini sudah diproses atau sedang berjalan (Lock aktif)."

        # Resolve Bot Poster (with failover)
        bot, bot_name, failover_note = await self.resolve_bot_for_target("poster", poster_channel_id)
        if not bot:
            err = "Tidak ada Bot Poster atau Bot Cadangan yang diotorisasi."
            await self.repository.mark_broadcast_job_failed(job_id, err)
            await self.repository.record_broadcast_history(
                BroadcastHistoryRecord(
                    id=None,
                    job_id=job_id,
                    bot_name="None",
                    target_channel_id=poster_channel_id,
                    target_channel_name="Channel Poster",
                    content_type="Poster",
                    content_preview=f"Poster #{poster.id} by {poster.sender_name}",
                    sent_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    status="FAILED",
                    error_message=err,
                    retry_count=1,
                )
            )
            return False, None, err

        # Execute publication to Channel Poster
        raw_data = poster.get_parsed_raw()
        direct_chat_id = raw_data.get("direct_chat_id")
        direct_message_id = raw_data.get("direct_message_id")
        published_msg_id: Optional[int] = None
        send_error: Optional[Exception] = None

        # Method 1: Copy message (preserves exact original media and text)
        if direct_chat_id and direct_message_id:
            try:
                sent = await bot.copy_message(
                    chat_id=poster_channel_id,
                    from_chat_id=direct_chat_id,
                    message_id=direct_message_id,
                )
                published_msg_id = sent.message_id
            except Exception as e:
                logger.warning(f"Copy message to Channel Poster failed: {e}")
                send_error = e

        # Method 2: Direct media send
        if published_msg_id is None:
            try:
                caption = poster.caption or None
                photo_url = raw_data.get("photo_url")
                video_url = raw_data.get("video_url")

                if poster.media_type == "photo" or photo_url:
                    photo_src = poster.file_id or (URLInputFile(photo_url) if photo_url else None)
                    if photo_src:
                        sent = await bot.send_photo(
                            chat_id=poster_channel_id,
                            photo=photo_src,
                            caption=caption,
                        )
                        published_msg_id = sent.message_id
                elif poster.media_type == "video" or video_url:
                    video_src = poster.file_id or (URLInputFile(video_url) if video_url else None)
                    if video_src:
                        sent = await bot.send_video(
                            chat_id=poster_channel_id,
                            video=video_src,
                            caption=caption,
                        )
                        published_msg_id = sent.message_id
                elif poster.media_type == "document" and poster.file_id:
                    sent = await bot.send_document(
                        chat_id=poster_channel_id,
                        document=poster.file_id,
                        caption=caption,
                    )
                    published_msg_id = sent.message_id
                else:
                    sent = await bot.send_message(
                        chat_id=poster_channel_id,
                        text=caption or "Media Partner Poster",
                    )
                    published_msg_id = sent.message_id
            except Exception as e:
                logger.error(f"Direct media send to Channel Poster failed: {e}")
                send_error = e

        # Failover to Bot Cadangan if primary failed
        if published_msg_id is None:
            backup_bots = await self.repository.get_backup_bots()
            for backup in backup_bots:
                if backup.is_active:
                    backup_bot_obj = self.get_bot_instance(backup.token)
                    logger.info(f"Attempting failover to Bot Cadangan @{backup.bot_username} for poster #{poster.id}")
                    try:
                        caption = poster.caption or None
                        photo_url = raw_data.get("photo_url")
                        photo_src = poster.file_id or (URLInputFile(photo_url) if photo_url else None)
                        if photo_src:
                            sent = await backup_bot_obj.send_photo(
                                chat_id=poster_channel_id,
                                photo=photo_src,
                                caption=caption,
                            )
                            published_msg_id = sent.message_id
                            bot_name = f"@{backup.bot_username} (Cadangan - Failover)"
                            send_error = None
                            break
                    except Exception as fb_err:
                        logger.warning(f"Backup bot failover also failed: {fb_err}")
                        send_error = fb_err

        # Record outcome
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if published_msg_id is not None:
            await self.repository.mark_broadcast_job_success(job_id)
            await self.repository.record_broadcast_history(
                BroadcastHistoryRecord(
                    id=None,
                    job_id=job_id,
                    bot_name=bot_name,
                    target_channel_id=poster_channel_id,
                    target_channel_name="Channel Poster",
                    content_type="Poster " + (poster.media_type or "Media").capitalize(),
                    content_preview=f"Poster #{poster.id} ({poster.sender_name})",
                    sent_at=now_str,
                    status="SUCCESS",
                    error_message=None,
                    retry_count=1,
                    published_message_id=published_msg_id,
                )
            )
            return True, published_msg_id, "SUCCESS"
        else:
            err_msg = str(send_error) if send_error else "Gagal menyebarkan ke Channel Poster."
            await self.repository.mark_broadcast_job_failed(job_id, err_msg)
            await self.repository.record_broadcast_history(
                BroadcastHistoryRecord(
                    id=None,
                    job_id=job_id,
                    bot_name=bot_name,
                    target_channel_id=poster_channel_id,
                    target_channel_name="Channel Poster",
                    content_type="Poster " + (poster.media_type or "Media").capitalize(),
                    content_preview=f"Poster #{poster.id} ({poster.sender_name})",
                    sent_at=now_str,
                    status="FAILED",
                    error_message=err_msg,
                    retry_count=1,
                )
            )
            return False, None, err_msg

    # ------------------ CHANNEL 1 & CHANNEL 2 MESSAGE DISPATCH (SECTION C) ------------------
    async def broadcast_message_to_channels(
        self,
        text: str,
        media_file_id: Optional[str] = None,
        media_type: Optional[str] = None,
        author_name: str = "Administrator",
    ) -> Dict[str, Any]:
        """
        Section C: Message Distribution Logic for Channel 1 and Channel 2:
        1. If Channel 1 ON & Channel 2 OFF -> send only to Channel 1.
        2. If Channel 1 OFF & Channel 2 ON -> send only to Channel 2.
        3. If Channel 1 ON & Channel 2 ON -> send to both channels.
        4. If Channel 1 OFF & Channel 2 OFF -> stop dispatch to both channels.
        5. Never send to a channel that is OFF.
        6. Reject if channel ID is not configured (prevent guessing/inventing IDs).
        """
        channels = await self.repository.get_channel_settings()

        # Check configuration & ON/OFF state
        ch1_ready = channels.channel_1_enabled and bool(channels.channel_1_id and str(channels.channel_1_id).strip())
        ch2_ready = channels.channel_2_enabled and bool(channels.channel_2_id and str(channels.channel_2_id).strip())

        # Rule C.4: If Channel 1 OFF and Channel 2 OFF, halt broadcast completely
        if not ch1_ready and not ch2_ready:
            msg = (
                "⚠️ *Penyebaran Dibatalkan:*\n"
                "Kedua Channel (Channel 1 dan Channel 2) sedang dalam kondisi *NONAKTIF (OFF)* "
                "atau ID channel belum dikonfigurasi oleh admin."
            )
            return {
                "ok": False,
                "targets_sent": [],
                "targets_skipped": ["Channel 1", "Channel 2"],
                "message": msg,
            }

        targets: List[Tuple[str, str, str]] = []  # (channel_key, channel_id, assigned_role)

        # Rule C.1 & C.3: Include Channel 1 if ON
        if ch1_ready:
            targets.append(("Channel 1", channels.channel_1_id, "channel_1"))

        # Rule C.2 & C.3: Include Channel 2 if ON
        if ch2_ready:
            targets.append(("Channel 2", channels.channel_2_id, "channel_2"))

        results = []
        for name, ch_id, role in targets:
            job_id = f"JOB-MSG-{uuid.uuid4().hex[:8].upper()}"
            idempotency_key = f"msg:{hash(text)}:{ch_id}:{datetime.now().strftime('%Y%m%d%H%M')}"

            # Enqueue
            queue_job = BroadcastQueueRecord(
                id=None,
                job_id=job_id,
                idempotency_key=idempotency_key,
                job_type="message",
                payload_id=None,
                target_channel_id=ch_id,
                target_channel_name=name,
                assigned_bot_id=None,
                assigned_role=role,
                status="PENDING",
            )
            await self.repository.enqueue_broadcast_job(queue_job)

            # Atomic lock
            worker_id = f"worker-{uuid.uuid4().hex[:4]}"
            locked = await self.repository.lock_broadcast_job(job_id, worker_id)
            if not locked:
                continue

            # Resolve bot
            bot, bot_name, failover_note = await self.resolve_bot_for_target(role, ch_id)
            if not bot:
                err_text = f"Tidak ada bot aktif/terverifikasi untuk {name}"
                await self.repository.mark_broadcast_job_failed(job_id, err_text)
                await self.repository.record_broadcast_history(
                    BroadcastHistoryRecord(
                        id=None,
                        job_id=job_id,
                        bot_name="None",
                        target_channel_id=ch_id,
                        target_channel_name=name,
                        content_type="Pesan Siaran",
                        content_preview=text[:60] + "...",
                        sent_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        status="FAILED",
                        error_message=err_text,
                    )
                )
                results.append({"channel": name, "ok": False, "error": err_text})
                continue

            # Send message or media
            pub_id: Optional[int] = None
            send_err: Optional[Exception] = None
            try:
                if media_type == "photo" and media_file_id:
                    sent = await bot.send_photo(chat_id=ch_id, photo=media_file_id, caption=text)
                    pub_id = sent.message_id
                elif media_type == "video" and media_file_id:
                    sent = await bot.send_video(chat_id=ch_id, video=media_file_id, caption=text)
                    pub_id = sent.message_id
                elif media_type == "document" and media_file_id:
                    sent = await bot.send_document(chat_id=ch_id, document=media_file_id, caption=text)
                    pub_id = sent.message_id
                else:
                    sent = await bot.send_message(chat_id=ch_id, text=text)
                    pub_id = sent.message_id
            except Exception as e:
                logger.warning(f"Direct send to {name} with bot {bot_name} failed: {e}")
                send_err = e

            # Failover to Bot Cadangan if needed
            if pub_id is None:
                backup_bots = await self.repository.get_backup_bots()
                for backup in backup_bots:
                    if backup.is_active:
                        backup_bot = self.get_bot_instance(backup.token)
                        logger.info(f"Attempting failover to Bot Cadangan @{backup.bot_username} for {name}")
                        try:
                            if media_file_id:
                                sent = await backup_bot.send_photo(chat_id=ch_id, photo=media_file_id, caption=text)
                            else:
                                sent = await backup_bot.send_message(chat_id=ch_id, text=text)
                            pub_id = sent.message_id
                            bot_name = f"@{backup.bot_username} (Cadangan)"
                            send_err = None
                            break
                        except Exception as fb_err:
                            send_err = fb_err

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if pub_id is not None:
                await self.repository.mark_broadcast_job_success(job_id)
                await self.repository.record_broadcast_history(
                    BroadcastHistoryRecord(
                        id=None,
                        job_id=job_id,
                        bot_name=bot_name,
                        target_channel_id=ch_id,
                        target_channel_name=name,
                        content_type="Pesan Siaran",
                        content_preview=text[:60] + "...",
                        sent_at=now_str,
                        status="SUCCESS",
                        error_message=None,
                        published_message_id=pub_id,
                    )
                )
                results.append({"channel": name, "ok": True, "bot": bot_name, "message_id": pub_id})
            else:
                err_text = str(send_err) if send_err else "Gagal mengirim pesan"
                await self.repository.mark_broadcast_job_failed(job_id, err_text)
                await self.repository.record_broadcast_history(
                    BroadcastHistoryRecord(
                        id=None,
                        job_id=job_id,
                        bot_name=bot_name,
                        target_channel_id=ch_id,
                        target_channel_name=name,
                        content_type="Pesan Siaran",
                        content_preview=text[:60] + "...",
                        sent_at=now_str,
                        status="FAILED",
                        error_message=err_text,
                    )
                )
                results.append({"channel": name, "ok": False, "error": err_text})

            # Small rate-limiting pause between channel dispatches
            await asyncio.sleep(0.5)

        sent_count = sum(1 for r in results if r.get("ok"))
        return {
            "ok": sent_count > 0,
            "results": results,
            "message": f"Berhasil disebarkan ke {sent_count} dari {len(targets)} channel aktif.",
        }
