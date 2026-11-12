"""
User handlers for MEDIAPATNER BOT.
Implements Welcome message, poster submission prompts, link detection,
public embed scraping, direct forward parsing, KEEP queue storage,
and official notification dispatches.
"""

import json
import logging
from typing import Optional
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    MessageOriginChannel,
    MessageOriginChat,
)
from aiogram.filters import CommandStart, Command

from mediapatner.config import Settings
from mediapatner.database.repository import Repository
from mediapatner.database.models import PosterRecord
from mediapatner.services.scheduler_service import (
    calculate_next_wib_slot,
    get_current_wib,
)
from mediapatner.services.poster_processor import (
    PosterProcessor,
    extract_telegram_link_info,
    scrape_telegram_embed,
)
from mediapatner.services.notification_service import NotificationService
from mediapatner.services.report_service import ReportService
from mediapatner.services.operational_service import check_submission_allowed
from mediapatner.keyboards.user_kb import (
    get_start_keyboard,
    get_submission_menu_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="user_router")

WELCOME_TEXT = (
    "𓄲 WELCOME, MEDIA PARTNER! 𓈒\n\n"
    "Hello! Selamat datang di layanan Media Partner ASCHEN EVENT ORGANIZER.\n\n"
    "Terima kasih telah memilih ASCHEN sebagai partner kolaborasi Anda. "
    "Senang sekali bisa menjalin hubungan kerja sama bersama kalian!\n\n"
    "Melalui bot ini, Anda dapat mengakses layanan Media Partner, "
    "mengirimkan kebutuhan publikasi, serta memperoleh informasi terkait kerja sama dengan ASCHEN.\n\n"
    "Silakan gunakan tombol menu yang tersedia untuk melanjutkan proses. "
    "Pastikan mengikuti setiap instruksi agar pengajuan dapat diproses dengan baik.\n\n"
    "Have a wonderful collaboration with us!\n\n"
    "𓄲 ASCHEN EVENT ORGANIZER\n"
    "Elegant Collaboration, Memorable Celebration."
)

SUBMISSION_PROMPT_TEXT = (
    "𓄲 POSTER SUBMISSION 𓈒\n\n"
    "Silakan teruskan (*forward*) langsung pesan poster dari Channel Telegram yang ingin Anda ajukan "
    "untuk dipublikasikan melalui Channel ASCHEN EVENT ORGANIZER.\n\n"
    "Pastikan postingan berisi poster dan caption yang ingin dipublikasikan.\n\n"
    "➤ *Teruskan (forward) poster Anda sekarang!*"
)


@router.message(CommandStart())
async def handle_start(
    message: Message,
    repository: Repository,
    settings: Settings,
):
    """
    Section 2: Welcome Message — Start Menu
    """
    user = message.from_user
    if user:
        await repository.upsert_user(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )

    await message.answer(
        text=WELCOME_TEXT,
        reply_markup=get_start_keyboard(),
    )


@router.callback_query(F.data == "cmd_submit_poster")
async def handle_submit_poster_callback(
    callback: CallbackQuery,
    repository: Repository,
):
    """
    Section 2.B: Fungsi Tombol Mengirim Poster.
    Checks operational schedule (Senin–Sabtu >= 06.00 WIB, Minggu TUTUP).
    """
    op_config = await repository.get_operational_config()
    is_allowed, reason, op_msg = check_submission_allowed(op_config)
    if not is_allowed:
        await callback.message.edit_text(
            text=op_msg,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard(),
        )
        await callback.answer("Pengajuan sedang di luar jam operasional.", show_alert=True)
        return

    await callback.message.edit_text(
        text=SUBMISSION_PROMPT_TEXT,
        parse_mode="Markdown",
        reply_markup=get_submission_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "cmd_main_menu")
