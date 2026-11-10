"""
Report Service for MEDIAPATNER BOT.
Dispatches incoming poster requests to the configured report chat (Channel/Group/Private),
attaches original media, provides interactive action buttons (Terima, Tolak, Selesai),
enforces anti-double-processing, and notifies the submitting Media Partner.
"""

import json
import logging
from typing import Optional
from datetime import datetime
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from mediapatner.config import Settings
from mediapatner.database.repository import Repository
from mediapatner.database.models import PosterRecord, PosterReportRecord
from mediapatner.services.scheduler_service import get_current_wib

logger = logging.getLogger(__name__)


def get_report_action_keyboard(report_id: int) -> InlineKeyboardMarkup:
    """Action buttons attached to the incoming poster report."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Terima Pengajuan",
                    callback_data=f"rpt_act:{report_id}:accept",
                ),
                InlineKeyboardButton(
                    text="❌ Tolak Pengajuan",
                    callback_data=f"rpt_act:{report_id}:reject",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📌 Tandai Selesai",
                    callback_data=f"rpt_act:{report_id}:complete",
                ),
            ],
        ]
    )


class ReportService:
    def __init__(self, bot: Bot, repository: Repository, settings: Settings):
        self.bot = bot
        self.repository = repository
        self.settings = settings

    async def send_incoming_poster_report(self, poster: PosterRecord) -> Optional[int]:
        """
        Dispatches Section 3 & 4 incoming request report to the configured report chat.
        Attaches/forwards original media and returns the report record ID.
        """
        report_chat_id = await self.repository.get_report_chat_id()
        if not report_chat_id:
            report_chat_id = self.settings.notification_channel_id

        # Determine institution name from raw_data channel_title if available
        parsed_raw = poster.get_parsed_raw()
        institution_name = parsed_raw.get("channel_title") or "-"

        now_wib = get_current_wib()
        date_str = now_wib.strftime("%d %B %Y")
        time_str = now_wib.strftime("%H.%M")

        # Create report record in database
        report = PosterReportRecord(
            id=None,
            poster_id=poster.id,
            report_chat_id=str(report_chat_id),
            report_message_id=None,
            sender_id=poster.sender_id,
            sender_name=poster.sender_name,
            sender_username=poster.sender_username,
            institution_name=institution_name,
            status="Menunggu Diproses",
        )
        report_id = await self.repository.create_poster_report(report)

        username_display = f"@{poster.sender_username}" if poster.sender_username else "-"
        text = (
            "𓄲 LAPORAN REQUEST POSTER 𓈒\n\n"
            f"➤ *Nama Media Partner:* {poster.sender_name}\n"
            f"➤ *Username:* {username_display}\n"
            f"➤ *Nama Instansi:* {institution_name}\n"
            f"➤ *Tanggal Pengajuan:* {date_str}\n"
            f"➤ *Waktu Pengajuan:* {time_str} WIB\n"
            "➤ *Status:* ⏳ Menunggu Diproses\n"
            f"➤ *ID Pengajuan:* `#{report_id}` (Poster `#{poster.id}`)\n"
            f"➤ *Slot Direncanakan:* {poster.slot_day}, {poster.slot_date} {poster.slot_time} WIB\n\n"
            "Silakan gunakan tombol di bawah untuk memproses pengajuan:"
        )

        # 1. Send the report message with action buttons
        try:
            sent_msg = await self.bot.send_message(
                chat_id=report_chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=get_report_action_keyboard(report_id),
            )
            await self.repository.update_report_message_id(report_id, sent_msg.message_id)
        except Exception as e:
            logger.error(f"Failed to send poster report to {report_chat_id}: {e}")
            # Fallback to permanent channel if custom chat failed
            if str(report_chat_id) != str(self.settings.notification_channel_id):
                try:
                    sent_msg = await self.bot.send_message(
                        chat_id=self.settings.notification_channel_id,
                        text=f"⚠️ [Fallback Report] Chat utama error: {e}\n\n" + text,
                        parse_mode="Markdown",
                        reply_markup=get_report_action_keyboard(report_id),
                    )
                    await self.repository.update_report_message_id(report_id, sent_msg.message_id)
                except Exception as fb_err:
                    logger.error(f"Fallback report also failed: {fb_err}")

        # 2. Forward or send the original poster media right after report
        try:
            if "direct_chat_id" in parsed_raw and "direct_message_id" in parsed_raw:
                await self.bot.forward_message(
                    chat_id=report_chat_id,
                    from_chat_id=parsed_raw["direct_chat_id"],
                    message_id=parsed_raw["direct_message_id"],
                )
            elif poster.file_id:
                caption_preview = f"📎 Media Pengajuan #{report_id}"
                if poster.media_type == "photo":
                    await self.bot.send_photo(
                        chat_id=report_chat_id, photo=poster.file_id, caption=caption_preview
                    )
                elif poster.media_type == "video":
                    await self.bot.send_video(
                        chat_id=report_chat_id, video=poster.file_id, caption=caption_preview
                    )
                elif poster.media_type == "document":
                    await self.bot.send_document(
                        chat_id=report_chat_id, document=poster.file_id, caption=caption_preview
                    )
        except Exception as media_err:
            logger.warning(f"Could not forward media to report chat: {media_err}")

        return report_id

    async def handle_action(
        self, callback: CallbackQuery, report_id: int, action: str
    ) -> None:
        """
        Handles interactive callbacks from report action buttons.
        Guarantees anti-double-processing and dispatches user notifications.
        """
        admin_user = callback.from_user
        report = await self.repository.get_poster_report(report_id)
        if not report:
            await callback.answer("Data laporan tidak ditemukan.", show_alert=True)
            return

        # Anti-double processing check
        if report.status != "Menunggu Diproses":
            await callback.answer(
                f"⚠️ Pengajuan #{report_id} SUDAH diproses sebelumnya oleh {report.processed_by_name} "
                f"dengan status: {report.status}!",
                show_alert=True,
            )
            return

        poster = await self.repository.get_poster(report.poster_id)

        # Status mapping
        status_text_map = {
            "accept": "✅ Diterima",
            "reject": "❌ Ditolak",
            "complete": "📌 Selesai",
        }
        new_status = status_text_map.get(action, "Menunggu Diproses")

        # Atomic status update
        success = await self.repository.update_poster_report_status(
            report_id=report_id,
            status=new_status,
            admin_id=admin_user.id,
            admin_name=admin_user.full_name,
            action_note=f"Action: {action} by {admin_user.full_name}",
        )
        if not success:
            await callback.answer(
                "⚠️ Gagal memperbarui status. Pengajuan mungkin baru saja diproses oleh admin lain.",
                show_alert=True,
            )
            return

        # If rejected, cancel the poster in database queue
        if action == "reject" and poster:
            await self.repository.cancel_poster(poster.id)
            await self.repository.log_activity(
                action="REQUEST_REJECTED",
                poster_id=poster.id,
                user_id=admin_user.id,
                details=f"Rejected by Admin {admin_user.full_name}",
            )
        elif action == "accept" and poster:
            await self.repository.log_activity(
                action="REQUEST_ACCEPTED",
                poster_id=poster.id,
                user_id=admin_user.id,
                details=f"Accepted by Admin {admin_user.full_name}",
            )
        elif action == "complete" and poster:
            await self.repository.log_activity(
                action="REQUEST_COMPLETED",
                poster_id=poster.id,
                user_id=admin_user.id,
                details=f"Marked completed by Admin {admin_user.full_name}",
            )

        # Update the report message text
        now_wib = get_current_wib()
        proc_time_str = now_wib.strftime("%d/%m/%Y %H:%M")
        username_display = f"@{report.sender_username}" if report.sender_username else "-"
        institution_display = report.institution_name or "-"

        updated_text = (
            "𓄲 LAPORAN REQUEST POSTER 𓈒\n\n"
            f"➤ *Nama Media Partner:* {report.sender_name}\n"
            f"➤ *Username:* {username_display}\n"
            f"➤ *Nama Instansi:* {institution_display}\n"
            f"➤ *ID Pengajuan:* `#{report.id}` (Poster `#{report.poster_id}`)\n"
            f"➤ *Status:* {new_status}\n"
            f"➤ *Diproses Oleh:* {admin_user.full_name} (`{admin_user.id}`)\n"
            f"➤ *Waktu Proses:* {proc_time_str} WIB\n\n"
            f"Laporan telah diperbarui dan Media Partner telah diberitahukan."
        )

        try:
            await callback.message.edit_text(
                text=updated_text,
                parse_mode="Markdown",
                reply_markup=None,  # Remove action buttons once processed
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Could not edit report message: {e}")

        await callback.answer(f"Berhasil: Pengajuan #{report_id} {new_status}!", show_alert=False)

        # Notify Media Partner sender
        try:
            if action == "accept" and poster:
                msg_user = (
                    "𓄲 STATUS MEDIA PARTNER — DITERIMA 𓈒\n\n"
                    f"Halo {report.sender_name}!\n\n"
                    "Selamat! Pengajuan poster Media Partner Anda telah *DITERIMA* oleh tim ASCHEN EVENT ORGANIZER.\n\n"
                    "Poster Anda telah masuk jadwal publikasi resmi ke Channel Utama:\n"
                    f"➤ Hari: *{poster.slot_day}*\n"
                    f"➤ Tanggal: *{poster.slot_date}*\n"
                    f"➤ Jam: *{poster.slot_time} WIB*\n"
                    f"➤ Channel: {self.settings.channel_username}\n\n"
                    "Terima kasih atas kerja samanya!\n\n"
                    "𓄲 ASCHEN EVENT ORGANIZER\n"
                    "Elegant Collaboration, Memorable Celebration."
                )
                await self.bot.send_message(chat_id=report.sender_id, text=msg_user, parse_mode="Markdown")

            elif action == "reject":
                msg_user = (
                    "𓄲 STATUS MEDIA PARTNER — DITOLAK 𓈒\n\n"
                    f"Halo {report.sender_name},\n\n"
                    "Mohon maaf, pengajuan poster Media Partner Anda *TIDAK DAPAT DITERIMA* karena belum memenuhi kriteria atau format publikasi ASCHEN EVENT ORGANIZER.\n\n"
                    "Silakan hubungi admin atau ajukan kembali poster sesuai ketentuan.\n\n"
                    "Terima kasih atas pengertian dan partisipasi Anda.\n\n"
                    "𓄲 ASCHEN EVENT ORGANIZER\n"
                    "Elegant Collaboration, Memorable Celebration."
                )
                await self.bot.send_message(chat_id=report.sender_id, text=msg_user, parse_mode="Markdown")

            elif action == "complete":
                msg_user = (
                    "𓄲 STATUS MEDIA PARTNER — SELESAI 𓈒\n\n"
                    f"Halo {report.sender_name}!\n\n"
                    "Pengajuan kolaborasi Media Partner Anda telah ditandai *SELESAI* oleh tim ASCHEN EVENT ORGANIZER.\n\n"
                    "Terima kasih banyak atas kerja sama yang luar biasa bersama ASCHEN!\n\n"
                    "𓄲 ASCHEN EVENT ORGANIZER\n"
                    "Elegant Collaboration, Memorable Celebration."
                )
                await self.bot.send_message(chat_id=report.sender_id, text=msg_user, parse_mode="Markdown")
        except Exception as notify_err:
            logger.warning(f"Could not notify user {report.sender_id}: {notify_err}")
