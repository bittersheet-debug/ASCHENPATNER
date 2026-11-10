"""
Notification service for MEDIAPATNER BOT.
Dispatches official formatted notifications to senders and the permanent notification channel.
Channel ID: -1004479248551 (PERMANENT).
"""

from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from mediapatner.config import Settings
from mediapatner.database.models import PosterRecord

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, bot: Bot, settings: Settings):
        self.bot = bot
        self.settings = settings
        # Permanent channel ID strictly locked
        self.notification_channel_id = self.settings.notification_channel_id

    # ------------------ SENDER NOTIFICATIONS ------------------

    async def send_keep_success_to_user(
        self, user_id: int, slot_day: str, slot_date: str, slot_time: str
    ) -> bool:
        """
        Sends Section 7 KEEP SUCCESS notification to the poster submitter.
        """
        text = (
            "𓄲 MEDIAPATNER — KEEP SUCCESS!\n\n"
            "Poster kamu berhasil diterima dan disimpan oleh sistem.\n\n"
            "➤ Status: KEEP\n"
            f"➤ Jadwal: {slot_day}\n"
            f"➤ Tanggal: {slot_date}\n"
            f"➤ Waktu: {slot_time} WIB\n\n"
            "Mohon menunggu jadwal publikasi.\n\n"
            "Terima kasih telah menjadi Media Partner kami!"
        )
        try:
            await self.bot.send_message(chat_id=user_id, text=text)
            return True
        except Exception as e:
            logger.warning(f"Failed to send keep success notification to user {user_id}: {e}")
            return False

    async def send_post_success_to_user(self, user_id: int) -> bool:
        """
        Sends Section 8 POST SUCCESS notification to the poster submitter
        with inline button linking to the main channel.
        """
        text = (
            "𓄲 MEDIAPATNER — POST SUCCESS!\n\n"
            "Yeay! Poster kamu sudah berhasil dipublikasikan oleh sistem.\n\n"
            "➤ Status: Successfully Posted\n"
            f"➤ Channel: {self.settings.channel_username}\n\n"
            "Silakan lihat poster kamu di Channel Utama kami!\n\n"
            "Terima kasih telah menjadi Media Partner ASCHEN."
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"LIHAT CHANNEL {self.settings.channel_username}",
                        url=self.settings.channel_link,
                    )
                ]
            ]
        )
        try:
            await self.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)
            return True
        except Exception as e:
            logger.warning(f"Failed to send post success notification to user {user_id}: {e}")
            return False

    # ------------------ PERMANENT NOTIFICATION CHANNEL (-1004479248551) ------------------

    async def send_channel_new_incoming_report(self, poster: PosterRecord) -> bool:
        """
        Section 9.A: Laporan Poster Masuk ke Channel Notifikasi Permanen.
        """
        username_str = f"@{poster.sender_username}" if poster.sender_username else "(Tidak ada username)"
        link_str = poster.source_link if poster.source_link else "(Direct Forward / Upload)"

        text = (
            "𓄲 MEDIAPATNER — NEW POSTER INCOMING!\n\n"
            "Seseorang baru saja mengirimkan poster Media Partner.\n\n"
            f"➤ Pengirim: {poster.sender_name}\n"
            f"➤ Username: {username_str}\n"
            f"➤ Link Poster: {link_str}\n"
            "➤ Status: KEEP QUEUE\n"
            f"➤ Jadwal Posting: {poster.slot_day}, {poster.slot_date}\n"
            f"➤ Waktu Posting: {poster.slot_time} WIB\n\n"
            "© MEDIAPATNER SYSTEM"
        )
        try:
            await self.bot.send_message(chat_id=self.notification_channel_id, text=text)
            return True
        except Exception as e:
            logger.error(
                f"Failed to send incoming report to Permanent Notification Channel ({self.notification_channel_id}): {e}"
            )
            return False

    async def send_channel_post_success_report(
        self, sender_name: str, slot_date: str, slot_time: str
    ) -> bool:
        """
        Section 9.B: Laporan Poster Berhasil ke Channel Notifikasi Permanen.
        """
        text = (
            "𓄲 MEDIAPATNER — POSTED SUCCESSFULLY!\n\n"
            "Poster berhasil diterbitkan ke Channel Utama.\n\n"
            f"➤ Pengirim: {sender_name}\n"
            f"➤ Channel: {self.settings.channel_username}\n"
            "➤ Status: PUBLISHED\n"
            f"➤ Tanggal: {slot_date}\n"
            f"➤ Waktu: {slot_time} WIB"
        )
        try:
            await self.bot.send_message(chat_id=self.notification_channel_id, text=text)
            return True
        except Exception as e:
            logger.error(
                f"Failed to send success report to Permanent Notification Channel ({self.notification_channel_id}): {e}"
            )
            return False

    async def send_channel_post_failure_report(
        self, sender_name: str, source_link: Optional[str], reason: str
    ) -> bool:
        """
        Section 9.C: Laporan Kegagalan ke Channel Notifikasi Permanen.
        """
        link_str = source_link if source_link else "(Direct Upload / Forward)"
        text = (
            "𓄲 MEDIAPATNER — POST FAILED!\n\n"
            "Poster gagal diproses atau dipublikasikan.\n\n"
            f"➤ Pengirim: {sender_name}\n"
            f"➤ Link: {link_str}\n"
            "➤ Status: FAILED\n"
            f"➤ Penyebab: {reason}"
        )
        try:
            await self.bot.send_message(chat_id=self.notification_channel_id, text=text)
            return True
        except Exception as e:
            logger.error(
                f"Failed to send failure report to Permanent Notification Channel ({self.notification_channel_id}): {e}"
            )
            return False