async def handle_main_menu_callback(callback: CallbackQuery):
    """
    Section 2.C: Tombol Menu Utama mengembalikan pengguna ke pesan Welcome.
    """
    await callback.message.edit_text(
        text=WELCOME_TEXT,
        reply_markup=get_start_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
@router.callback_query(F.data == "noop_permanent_info")
async def handle_noop_callback(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("sched_info:"))
async def handle_sched_info_callback(callback: CallbackQuery):
    """Provides schedule information popup when schedule hour buttons are pressed."""
    slot = callback.data.split(":")[1]
    if slot == "09":
        await callback.answer(
            "🌅 Sesi Pagi: Setiap Selasa & Kamis pukul 09.00 WIB\nPoster otomatis masuk slot terdekat.",
            show_alert=True,
        )
    elif slot == "12":
        await callback.answer(
            "☀️ Sesi Siang: Setiap Rabu & Jumat pukul 12.00 WIB\nPoster otomatis masuk slot terdekat.",
            show_alert=True,
        )
    elif slot == "20":
        await callback.answer(
            "🌙 Sesi Malam: Setiap Sabtu pukul 20.00 WIB\nPoster otomatis masuk slot terdekat.",
            show_alert=True,
        )
    else:
        await callback.answer()


# ------------------ POSTER LINK & MEDIA INGESTION ------------------


@router.message(F.text | F.photo | F.video | F.forward_origin | F.forward_from_chat)
async def handle_poster_submission(
    message: Message,
    repository: Repository,
    processor: PosterProcessor,
    notification_service: NotificationService,
    settings: Settings,
    report_service: Optional[ReportService] = None,
):
    """
    Section 3, 4, 6:
    Receives Telegram link or forwarded post/media.
    Enforces operational hours, auto-detects, validates, checks duplicates,
    calculates schedule slot, stores to KEEP queue, dispatches interactive report
    to configured report chat, and sends notifications.
    """
    user = message.from_user
    if not user:
        return

    # Update user record
    await repository.upsert_user(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )

    # Ignore command messages
    if message.text and message.text.startswith("/"):
        return

    # Check if user sent the admin password directly (e.g. following /admin prompt)
    if message.text and message.text.strip() == settings.admin_password:
        from mediapatner.handlers.admin import AUTHENTICATED_ADMINS, render_overview_text
        from mediapatner.keyboards.admin_kb import get_admin_main_keyboard
        AUTHENTICATED_ADMINS.add(user.id)
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(
            "🔓 *Autentikasi Berhasil!*\nSelamat datang di Dashboard Administrator ASCHEN.",
            parse_mode="Markdown",
        )
        text = await render_overview_text(repository, settings)
        await message.answer(
            text=text,
            parse_mode="Markdown",
            reply_markup=get_admin_main_keyboard(),
        )
        return

    # Operational Hours Enforcement (Senin–Sabtu >= 06.00 WIB, Minggu TUTUP)
    op_config = await repository.get_operational_config()
    is_allowed, op_reason, op_msg = check_submission_allowed(op_config)
    if not is_allowed:
        await message.reply(
            op_msg,
            parse_mode="Markdown",
            reply_markup=get_start_keyboard(),
        )
        await repository.log_activity(
            action="SUBMISSION_BLOCKED_HOURS",
            user_id=user.id,
            details=f"Reason: {op_reason}",
        )
        return

    source_link = None
    source_chat_id = None
    source_message_id = None
    media_type = None
    file_id = None
    caption = None
    raw_data = {}

    is_forwarded = bool(message.forward_origin or message.forward_from_chat)

    # PRIORITY 1: Message forwarded directly from a Channel or Chat
    if is_forwarded:
        # Save direct message coordinates so bot can natively forward this exact message
        raw_data["direct_chat_id"] = message.chat.id
        raw_data["direct_message_id"] = message.message_id

        # Extract origin channel metadata
        if message.forward_origin:
            if isinstance(message.forward_origin, MessageOriginChannel):
                origin_chat = message.forward_origin.chat
                source_chat_id = f"@{origin_chat.username}" if origin_chat.username else str(origin_chat.id)
                source_message_id = message.forward_origin.message_id
                raw_data["channel_title"] = origin_chat.title
                if origin_chat.username and source_message_id:
                    source_link = f"https://t.me/{origin_chat.username}/{source_message_id}"
            elif isinstance(message.forward_origin, MessageOriginChat):
                origin_chat = message.forward_origin.sender_chat
                source_chat_id = f"@{origin_chat.username}" if origin_chat.username else str(origin_chat.id)
                raw_data["channel_title"] = origin_chat.title
        elif message.forward_from_chat:
            source_chat_id = (
                f"@{message.forward_from_chat.username}"
                if message.forward_from_chat.username
                else str(message.forward_from_chat.id)
            )
            source_message_id = message.forward_from_message_id
            raw_data["channel_title"] = message.forward_from_chat.title
            if message.forward_from_chat.username and source_message_id:
                source_link = f"https://t.me/{message.forward_from_chat.username}/{source_message_id}"

        # Extract media & EXACT original caption (zero modification)
        if message.photo:
            media_type = "photo"
            file_id = message.photo[-1].file_id
            caption = message.caption or ""
        elif message.video:
            media_type = "video"
            file_id = message.video.file_id
            caption = message.caption or ""
        elif message.document:
            media_type = "document"
            file_id = message.document.file_id
            caption = message.caption or ""
        else:
            media_type = "text"
            caption = message.text or ""

        # Duplicate check
        duplicate = await processor.check_duplicate(
            source_link=source_link,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
        )
        if duplicate:
            await message.reply(
                "𓄲 MEDIAPATNER — DUPLICATE NOTICE\n\n"
                "Poster dari channel ini sudah pernah diajukan sebelumnya dan saat ini "
                f"berada dalam status *{duplicate.status}* dengan jadwal {duplicate.slot_day}, {duplicate.slot_date} ({duplicate.slot_time} WIB).\n\n"
                "Sistem mencegah pengiriman ganda untuk menjaga kerapian Channel.",
                parse_mode="Markdown",
            )
            return

    # PRIORITY 2: Telegram Post Link provided in text (without forwarding)
    else:
        text_content = message.text or message.caption or ""
        link_info = extract_telegram_link_info(text_content)

        if link_info:
            source_link = link_info["raw_url"]
            source_chat_id = link_info["channel"]
            source_message_id = link_info["message_id"]

            # Duplicate Prevention Check
            duplicate = await processor.check_duplicate(
                source_link=source_link,
                source_chat_id=source_chat_id,
                source_message_id=source_message_id,
            )
            if duplicate:
                await message.reply(
                    "𓄲 MEDIAPATNER — DUPLICATE NOTICE\n\n"
                    "Poster dari link ini sudah pernah diajukan sebelumnya dan saat ini "
                    f"berada dalam status *{duplicate.status}* dengan jadwal {duplicate.slot_day}, {duplicate.slot_date} ({duplicate.slot_time} WIB).\n\n"
                    "Sistem mencegah pengiriman ganda untuk menjaga kerapian Channel.",
                    parse_mode="Markdown",
                )
                return

            # Scrape public embed to verify post and extract media
            if not link_info["is_private_c"]:
                embed_info = await scrape_telegram_embed(
                    username=link_info["username"],
                    message_id=link_info["message_id"],
                )
                if embed_info:
                    media_type = embed_info["media_type"]
                    caption = embed_info["caption"]
                    raw_data = {
                        "photo_url": embed_info.get("photo_url"),
                        "video_url": embed_info.get("video_url"),
                        "channel_title": embed_info.get("channel_title"),
                    }
                else:
                    logger.warning(f"Could not scrape embed for {source_link}")
                    await message.reply(
                        "𓄲 MEDIAPATNER — LINK NOT ACCESSIBLE\n\n"
                        "Link Telegram yang Anda berikan tidak dapat diakses secara publik oleh sistem.\n\n"
                        "➤ *Saran Terbaik:* Teruskan (*forward*) langsung pesan poster dari channel Anda ke bot ini agar sistem dapat menyebarkannya dengan tanda forward dari channel dan teks 100% sama.",
                        parse_mode="Markdown",
                    )
                    await notification_service.send_channel_post_failure_report(
                        sender_name=user.full_name,
                        source_link=source_link,
                        reason="Link tidak dapat diakses / postingan privat",
                    )
                    return
            else:
                await message.reply(
                    "𓄲 MEDIAPATNER — LINK NOTICE\n\n"
                    "Link format `/c/` merupakan tautan privat internal.\n\n"
                    "Silakan *teruskan (forward) langsung pesan poster* dari channel ke bot ini agar poster dapat diteruskan secara utuh.",
                    parse_mode="Markdown",
                )
                return

        # PRIORITY 3: Direct Media Uploaded (without forward or link)
        elif message.photo or message.video or message.document:
            raw_data["direct_chat_id"] = message.chat.id
            raw_data["direct_message_id"] = message.message_id
            if message.photo:
                media_type = "photo"
                file_id = message.photo[-1].file_id
                caption = message.caption or ""
            elif message.video:
                media_type = "video"
                file_id = message.video.file_id
                caption = message.caption or ""
            elif message.document:
                media_type = "document"
                file_id = message.document.file_id
                caption = message.caption or ""
        else:
            # Plain invalid text
            await message.reply(
                "𓄲 POSTER SUBMISSION 𓈒\n\n"
                "Format yang Anda kirimkan belum sesuai.\n\n"
                "Silakan *teruskan (forward) langsung* pesan poster dari Channel Telegram Anda ke bot ini.",
                parse_mode="Markdown",
                reply_markup=get_submission_menu_keyboard(),
            )
            return

    # ------------------ AUTO SCHEDULE & KEEP QUEUE ------------------
    slot_dt, slot_day, slot_date, slot_time = calculate_next_wib_slot()
    slot_iso = slot_dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Create Poster Record
    poster_record = PosterRecord(
        id=None,
        sender_id=user.id,
        sender_name=user.full_name,
        sender_username=user.username,
        source_link=source_link,
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        media_type=media_type,
        file_id=file_id,
        caption=caption,
        raw_data=json.dumps(raw_data) if raw_data else None,
        status="KEEP",
        scheduled_slot=slot_iso,
        slot_day=slot_day,
        slot_date=slot_date,
        slot_time=slot_time,
        retry_count=0,
    )

    poster_id = await repository.create_poster(poster_record)
    poster_record.id = poster_id

    # Update user submission count
    await repository.increment_user_submissions(user.id)

    # Log activity
    await repository.log_activity(
        action="KEEP_QUEUED",
        poster_id=poster_id,
        user_id=user.id,
        details=f"Slot: {slot_day}, {slot_date} {slot_time} WIB",
    )

    # 1. Send Section 7 Keep Success notification to user
    await notification_service.send_keep_success_to_user(
        user_id=user.id,
        slot_day=slot_day,
        slot_date=slot_date,
        slot_time=slot_time,
    )

    # 2. Send Section 9.A Incoming Poster Report to Permanent Notification Channel
    await notification_service.send_channel_new_incoming_report(poster_record)

    # 3. Send Section 4 & 5 Interactive Request Report to Configured Report Chat
    if report_service:
        await report_service.send_incoming_poster_report(poster_record)

    logger.info(
        f"Poster #{poster_id} successfully queued for {user.full_name} | "
        f"Slot: {slot_day}, {slot_date} {slot_time} WIB"
    )
