"""
Publisher service for MEDIAPATNER BOT.
Dispatches posters to the main channel (@ASCHENEO).
Preserves native channel forward attribution and exact original text without differences.
"""

from typing import Optional, Tuple, Dict, Any
from aiogram import Bot
from aiogram.types import URLInputFile
import logging
import asyncio
import time
from datetime import datetime
from mediapatner.config import Settings
from mediapatner.database.repository import Repository
from mediapatner.database.models import PosterRecord
from mediapatner.services.notification_service import NotificationService
from mediapatner.services.scheduler_service import format_indonesian_date, format_indonesian_time, get_current_wib

logger = logging.getLogger(__name__)


class PublisherService:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        repository: Repository,
        notification_service: NotificationService,
        multi_bot_service: Optional[Any] = None,
    ):
        self.bot = bot
        self.settings = settings
        self.repository = repository
        self.notification_service = notification_service
        self.multi_bot_service = multi_bot_service

    async def publish_poster(
        self,
        poster: PosterRecord,
        target_destination: Optional[str] = None,
    ) -> bool:
        """
        Publishes a poster.
        If multi_bot_service is configured, routes via Section D & Target Selection:
        Distributes to chosen channels (Channel Utama, Channel Sebar, Keduanya, atau Semua Saluran).
        """
        if self.multi_bot_service:
            success, published_msg_id, message = await self.multi_bot_service.dispatch_poster_publication(
                poster, target_destination=target_destination
            )
            now_wib = get_current_wib()
            current_date_str = format_indonesian_date(now_wib)
            current_time_str = format_indonesian_time(now_wib)

            if success and published_msg_id is not None:
                await self.repository.mark_published(poster.id, published_message_id=published_msg_id)
                await self.repository.log_activity(
                    action="PUBLISHED",
                    poster_id=poster.id,
                    user_id=poster.sender_id,
                    details=message,
                )
                await self.notification_service.send_post_success_to_user(poster.sender_id)
                await self.notification_service.send_channel_post_success_report(
                    sender_name=poster.sender_name,
                    slot_date=current_date_str,
                    slot_time=current_time_str,
                )
                return True
            else:
                if "NONAKTIF (OFF)" in message or "blocked" in message:
                    logger.info(f"Poster #{poster.id} halted: {message}")
                    return False

                err_msg = message
                logger.error(f"Publication failed for poster #{poster.id}: {err_msg}")
                if poster.retry_count + 1 >= self.settings.retry_max_attempts:
                    await self.repository.mark_failed(poster.id, err_msg, increment_retry=True)
                    await self.repository.log_activity(
                        action="PUBLISH_FAILED",
                        poster_id=poster.id,
                        user_id=poster.sender_id,
                        details=f"Permanent failure after {poster.retry_count + 1} attempts: {err_msg}",
                    )
                    await self.notification_service.send_channel_post_failure_report(
                        sender_name=poster.sender_name,
                        source_link=poster.source_link,
                        reason=err_msg,
                    )
                else:
                    await self.repository.mark_failed(poster.id, err_msg, increment_retry=True)
                return False
        main_channel = self.settings.channel_username
        auto_forward_enabled = await self.repository.is_auto_forward_enabled()
        raw_data = poster.get_parsed_raw()

        published_msg_id: Optional[int] = None
        publish_error: Optional[Exception] = None

        logger.info(
            f"Publishing poster #{poster.id} to {main_channel}. Auto-forward: {auto_forward_enabled}"
        )

        direct_chat_id = raw_data.get("direct_chat_id")
        direct_message_id = raw_data.get("direct_message_id")

        # Attempt 1: Forward the exact message that was forwarded to the bot in private chat
        # When a bot forwards a message that was forwarded from a channel, Telegram displays
        # "Forwarded from [Channel Name]" and preserves 100% of the exact text and media!
        if auto_forward_enabled and direct_chat_id and direct_message_id:
            try:
                sent = await self.bot.forward_message(
                    chat_id=main_channel,
                    from_chat_id=direct_chat_id,
                    message_id=direct_message_id,
                )
                published_msg_id = sent.message_id
                logger.info(
                    f"Native forward from direct chat succeeded for #{poster.id}. Message ID: {published_msg_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Native forward from direct chat failed for #{poster.id}: {e}"
                )
                publish_error = e

        # Attempt 2: If direct message is not available, try forwarding directly from source channel
        if (
            published_msg_id is None
            and auto_forward_enabled
            and poster.source_chat_id
            and poster.source_message_id
        ):
            try:
                sent = await self.bot.forward_message(
                    chat_id=main_channel,
                    from_chat_id=poster.source_chat_id,
                    message_id=poster.source_message_id,
                )
                published_msg_id = sent.message_id
                logger.info(
                    f"Native forward from source channel succeeded for #{poster.id}. Message ID: {published_msg_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Native forward from source channel failed for #{poster.id}: {e}"
                )
                publish_error = e

        # Attempt 3: Copy message (preserves exact text, entities, formatting, media without difference)
        if published_msg_id is None and direct_chat_id and direct_message_id:
            try:
                sent = await self.bot.copy_message(
                    chat_id=main_channel,
                    from_chat_id=direct_chat_id,
                    message_id=direct_message_id,
                )
                published_msg_id = sent.message_id
                logger.info(
                    f"Copy message succeeded for #{poster.id}. Message ID: {published_msg_id}"
                )
            except Exception as e:
                logger.warning(f"Copy message failed for #{poster.id}: {e}")
                publish_error = e

        # Attempt 4: Direct media send with EXACT original caption (zero modification or extra text)
        if published_msg_id is None:
            try:
                # The text must be EXACTLY identical to the original - no added footer or attribution
                caption = poster.caption or None
                photo_url = raw_data.get("photo_url")
                video_url = raw_data.get("video_url")

                if poster.media_type == "photo" or photo_url:
                    photo_source = poster.file_id or (URLInputFile(photo_url) if photo_url else None)
                    if photo_source:
                        sent = await self.bot.send_photo(
                            chat_id=main_channel,
                            photo=photo_source,
                            caption=caption,
                        )
                        published_msg_id = sent.message_id
                    else:
                        raise ValueError("No photo file_id or URL available for photo poster.")

                elif poster.media_type == "video" or video_url:
                    video_source = poster.file_id or (URLInputFile(video_url) if video_url else None)
                    if video_source:
                        sent = await self.bot.send_video(
                            chat_id=main_channel,
                            video=video_source,
                            caption=caption,
                        )
                        published_msg_id = sent.message_id
                    else:
                        raise ValueError("No video file_id or URL available for video poster.")

                elif poster.media_type == "document" and poster.file_id:
                    sent = await self.bot.send_document(
                        chat_id=main_channel,
                        document=poster.file_id,
                        caption=caption,
                    )
                    published_msg_id = sent.message_id

                else:
                    # Text post
                    text_content = caption or "Media Partner Poster"
                    sent = await self.bot.send_message(
                        chat_id=main_channel,
                        text=text_content,
                    )
                    published_msg_id = sent.message_id

            except Exception as e:
                logger.error(f"Direct media send failed for poster #{poster.id}: {e}", exc_info=True)
                publish_error = e

        # Outcome handling
        now_wib = get_current_wib()
        current_date_str = format_indonesian_date(now_wib)
        current_time_str = format_indonesian_time(now_wib)

        if published_msg_id is not None:
            # Succeeded!
            await self.repository.mark_published(poster.id, published_message_id=published_msg_id)
            await self.repository.log_activity(
                action="PUBLISHED",
                poster_id=poster.id,
                user_id=poster.sender_id,
                details=f"Published to {main_channel} as msg_id {published_msg_id}",
            )

            # 1. Send Section 8 Post Success notification to user
            await self.notification_service.send_post_success_to_user(poster.sender_id)

            # 2. Send Section 9.B Posted Successfully report to notification channel
            await self.notification_service.send_channel_post_success_report(
                sender_name=poster.sender_name,
                slot_date=current_date_str,
                slot_time=current_time_str,
            )
            return True
        else:
            # Failed!
            err_msg = str(publish_error) if publish_error else "Unknown publication error"
            logger.error(f"Publication permanently failed for poster #{poster.id}: {err_msg}")

            if poster.retry_count + 1 >= self.settings.retry_max_attempts:
                # Mark as FAILED and notify
                await self.repository.mark_failed(poster.id, err_msg, increment_retry=True)
                await self.repository.log_activity(
                    action="PUBLISH_FAILED",
                    poster_id=poster.id,
                    user_id=poster.sender_id,
                    details=f"Permanent failure after {poster.retry_count + 1} attempts: {err_msg}",
                )

                # Send Section 9.C Post Failure report to notification channel
                await self.notification_service.send_channel_post_failure_report(
                    sender_name=poster.sender_name,
                    source_link=poster.source_link,
                    reason=err_msg,
                )
            else:
                # Still has retries left, reschedule for next tick
                await self.repository.mark_failed(poster.id, err_msg, increment_retry=True)
                logger.info(
                    f"Poster #{poster.id} retry {poster.retry_count + 1}/{self.settings.retry_max_attempts}"
                )

            return False

    async def ping_channel(self) -> Dict[str, Any]:
        """
        Pings the main broadcast channel (@ASCHENEO).
        Checks bot membership, administrator status, posting rights,
        and round-trip latency to Telegram API.
        """
        main_channel = self.settings.channel_username
        start_time = time.perf_counter()

        try:
            # 1. Probe chat info
            chat = await self.bot.get_chat(main_channel)
            chat_title = chat.title or main_channel

            # 2. Probe bot permissions
            bot_me = await self.bot.get_me()
            member = await self.bot.get_chat_member(main_channel, bot_me.id)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

            is_admin = member.status in ("administrator", "creator")
            can_post = (
                getattr(member, "can_post_messages", False)
                or member.status == "creator"
                or (is_admin and getattr(member, "can_post_messages", None) is not False)
            )
            can_edit = (
                getattr(member, "can_edit_messages", False)
                or member.status == "creator"
            )

            status_str = "SEHAT & SIAP PUBLIKASI ✅" if (is_admin and can_post) else "PERHATIAN: CEK IZIN BOT ⚠️"

            return {
                "success": True,
                "channel": main_channel,
                "chat_title": chat_title,
                "bot_id": bot_me.id,
                "bot_username": f"@{bot_me.username}",
                "member_status": member.status,
                "is_admin": is_admin,
                "can_post": can_post,
                "can_edit": can_edit,
                "latency_ms": elapsed_ms,
                "health_status": status_str,
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"Ping to broadcast channel {main_channel} failed: {e}")
            return {
                "success": False,
                "channel": main_channel,
                "latency_ms": elapsed_ms,
                "error": str(e),
                "health_status": "TERPUTUS / GAGAL ❌",
            }

    async def publish_poster_early(
        self, poster: PosterRecord, admin_name: str, admin_id: int
    ) -> Tuple[bool, str]:
        """
        Publishes a poster immediately (Sebar Duluan) bypassing the scheduled cron queue.
        """
        if poster.status == "PUBLISHED":
            return False, f"Poster #{poster.id} sudah pernah diterbitkan sebelumnya!"

        await self.repository.mark_publishing(poster.id)
        success = await self.publish_poster(poster)
        if success:
            await self.repository.log_activity(
                action="EARLY_PUBLISH",
                poster_id=poster.id,
                user_id=admin_id,
                details=f"Sebar duluan dipublikasikan oleh Admin {admin_name} ({admin_id})",
            )
            return True, f"Poster #{poster.id} berhasil disebar duluan ke {self.settings.channel_username}!"
        else:
            return False, f"Gagal menyebarkan poster #{poster.id}. Silakan periksa izin bot di channel {self.settings.channel_username}."
