"""
Admin Dashboard handler for MEDIAPATNER BOT.
Implements the 8 main admin management menus:
1. Login Device (4-stage verification: Phone -> Telegram Code -> 2FA -> Success)
2. Manajemen Device Admin (Active devices list, logout, revoke access, revoke all)
3. Pemilihan Chat Tujuan Pelaporan (Permanent channel, group, private admin, custom ID, test send)
4. Pengaturan Chat & Bot (Auto forward toggle, permanent notification channel info)
5. Riwayat Request Poster & Dynamic Interactive Status (Menunggu Diproses, Diterima, Ditolak, Selesai)
6. Pengaturan Jadwal Operasional (Senin–Sabtu buka 06.00 WIB, custom jam tutup, Minggu libur)
7. Dashboard Antrean (Keep, Scheduled, Published, Failed, Rescheduling, Manual Publish)
8. Logout Sesi Admin
"""

import math
import random
import secrets
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from mediapatner.config import Settings
from mediapatner.database.repository import Repository
from mediapatner.database.models import (
    PosterRecord,
    AdminDeviceRecord,
    PosterReportRecord,
    OperationalHoursConfig,
    BroadcastBotRecord,
    ChannelSettings,
)
from mediapatner.services.publisher_service import PublisherService
from mediapatner.services.report_service import ReportService
from mediapatner.services.multi_bot_service import MultiBotService
from mediapatner.services.scheduler_service import (
    calculate_next_wib_slot,
    format_indonesian_date,
    format_indonesian_day,
    format_indonesian_time,
    get_current_wib,
    WIB_TZ,
)
from mediapatner.keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_poster_list_keyboard,
    get_poster_detail_keyboard,
    get_reschedule_options_keyboard,
    get_settings_keyboard,
    get_back_to_admin_button,
    get_login_phone_keyboard,
    get_login_otp_keyboard,
    get_login_2fa_keyboard,
    get_login_success_keyboard,
    get_device_list_keyboard,
    get_report_chat_keyboard,
    get_operational_settings_keyboard,
    get_request_list_keyboard,
    get_request_detail_keyboard,
    get_ping_channel_keyboard,
    get_channel_control_keyboard,
    get_channel_settings_keyboard,
    get_broadcast_history_keyboard,
    get_bot_management_keyboard,
    get_bot_detail_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="admin_router")

PAGE_SIZE = 6

# Session set for users who have authenticated with the admin password
AUTHENTICATED_ADMINS: set[int] = set()


class AdminAuthStates(StatesGroup):
    waiting_for_password = State()


class AdminDeviceLoginStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()


class AdminReportChatStates(StatesGroup):
    waiting_for_custom_chat_id = State()


class AdminChannelConfigStates(StatesGroup):
    waiting_for_channel_1_id = State()
    waiting_for_channel_2_id = State()


class AdminBotAddStates(StatesGroup):
    waiting_for_bot_token = State()


class AdminBroadcastSendStates(StatesGroup):
    waiting_for_broadcast_content = State()


def is_admin_check(user_id: int, settings: Settings) -> bool:
    """Checks if the user has authenticated with the admin password."""
    return user_id in AUTHENTICATED_ADMINS or settings.is_admin(user_id)


def mask_phone_number(phone: str) -> str:
    """Masks a phone number for privacy display: +62812****7890."""
    cleaned = re.sub(r"[^\d+]", "", phone)
    if len(cleaned) > 8:
        prefix = cleaned[:5]
        suffix = cleaned[-4:]
        return f"{prefix}****{suffix}"
    return cleaned[:2] + "****" + cleaned[-2:]


async def render_overview_text(repository: Repository, settings: Settings) -> str:
    stats = await repository.get_system_stats()
    auto_fwd = await repository.is_auto_forward_enabled()
    fwd_label = "AKTIF ✅" if auto_fwd else "NONAKTIF ❌"

    report_chat_id = await repository.get_report_chat_id()
    op_config = await repository.get_operational_config()
    sun_status = "TUTUP (Libur)" if op_config.sunday_closed else "BUKA"

    active_devices = await repository.get_active_devices()
    total_devices = len(active_devices)

    return (
        "𓄲 MEDIAPATNER — ADMIN DASHBOARD 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        "📊 *STATISTIK SISTEM*\n"
        f"➤ Total Link Masuk: `{stats.total_links_received}`\n"
        f"➤ Total Poster Diterima: `{stats.total_posters_accepted}`\n"
        f"➤ Total Poster KEEP: `{stats.total_posters_keep}`\n"
        f"➤ Total Poster Published: `{stats.total_posters_published}`\n"
        f"➤ Total Poster Failed: `{stats.total_posters_failed}`\n"
        f"➤ Total Pengguna: `{stats.total_users}`\n"
        f"➤ Total Aktivitas Hari Ini: `{stats.total_activity_today}`\n\n"
        "⚙️ *STATUS KONFIGURASI*\n"
        f"➤ Main Channel: `{settings.channel_username}`\n"
        f"➤ Notification Channel: `{settings.notification_channel_id}` (PERMANENT)\n"
        f"➤ Chat Pelaporan Saat Ini: `{report_chat_id}`\n"
        f"➤ Jam Operasional: `Senin–Sabtu {op_config.open_hour:02d}.00 – {op_config.close_hour:02d}.00 WIB`\n"
        f"➤ Hari Minggu: `{sun_status}`\n"
        f"➤ Device Terhubung: `{total_devices}` perangkat aktif\n"
        f"➤ Auto Forward: `{fwd_label}`\n"
        f"➤ Timezone: `{settings.timezone}` (WIB)\n\n"
        "Silakan pilih menu navigasi di bawah ini:"
    )


# ------------------ /admin COMMAND & PASSWORD AUTH ------------------


@router.message(Command("admin"))
async def handle_admin_command(
    message: Message,
    state: FSMContext,
    repository: Repository,
    settings: Settings,
):
    """
    Section 10: Admin Dashboard Authentication & Overview
    Prompts for password: aschen2026 or accepts directly: /admin aschen2026
    """
    user = message.from_user
    if not user:
        return

    # Check if password was supplied directly in command: /admin aschen2026
    parts = (message.text or "").strip().split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip() == settings.admin_password:
        AUTHENTICATED_ADMINS.add(user.id)
        await state.clear()
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

    # If already authenticated in session, show dashboard immediately
    if user.id in AUTHENTICATED_ADMINS or settings.is_admin(user.id):
        text = await render_overview_text(repository, settings)
        await message.answer(
            text=text,
            parse_mode="Markdown",
            reply_markup=get_admin_main_keyboard(),
        )
        return

    # Set state and prompt for password
    await state.set_state(AdminAuthStates.waiting_for_password)
    await message.reply(
        "𓄲 MEDIAPATNER — ADMIN AUTHENTICATION 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        "🔒 *Akses Dashboard Administrator Terkunci.*\n"
        "Silakan ketik password administrator untuk melanjutkan:\n\n"
        "💡 *Tips:* Anda juga dapat mengetik `/admin aschen2026` secara langsung.",
        parse_mode="Markdown",
    )


@router.message(AdminAuthStates.waiting_for_password)
async def handle_admin_password_input(
    message: Message,
    state: FSMContext,
    repository: Repository,
    settings: Settings,
):
    user = message.from_user
    entered_pass = (message.text or "").strip()

    # Safely delete password input message from chat history
    try:
        await message.delete()
    except Exception:
        pass

    if entered_pass == settings.admin_password:
        AUTHENTICATED_ADMINS.add(user.id)
        await state.clear()
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
    else:
        await state.clear()
        await message.answer(
            "⛔ *Password Salah!*\n"
            "Akses Dashboard Administrator ditolak.\n"
            "Ketik `/admin` kembali jika ingin mencoba lagi.",
            parse_mode="Markdown",
        )


@router.callback_query(F.data == "admin_act:logout")
async def handle_admin_logout(callback: CallbackQuery):
    user = callback.from_user
    if user and user.id in AUTHENTICATED_ADMINS:
        AUTHENTICATED_ADMINS.discard(user.id)
    await callback.message.edit_text(
        "🔒 *Anda telah keluar (logout) dari sesi Administrator.*\n\n"
        "Ketik `/admin` dan masukkan password untuk masuk kembali ke Dashboard.",
        parse_mode="Markdown",
    )
    await callback.answer("Logout berhasil.")


# ------------------ DASHBOARD MENUS ------------------


@router.callback_query(F.data == "admin_menu:home")
@router.callback_query(F.data == "admin_menu:overview")
async def handle_admin_overview_callback(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak. Sesi admin terkunci. Ketik /admin untuk login.", show_alert=True)
        return

    await state.clear()
    text = await render_overview_text(repository, settings)

    try:
        await callback.message.edit_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=get_admin_main_keyboard(),
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()


# ------------------ 1. SISTEM LOGIN DEVICE (4-STAGE AUTH) ------------------


@router.callback_query(F.data == "admin_menu:login_device")
async def handle_start_device_login(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
):
    """TAHAP 1 — INPUT NOMOR TELEPON"""
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await state.set_state(AdminDeviceLoginStates.waiting_for_phone)
    text = (
        "𓄲 ADMIN DEVICE LOGIN\n\n"
        "Selamat datang di sistem autentikasi Admin ASCHEN EVENT ORGANIZER.\n\n"
        "Silakan masukkan nomor telepon yang terhubung dengan akun Telegram Anda.\n\n"
        "Contoh: `+62xxxxxxxxxxx`\n\n"
        "Pastikan nomor telepon aktif dan dapat menerima kode verifikasi Telegram."
    )
    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_login_phone_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_login:cancel")
async def handle_cancel_device_login(
    callback: CallbackQuery,
    state: FSMContext,
    repository: Repository,
    settings: Settings,
):
    await state.clear()
    await callback.answer("Proses login perangkat dibatalkan.")
    await handle_admin_overview_callback(callback, repository, settings, state)


@router.message(AdminDeviceLoginStates.waiting_for_phone)
async def handle_device_phone_input(
    message: Message,
    state: FSMContext,
    settings: Settings,
    bot: Bot,
):
    """Validates phone number and moves to TAHAP 2 — VERIFIKASI KODE TELEGRAM."""
    phone_text = (message.text or "").strip()
    clean_phone = re.sub(r"[^\d+]", "", phone_text)

    if not clean_phone.startswith("+") or len(clean_phone) < 9 or len(clean_phone) > 16:
        await message.reply(
            "⚠️ Format nomor telepon tidak valid.\n"
            "Gunakan format internasional, contoh: `+628123456789`\n"
            "Silakan ketik ulang nomor telepon Anda:",
            parse_mode="Markdown",
            reply_markup=get_login_phone_keyboard(),
        )
        return

    # Generate 5-digit verification code
    code = f"{random.randint(10000, 99999)}"
    expires_at = datetime.now() + timedelta(minutes=3)

    await state.update_data(
        phone=clean_phone,
        code=code,
        expires_at=expires_at.isoformat(),
        attempts=0,
    )
    await state.set_state(AdminDeviceLoginStates.waiting_for_code)

    # Dispatch verification code notification to the admin via Telegram
    try:
        await bot.send_message(
            chat_id=message.from_user.id,
            text=(
                "🔐 *TELEGRAM VERIFICATION CODE*\n\n"
                f"Kode verifikasi masuk perangkat Anda: `{code}`\n\n"
                "⚠️ _Jangan bagikan kode ini kepada siapa pun! Kode berlaku selama 3 menit._"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Could not dispatch verification code message: {e}")

    text = (
        "𓄲 TELEGRAM VERIFICATION\n\n"
        "Kode verifikasi telah dikirimkan melalui Telegram.\n\n"
        "Silakan masukkan kode verifikasi untuk melanjutkan proses login."
    )
    await message.reply(
        text=text,
        reply_markup=get_login_otp_keyboard(),
    )


@router.callback_query(F.data == "admin_login:resend_code")
async def handle_resend_verification_code(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
):
    data = await state.get_data()
    phone = data.get("phone")
    if not phone:
        await callback.answer("Sesi telah berakhir. Silakan login ulang.", show_alert=True)
        return

    # Generate new code
    new_code = f"{random.randint(10000, 99999)}"
    expires_at = datetime.now() + timedelta(minutes=3)
    await state.update_data(code=new_code, expires_at=expires_at.isoformat(), attempts=0)

    try:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=(
                "🔄 *KODE VERIFIKASI BARU*\n\n"
                f"Kode verifikasi Telegram Anda: `{new_code}`\n\n"
                "⚠️ _Kode berlaku selama 3 menit._"
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"Failed to resend code: {e}")

    await callback.answer("Kode verifikasi baru telah dikirimkan!", show_alert=True)


@router.message(AdminDeviceLoginStates.waiting_for_code)
async def handle_device_code_input(
    message: Message,
    state: FSMContext,
    settings: Settings,
):
    """Verifies Telegram code and prompts for TAHAP 3 — TWO-STEP VERIFICATION (2FA)."""
    entered_code = (message.text or "").strip()
    data = await state.get_data()
    expected_code = data.get("code")
    expires_str = data.get("expires_at")
    attempts = data.get("attempts", 0)

    # Check expiration
    if expires_str:
        expires_at = datetime.fromisoformat(expires_str)
        if datetime.now() > expires_at:
            await message.reply(
                "⚠️ Kode verifikasi telah kadaluarsa.\n"
                "Silakan tekan tombol di bawah untuk meminta pengiriman ulang kode.",
                reply_markup=get_login_otp_keyboard(),
            )
            return

    # Check attempts
    if attempts >= 3:
        await state.clear()
        await message.reply(
            "⛔ Batas percobaan verifikasi terlampaui demi keamanan.\n"
            "Proses login dibatalkan. Silakan mulai kembali dari Menu Admin.",
            reply_markup=get_admin_main_keyboard(),
        )
        return

    if entered_code != expected_code:
        attempts += 1
        await state.update_data(attempts=attempts)
        remaining = 3 - attempts
        await message.reply(
            f"❌ Kode verifikasi salah! Sisa percobaan: {remaining} kali.\n"
            "Silakan periksa kembali kode yang dikirimkan melalui Telegram dan ketik ulang:",
            reply_markup=get_login_otp_keyboard(),
        )
        return

    # Move to TAHAP 3 — TWO-STEP VERIFICATION
    await state.set_state(AdminDeviceLoginStates.waiting_for_2fa)
    text = (
        "𓄲 TWO-STEP VERIFICATION\n\n"
        "Akun Telegram Anda menggunakan sistem keamanan Two-Step Verification.\n\n"
        "Silakan masukkan password Telegram Anda untuk menyelesaikan proses autentikasi."
    )
    await message.reply(
        text=text,
        reply_markup=get_login_2fa_keyboard(),
    )


@router.message(AdminDeviceLoginStates.waiting_for_2fa)
async def handle_device_2fa_input(
    message: Message,
    state: FSMContext,
    repository: Repository,
    settings: Settings,
):
    """
    TAHAP 3 & 4: Verifies 2FA password, deletes message immediately,
    and registers device into SQLite database.
    """
    entered_2fa = (message.text or "").strip()

    # Safely delete password input message from chat
    try:
        await message.delete()
    except Exception:
        pass

    data = await state.get_data()
    phone = data.get("phone", "+62xxxxxxx")

    # Validate 2FA password against configured password
    if entered_2fa != settings.admin_password:
        await message.reply(
            "❌ Password Two-Step Verification (2FA) salah!\n"
            "Silakan ketik ulang password dengan benar:",
            reply_markup=get_login_2fa_keyboard(),
        )
        return

    # TAHAP 4 — LOGIN BERHASIL
    user = message.from_user
    device_hex = secrets.token_hex(2).upper()
    device_id = f"DEV-ASCHEN-{device_hex}"
    masked_phone = mask_phone_number(phone)

    now_wib = get_current_wib()
    login_str = now_wib.strftime("%d %B %Y, %H.%M")
    now_iso = now_wib.strftime("%Y-%m-%d %H:%M:%S")

    device_record = AdminDeviceRecord(
        device_id=device_id,
        admin_id=user.id,
        admin_name=user.full_name,
        admin_username=user.username,
        phone_number=masked_phone,
        device_model="Telegram Android / Desktop Client",
        session_token=secrets.token_hex(16),
        status="Active",
        login_at=login_str,
        last_active=now_iso,
    )
    await repository.register_device(device_record)

    await repository.log_activity(
        action="DEVICE_LOGIN_SUCCESS",
        user_id=user.id,
        details=f"Device {device_id} registered for phone {masked_phone}",
    )

    await state.clear()

    success_text = (
        "𓄲 LOGIN DEVICE BERHASIL!\n\n"
        "Selamat! Akun Telegram Anda berhasil terhubung dengan sistem Admin Media Partner ASCHEN EVENT ORGANIZER.\n\n"
        "INFORMASI PERANGKAT\n\n"
        f"➤ Nomor Telegram: {masked_phone}\n"
        f"➤ Device ID: `{device_id}`\n"
        f"➤ Waktu Login: {login_str} WIB\n"
        "➤ Status: Active [🟢]\n\n"
        "Silakan pilih menu lanjutan di bawah ini:"
    )

    await message.answer(
        text=success_text,
        parse_mode="Markdown",
        reply_markup=get_login_success_keyboard(),
    )


# ------------------ 2. MANAJEMEN DEVICE ADMIN ------------------


@router.callback_query(F.data == "admin_menu:devices")
async def handle_manage_devices_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    devices = await repository.get_active_devices()
    text = (
        "𓄲 MANAJEMEN DEVICE ADMIN 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        f"Total perangkat terhubung aktif: `{len(devices)}`\n\n"
    )

    if not devices:
        text += (
            "Belum ada perangkat admin yang terdaftar.\n"
            "Gunakan tombol *Login Device* untuk menghubungkan perangkat Telegram Anda."
        )
    else:
        for idx, d in enumerate(devices, 1):
            text += (
                f"*{idx}. Device ID:* `{d.device_id}`\n"
                f"   ➤ Nomor: `{d.phone_number}`\n"
                f"   ➤ Admin: {d.admin_name} (@{d.admin_username or 'none'})\n"
                f"   ➤ Waktu Login: {d.login_at} WIB\n"
                f"   ➤ Status: `{d.status}` [🟢]\n\n"
            )

    keyboard = get_device_list_keyboard(devices)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("device_info:"))
async def handle_device_info(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    device_id = callback.data.split(":")[1]
    dev = await repository.get_device(device_id)
    if not dev:
        await callback.answer("Perangkat tidak ditemukan.", show_alert=True)
        return

    text = (
        f"📱 *DETAIL PERANGKAT ADMIN*\n\n"
        f"➤ Device ID: `{dev.device_id}`\n"
        f"➤ Nomor Terhubung: `{dev.phone_number}`\n"
        f"➤ Admin Pemilik: {dev.admin_name} (`{dev.admin_id}`)\n"
        f"➤ Username: @{dev.admin_username or 'none'}\n"
        f"➤ Tipe Klien: `{dev.device_model}`\n"
        f"➤ Login Pada: {dev.login_at} WIB\n"
        f"➤ Status: `{dev.status}`\n"
    )
    await callback.answer(f"Perangkat: {dev.device_id} ({dev.phone_number})", show_alert=True)


@router.callback_query(F.data.startswith("device_act:logout:"))
async def handle_device_logout_single(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    device_id = callback.data.split(":")[2]
    revoked = await repository.revoke_device(device_id)
    if revoked:
        await repository.log_activity(
            action="DEVICE_LOGOUT",
            user_id=callback.from_user.id,
            details=f"Device {device_id} logged out by Admin {callback.from_user.full_name}",
        )
        await callback.answer(f"Perangkat {device_id} berhasil di-logout.", show_alert=True)
    else:
        await callback.answer("Gagal me-logout perangkat.", show_alert=True)

    await handle_manage_devices_menu(callback, repository, settings)


@router.callback_query(F.data.startswith("device_act:revoke:"))
async def handle_device_revoke_single(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    device_id = callback.data.split(":")[2]
    revoked = await repository.revoke_device(device_id)
    if revoked:
        await repository.log_activity(
            action="DEVICE_REVOKED",
            user_id=callback.from_user.id,
            details=f"Akses device {device_id} dicabut oleh Admin {callback.from_user.full_name}",
        )
        await callback.answer(f"Akses perangkat {device_id} telah dicabut secara permanen.", show_alert=True)
    else:
        await callback.answer("Gagal mencabut akses perangkat.", show_alert=True)

    await handle_manage_devices_menu(callback, repository, settings)


@router.callback_query(F.data == "device_act:revoke_all")
async def handle_device_revoke_all(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    count = await repository.revoke_all_devices()
    await repository.log_activity(
        action="ALL_DEVICES_REVOKED",
        user_id=callback.from_user.id,
        details=f"All {count} active sessions ended by Admin {callback.from_user.full_name}",
    )
    await callback.answer(f"Seluruh {count} sesi perangkat aktif berhasil diakhiri.", show_alert=True)
    await handle_manage_devices_menu(callback, repository, settings)


# ------------------ 3. PEMILIHAN CHAT TUJUAN PELAPORAN ------------------


@router.callback_query(F.data == "admin_menu:choose_report_chat")
async def handle_choose_report_chat_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    current_chat = await repository.get_report_chat_id()
    current_type = await repository.get_report_chat_type()

    text = (
        "𓄲 PILIH CHAT PELAPORAN 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        "Konfigurasi Chat Tujuan Laporan Request Poster:\n\n"
        f"➤ *Chat Pelaporan Aktif:* `{current_chat}`\n"
        f"➤ *Tipe Target:* `{current_type}`\n"
        f"➤ *Channel Notifikasi Resmi:* `{settings.notification_channel_id}` (Permanen)\n\n"
        "Pilih salah satu target chat pelaporan atau atur custom ID grup/channel di bawah ini:"
    )

    keyboard = get_report_chat_keyboard(current_chat, current_type)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "report_chat:set_permanent")
async def handle_set_report_chat_permanent(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    await repository.set_report_chat_id(settings.notification_channel_id, "PERMANENT_CHANNEL")
    await callback.answer("Chat pelaporan diubah ke Channel Notifikasi Permanen.", show_alert=True)
    await handle_choose_report_chat_menu(callback, repository, settings)


@router.callback_query(F.data == "report_chat:set_private")
async def handle_set_report_chat_private(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user_id = str(callback.from_user.id)
    await repository.set_report_chat_id(user_id, "PRIVATE_CHAT")
    await callback.answer(f"Chat pelaporan diubah ke Chat Pribadi Admin ({user_id}).", show_alert=True)
    await handle_choose_report_chat_menu(callback, repository, settings)


@router.callback_query(F.data == "report_chat:set_current")
async def handle_set_report_chat_current(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    chat_id = str(callback.message.chat.id)
    chat_type = "GROUP" if callback.message.chat.type in ("group", "supergroup") else "PRIVATE_CHAT"
    await repository.set_report_chat_id(chat_id, chat_type)
    await callback.answer(f"Chat pelaporan diubah ke chat ini ({chat_id}).", show_alert=True)
    await handle_choose_report_chat_menu(callback, repository, settings)


@router.callback_query(F.data == "report_chat:input_custom")
async def handle_prompt_custom_chat_id(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
):
    await state.set_state(AdminReportChatStates.waiting_for_custom_chat_id)
    text = (
        "✏️ *INPUT CUSTOM CHAT / GROUP ID*\n\n"
        "Silakan ketik atau tempelkan Chat ID atau Username Grup/Channel tujuan pelaporan.\n\n"
        "Contoh Grup / Channel ID: `-1001234567890`\n"
        "Contoh Username: `@GrupAschenInternal`\n\n"
        "⚠️ _Pastikan bot telah ditambahkan ke grup/channel tersebut sebagai Administrator._"
    )
    from aiogram.types import InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Batal", callback_data="admin_menu:choose_report_chat")]]
    )
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.message(AdminReportChatStates.waiting_for_custom_chat_id)
async def handle_save_custom_chat_id(
    message: Message,
    state: FSMContext,
    repository: Repository,
    bot: Bot,
    settings: Settings,
):
    target = (message.text or "").strip()
    try:
        chat = await bot.get_chat(target)
        chat_type_str = f"CUSTOM_{chat.type.upper()}"
        await repository.set_report_chat_id(str(chat.id), chat_type_str)
        await state.clear()
        await message.answer(
            f"✅ *Berhasil!* Chat pelaporan berhasil disetel ke:\n"
            f"➤ Judul: *{chat.title or chat.full_name}*\n"
            f"➤ ID: `{chat.id}`\n"
            f"➤ Tipe: `{chat.type}`",
            parse_mode="Markdown",
            reply_markup=get_admin_main_keyboard(),
        )
    except Exception as e:
        await message.reply(
            f"⚠️ Bot tidak dapat mengakses chat `{target}`.\n"
            f"Penyebab: `{e}`\n\n"
            "Pastikan bot telah ditambahkan ke dalam chat tersebut dan memiliki hak kirim pesan.",
            parse_mode="Markdown",
        )


@router.callback_query(F.data == "report_chat:test_send")
async def handle_test_send_report_chat(
    callback: CallbackQuery,
    repository: Repository,
    bot: Bot,
    settings: Settings,
):
    target_chat = await repository.get_report_chat_id()
    now_str = get_current_wib().strftime("%d %B %Y, %H.%M")
    test_text = (
        "🧪 *TEST KONEKSI CHAT PELAPORAN* 𓈒\n\n"
        "Pesan pengujian otomatis dari sistem Media Partner ASCHEN EVENT ORGANIZER.\n\n"
        f"➤ Waktu: {now_str} WIB\n"
        "➤ Status Hak Akses: AKTIF [🟢]\n"
        "Bot siap menerima dan mengirim laporan Request Poster ke chat ini."
    )
    try:
        await bot.send_message(chat_id=target_chat, text=test_text, parse_mode="Markdown")
        await callback.answer(f"✅ Pesan tes berhasil dikirim ke {target_chat}!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Gagal kirim ke {target_chat}: {e}", show_alert=True)


# ------------------ 6. PENGATURAN JADWAL OPERASIONAL ------------------


@router.callback_query(F.data == "admin_menu:op_hours")
async def handle_operational_hours_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    op_config = await repository.get_operational_config()
    sun_status = "TUTUP (Libur Seharian) ✅" if op_config.sunday_closed else "BUKA ❌"

    text = (
        "𓄲 PENGATURAN JADWAL OPERASIONAL 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        "Konfigurasi Jam Operasional Pengajuan Poster:\n\n"
        f"➤ *Hari Kerja:* Senin – Sabtu\n"
        f"➤ *Jam Buka:* `{op_config.open_hour:02d}.00 WIB`\n"
        f"➤ *Jam Tutup:* `{op_config.close_hour:02d}.00 WIB`\n"
        f"➤ *Hari Minggu:* `{sun_status}`\n\n"
        "Gunakan tombol di bawah untuk mengubah pengaturan:"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_operational_settings_keyboard(op_config),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("op_set:open:"))
async def handle_set_open_hour(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    new_open = int(callback.data.split(":")[2])
    cfg = await repository.get_operational_config()
    await repository.set_operational_config(new_open, cfg.close_hour, cfg.sunday_closed)
    await callback.answer(f"Jam buka diubah ke {new_open:02d}.00 WIB")
    await handle_operational_hours_menu(callback, repository, settings)


@router.callback_query(F.data.startswith("op_set:close:"))
async def handle_set_close_hour(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    new_close = int(callback.data.split(":")[2])
    cfg = await repository.get_operational_config()
    await repository.set_operational_config(cfg.open_hour, new_close, cfg.sunday_closed)
    await callback.answer(f"Jam tutup diubah ke {new_close:02d}.00 WIB")
    await handle_operational_hours_menu(callback, repository, settings)


@router.callback_query(F.data == "op_set:toggle_sunday")
async def handle_toggle_sunday_status(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    cfg = await repository.get_operational_config()
    new_sunday = not cfg.sunday_closed
    await repository.set_operational_config(cfg.open_hour, cfg.close_hour, new_sunday)
    status_label = "TUTUP (Libur)" if new_sunday else "BUKA"
    await callback.answer(f"Hari Minggu sekarang: {status_label}")
    await handle_operational_hours_menu(callback, repository, settings)


# ------------------ 5. RIWAYAT REQUEST POSTER & ACTION BUTTONS ------------------


@router.callback_query(F.data.startswith("admin_menu:requests:"))
async def handle_requests_history_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    page = int(callback.data.split(":")[2])
    total_count = await repository.get_poster_reports_count()
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    reports = await repository.get_poster_reports(limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    text = (
        "𓄲 MEDIAPATNER — RIWAYAT REQUEST POSTER 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        f"Total pengajuan: `{total_count}` | Halaman: `{page + 1}/{total_pages}`\n\n"
    )

    if not reports:
        text += "Belum ada laporan request poster dari pengguna."
        items = []
    else:
        text += "Pilih pengajuan di bawah ini untuk melihat detail dan status:"
        items = [
            (
                r.id,
                f"#{r.id} [{r.status}] {r.sender_name[:12]} ({r.institution_name or '-'})",
            )
            for r in reports
        ]

    keyboard = get_request_list_keyboard(items, page, total_pages)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("request_detail:"))
async def handle_request_detail(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    parts = callback.data.split(":")
    report_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0

    report = await repository.get_poster_report(report_id)
    if not report:
        await callback.answer("Pengajuan tidak ditemukan.", show_alert=True)
        return

    poster = await repository.get_poster(report.poster_id)

    text = (
        f"𓄲 DETAIL REQUEST POSTER #{report.id} 𓈒\n\n"
        f"➤ *Media Partner:* {report.sender_name} (`{report.sender_id}`)\n"
        f"➤ *Username:* @{report.sender_username or 'none'}\n"
        f"➤ *Nama Instansi:* {report.institution_name or '-'}\n"
        f"➤ *Status Saat Ini:* *{report.status}*\n"
        f"➤ *ID Poster:* `#{report.poster_id}`\n"
    )
    if poster:
        text += f"➤ *Jadwal Siar:* {poster.slot_day}, {poster.slot_date} {poster.slot_time} WIB\n"
    if report.processed_by_name:
        text += f"➤ *Diproses Oleh:* {report.processed_by_name} ({report.processed_at} WIB)\n"
    if report.action_note:
        text += f"➤ *Catatan:* {report.action_note}\n"

    keyboard = get_request_detail_keyboard(report.id, report.status, page, poster_id=report.poster_id)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("rpt_act:"))
async def handle_report_action_callback(
    callback: CallbackQuery,
    report_service: ReportService,
    repository: Repository,
    settings: Settings,
):
    """
    Handles interactive actions from report chat buttons:
    Terima, Tolak, Tandai Selesai.
    """
    parts = callback.data.split(":")
    report_id = int(parts[1])
    action = parts[2]

    await report_service.handle_action(callback, report_id, action)


# ------------------ 7. DASHBOARD ANTREAN (KEEP / SCHEDULED / PUBLISHED / FAILED) ------------------


@router.callback_query(F.data.startswith("admin_menu:keep:"))
@router.callback_query(F.data.startswith("admin_menu:scheduled:"))
@router.callback_query(F.data.startswith("admin_menu:published:"))
@router.callback_query(F.data.startswith("admin_menu:failed:"))
async def handle_poster_list_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    parts = callback.data.split(":")
    menu_name = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0

    status_map = {
        "keep": "KEEP",
        "scheduled": "SCHEDULED",
        "published": "PUBLISHED",
        "failed": "FAILED",
    }
    target_status = status_map.get(menu_name, "KEEP")

    total_count = await repository.get_posters_count_by_status(target_status)
    total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    posters = await repository.get_posters_by_status(
        status=target_status,
        limit=PAGE_SIZE,
        offset=page * PAGE_SIZE,
    )

    title_map = {
        "keep": "📥 KEEP QUEUE",
        "scheduled": "🗓 SCHEDULED POSTERS",
        "published": "✅ PUBLISHED POSTERS",
        "failed": "❌ FAILED POSTERS",
    }
    title = title_map.get(menu_name, "POSTERS")

    if not posters:
        text = (
            f"𓄲 MEDIAPATNER — {title} 𓈒\n\n"
            "Saat ini tidak ada poster dalam daftar ini.\n"
            f"Total: `0` poster."
        )
        items = []
    else:
        text = (
            f"𓄲 MEDIAPATNER — {title} 𓈒\n\n"
            f"Total: `{total_count}` poster | Halaman: `{page + 1}/{total_pages}`\n"
            "Klik pada poster di bawah ini untuk melihat detail dan tindakan:"
        )
        items = [
            (
                p.id,
                f"#{p.id} | {p.slot_day} {p.slot_time} | {p.sender_name[:12]}",
            )
            for p in posters
        ]

    keyboard = get_poster_list_keyboard(items, menu_name, page, total_pages)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_menu:activity:"))
async def handle_activity_log_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    parts = callback.data.split(":")
    page = int(parts[2]) if len(parts) > 2 else 0

    logs = await repository.get_recent_activity(limit=10, offset=page * 10)

    text = "𓄲 MEDIAPATNER — USER ACTIVITY 𓈒\n\n"
    if not logs:
        text += "Belum ada catatan aktivitas pengguna."
    else:
        for log in logs:
            text += f"• `[{log.timestamp}]` *{log.action}*\n"
            if log.poster_id:
                text += f"  Poster: `#{log.poster_id}` | User: `{log.user_id}`\n"
            if log.details:
                text += f"  Detail: {log.details}\n"
            text += "\n"

    from aiogram.types import InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[get_back_to_admin_button()]]
    )
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_menu:settings")
async def handle_settings_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    auto_fwd = await repository.is_auto_forward_enabled()
    fwd_label = "AKTIF ✅" if auto_fwd else "NONAKTIF ❌"

    text = (
        "𓄲 MEDIAPATNER — BOT SETTINGS 𓈒\n\n"
        "Konfigurasi Sistem:\n\n"
        f"➤ *Main Broadcast Channel:* `{settings.channel_username}`\n"
        f"➤ *Notification Channel:* `{settings.notification_channel_id}`\n"
        "   _Status: PERMANENT (Terkunci & Tidak dapat diubah)_\n"
        f"➤ *Timezone:* `{settings.timezone}` (WIB)\n"
        f"➤ *Auto Forward Mode:* `{fwd_label}`\n"
        f"➤ *Retry Limit:* `{settings.retry_max_attempts}` kali\n"
        f"➤ *Interval Publikasi:* `{settings.post_interval_seconds}` detik\n\n"
        "Gunakan tombol di bawah untuk mengubah setelan Auto Forward:"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_settings_keyboard(auto_fwd),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_act:toggle_auto_forward")
async def handle_toggle_auto_forward(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    new_val = await repository.toggle_auto_forward()
    await repository.log_activity(
        action="SETTINGS_CHANGED",
        user_id=user.id,
        details=f"Auto Forward changed to {new_val}",
    )

    await callback.answer(f"Auto Forward berhasil diubah menjadi: {'AKTIF' if new_val else 'NONAKTIF'}")
    await handle_settings_menu(callback, repository, settings)


# ------------------ PING CHANNEL SIARAN (@ASCHENEO) ------------------


@router.message(Command("ping", "pingchannel"))
async def handle_ping_command(
    message: Message,
    publisher_service: PublisherService,
    settings: Settings,
):
    user = message.from_user
    if not user or not is_admin_check(user.id, settings):
        return

    status_msg = await message.answer("📡 *Melakukan Ping ke Channel Siaran...*", parse_mode="Markdown")
    ping_data = await publisher_service.ping_channel()

    text = (
        "𓄲 STATUS PING CHANNEL SIARAN 𓈒\n\n"
        f"➤ *Channel Tujuan:* `{ping_data.get('channel')}`\n"
        f"➤ *Judul Channel:* *{ping_data.get('chat_title', '-')}*\n"
        f"➤ *Status Bot:* `{ping_data.get('member_status', '-')}`\n"
        f"➤ *Hak Administrator:* `{'YA ✅' if ping_data.get('is_admin') else 'TIDAK ❌'}`\n"
        f"➤ *Izin Siaran (Post):* `{'AKTIF ✅' if ping_data.get('can_post') else 'NONAKTIF ❌'}`\n"
        f"➤ *Izin Edit Pesan:* `{'AKTIF ✅' if ping_data.get('can_edit') else 'NONAKTIF ❌'}`\n"
        f"➤ *Latency Telegram API:* `{ping_data.get('latency_ms', 0)} ms` ⚡\n"
        f"➤ *Kondisi Sistem:* *{ping_data.get('health_status', '-')}*\n\n"
    )
    if not ping_data.get("success"):
        text += f"⚠️ *Error:* `{ping_data.get('error')}`\n\n"
    text += "Semua poster berstatus KEEP akan dikirimkan ke channel ini."

    await status_msg.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_ping_channel_keyboard(),
    )


@router.callback_query(F.data == "admin_menu:ping_channel")
async def handle_ping_channel_callback(
    callback: CallbackQuery,
    publisher_service: PublisherService,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await callback.answer("📡 Menghubungi Channel Siaran...", show_alert=False)
    ping_data = await publisher_service.ping_channel()

    text = (
        "𓄲 STATUS PING CHANNEL SIARAN 𓈒\n\n"
        f"➤ *Channel Tujuan:* `{ping_data.get('channel')}`\n"
        f"➤ *Judul Channel:* *{ping_data.get('chat_title', '-')}*\n"
        f"➤ *Status Bot:* `{ping_data.get('member_status', '-')}`\n"
        f"➤ *Hak Administrator:* `{'YA ✅' if ping_data.get('is_admin') else 'TIDAK ❌'}`\n"
        f"➤ *Izin Siaran (Post):* `{'AKTIF ✅' if ping_data.get('can_post') else 'NONAKTIF ❌'}`\n"
        f"➤ *Izin Edit Pesan:* `{'AKTIF ✅' if ping_data.get('can_edit') else 'NONAKTIF ❌'}`\n"
        f"➤ *Latency Telegram API:* `{ping_data.get('latency_ms', 0)} ms` ⚡\n"
        f"➤ *Kondisi Sistem:* *{ping_data.get('health_status', '-')}*\n\n"
    )
    if not ping_data.get("success"):
        text += f"⚠️ *Error:* `{ping_data.get('error')}`\n\n"
    text += "Semua poster berstatus KEEP akan dikirimkan ke channel ini."

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_ping_channel_keyboard(),
    )


# ------------------ POSTER DETAIL & ACTIONS ------------------


@router.callback_query(F.data.startswith("poster_detail:"))
async def handle_poster_detail(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    parts = callback.data.split(":")
    poster_id = int(parts[1])
    return_menu = parts[2] if len(parts) > 2 else "keep"
    page = int(parts[3]) if len(parts) > 3 else 0

    poster = await repository.get_poster(poster_id)
    if not poster:
        await callback.answer("Poster tidak ditemukan.", show_alert=True)
        return

    link_display = poster.source_link if poster.source_link else "(Direct Upload/Forward)"
    caption_preview = (poster.caption[:150] + "...") if poster.caption and len(poster.caption) > 150 else (poster.caption or "-")

    text = (
        f"𓄲 POSTER DETAIL #{poster.id} 𓈒\n\n"
        f"➤ *Pengirim:* {poster.sender_name} (`{poster.sender_id}`)\n"
        f"➤ *Username:* @{poster.sender_username or 'none'}\n"
        f"➤ *Status:* `{poster.status}`\n"
        f"➤ *Jadwal:* {poster.slot_day}, {poster.slot_date} ({poster.slot_time} WIB)\n"
        f"➤ *Link:* {link_display}\n"
        f"➤ *Tipe Media:* `{poster.media_type or 'text'}`\n"
        f"➤ *Percobaan Retry:* `{poster.retry_count}`\n"
    )

    if poster.failure_reason:
        text += f"➤ *Alasan Gagal:* `{poster.failure_reason}`\n"
    if poster.published_at:
        text += f"➤ *Diterbitkan pada:* `{poster.published_at}`\n"

    text += f"\n📝 *Caption:*\n_{caption_preview}_\n"

    keyboard = get_poster_detail_keyboard(poster.id, poster.status, return_menu, page)
    await callback.message.edit_text(text=text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("poster_act:publish:"))
async def handle_manual_publish(
    callback: CallbackQuery,
    repository: Repository,
    publisher_service: PublisherService,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    poster_id = int(callback.data.split(":")[2])
    poster = await repository.get_poster(poster_id)
    if not poster:
        await callback.answer("Poster tidak ditemukan.", show_alert=True)
        return

    await callback.answer("Memproses publikasi ke Channel Utama...")

    await repository.mark_publishing(poster.id)
    success = await publisher_service.publish_poster(poster)
    if success:
        await repository.log_activity(
            action="MANUAL_PUBLISH",
            poster_id=poster.id,
            user_id=user.id,
            details=f"Manually published by Admin {user.full_name}",
        )
        await callback.message.answer(
            f"✅ *Sukses!* Poster `#{poster.id}` berhasil dipublikasikan ke `{settings.channel_username}`.",
            parse_mode="Markdown",
        )
    else:
        await callback.message.answer(
            f"❌ *Gagal!* Publikasi poster `#{poster.id}` tidak berhasil. Silakan periksa log notifikasi.",
            parse_mode="Markdown",
        )

    await handle_admin_overview_callback(callback, repository, settings, state)


@router.callback_query(F.data.startswith("poster_act:delete:"))
async def handle_delete_poster(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    poster_id = int(callback.data.split(":")[2])
    deleted = await repository.delete_poster(poster_id)

    if deleted:
        await repository.log_activity(
            action="DELETED",
            poster_id=poster_id,
            user_id=user.id,
            details=f"Deleted by Admin {user.full_name}",
        )
        await callback.answer(f"Poster #{poster_id} berhasil dihapus dari antrean.", show_alert=True)
    else:
        await callback.answer("Gagal menghapus poster.", show_alert=True)

    await handle_admin_overview_callback(callback, repository, settings, state)


@router.callback_query(F.data.startswith("poster_act:reschedule_menu:"))
async def handle_reschedule_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    poster_id = int(callback.data.split(":")[2])
    poster = await repository.get_poster(poster_id)
    if not poster:
        await callback.answer("Poster tidak ditemukan.", show_alert=True)
        return

    text = (
        f"🗓 *UBAH JADWAL POSTER #{poster.id}*\n\n"
        f"Jadwal saat ini: *{poster.slot_day}, {poster.slot_date} {poster.slot_time} WIB*\n\n"
        "Pilih slot publikasi baru:"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_reschedule_options_keyboard(poster.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("resched_set:"))
async def handle_apply_reschedule(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    parts = callback.data.split(":")
    poster_id = int(parts[1])
    slot_choice = parts[2]

    now_wib = get_current_wib()

    if slot_choice == "next":
        target_time = now_wib + timedelta(hours=1)
        slot_dt, day_str, date_str, time_str = calculate_next_wib_slot(target_time)
    else:
        slot_map = {
            "tue_09": (1, 9, 0),
            "wed_12": (2, 12, 0),
            "thu_09": (3, 9, 0),
            "fri_12": (4, 12, 0),
            "sat_20": (5, 20, 0),
        }
        target_weekday, hour, minute = slot_map.get(slot_choice, (1, 9, 0))

        days_ahead = (target_weekday - now_wib.weekday()) % 7
        if days_ahead == 0 and (now_wib.hour > hour or (now_wib.hour == hour and now_wib.minute >= minute)):
            days_ahead = 7
        slot_dt = (now_wib + timedelta(days=days_ahead)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        day_str = format_indonesian_day(slot_dt)
        date_str = format_indonesian_date(slot_dt)
        time_str = format_indonesian_time(slot_dt)

    slot_iso = slot_dt.strftime("%Y-%m-%dT%H:%M:%S")

    await repository.reschedule_poster(
        poster_id=poster_id,
        scheduled_slot=slot_iso,
        slot_day=day_str,
        slot_date=date_str,
        slot_time=time_str,
    )

    await repository.log_activity(
        action="RESCHEDULED",
        poster_id=poster_id,
        user_id=user.id,
        details=f"Rescheduled by Admin to {day_str}, {date_str} {time_str} WIB",
    )

    await callback.answer(f"Jadwal diubah ke: {day_str}, {date_str} {time_str} WIB", show_alert=True)
    await handle_admin_overview_callback(callback, repository, settings, state)


@router.callback_query(F.data.startswith("poster_act:retry:"))
async def handle_retry_failed_poster(
    callback: CallbackQuery,
    repository: Repository,
    publisher_service: PublisherService,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    poster_id = int(callback.data.split(":")[2])
    poster = await repository.get_poster(poster_id)
    if not poster:
        await callback.answer("Poster tidak ditemukan.", show_alert=True)
        return

    await callback.answer("Mencoba publikasi ulang...")
    success = await publisher_service.publish_poster(poster)
    if success:
        await callback.message.answer(
            f"✅ *Sukses!* Poster `#{poster.id}` berhasil dipublikasikan setelah retry.",
            parse_mode="Markdown",
        )
    else:
        await callback.message.answer(
            f"❌ *Retry Gagal!* Poster `#{poster.id}` tetap gagal dipublikasikan.",
            parse_mode="Markdown",
        )

    await handle_admin_overview_callback(callback, repository, settings, state)


# ==============================================================================
# SECTION 8: SISTEM KONFIGURASI CHANNEL PENYEBARAN & MULTI-BOT (FINAL FIX)
# ==============================================================================

async def render_channel_control_text(repository: Repository) -> str:
    channels = await repository.get_channel_settings()
    bots = await repository.get_all_broadcast_bots()
    hist_count = await repository.get_broadcast_history_count()

    def status_badge(enabled: bool, cid: str) -> str:
        if not cid or not cid.strip():
            return "Belum Dikonfigurasi (OFF) ⚪"
        return "AKTIF [ON] 🟢" if enabled else "NONAKTIF [OFF] 🔴"

    b_ch1 = next((b for b in bots if b.role == "channel_1" and b.is_active), None)
    b_ch2 = next((b for b in bots if b.role == "channel_2" and b.is_active), None)
    b_poster = next((b for b in bots if b.role == "poster" and b.is_active), None)
    backups = [b for b in bots if b.role == "cadangan" and b.is_active]

    ch1_name = f"@{b_ch1.bot_username}" if b_ch1 else "*(Belum Ditugaskan)*"
    ch2_name = f"@{b_ch2.bot_username}" if b_ch2 else "*(Belum Ditugaskan)*"
    poster_bot_name = f"@{b_poster.bot_username}" if b_poster else "*(Belum Ditugaskan)*"
    backup_count = f"{len(backups)} Bot Siap" if backups else "Tidak Ada"

    ch1_display_id = f"`{channels.channel_1_id}`" if channels.channel_1_id else "_(Belum Diatur)_"
    ch2_display_id = f"`{channels.channel_2_id}`" if channels.channel_2_id else "_(Belum Diatur)_"

    return (
        "𓄲 *KONTROL SALURAN & MULTI-BOT DISPATCHER* 𓈒\n"
        "ASCHEN EVENT ORGANIZER\n\n"
        "📡 *STATUS SALURAN PENYEBARAN*\n"
        f"➤ *Channel Utama:* `-1002123283346`\n"
        f"   └ Status: {'AKTIF [ON] 🟢' if channels.main_enabled else 'NONAKTIF [OFF] 🔴'}\n"
        f"➤ *Channel Poster:* `-1003512801822`\n"
        f"   └ Status: {'AKTIF [ON] 🟢' if channels.poster_enabled else 'NONAKTIF [OFF] 🔴'}\n"
        f"➤ *Channel 1:* {ch1_display_id}\n"
        f"   └ Status: {status_badge(channels.channel_1_enabled, channels.channel_1_id)}\n"
        f"➤ *Channel 2:* {ch2_display_id}\n"
        f"   └ Status: {status_badge(channels.channel_2_enabled, channels.channel_2_id)}\n\n"
        "🤖 *PEMBAGIAN TUGAS BOT*\n"
        f"➤ *Bot Channel 1:* {ch1_name}\n"
        f"➤ *Bot Channel 2:* {ch2_name}\n"
        f"➤ *Bot Poster:* {poster_bot_name}\n"
        f"➤ *Bot Cadangan (Failover):* {backup_count}\n\n"
        "📊 *MONITORING ANTREAN*\n"
        f"➤ Total Riwayat Penyebaran: *{hist_count}* pekerjaan tercatat.\n"
        "➤ Mode Failover: *Aktif Otomatis* jika bot utama gagal.\n\n"
        "ᵎ!ᵎ _Pilih tombol kontrol di bawah untuk mengubah status atau konfigurasi:_"
    )


@router.callback_query(F.data == "admin_menu:channel_control")
async def handle_channel_control_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await state.clear()
    channels = await repository.get_channel_settings()
    text = await render_channel_control_text(repository)
    kb = get_channel_control_keyboard(channels)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("chan_toggle:"))
async def handle_channel_toggle(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Data tombol tidak valid.", show_alert=True)
        return

    channel_key = parts[1]  # 'ch1', 'ch2', 'poster'
    target_action = parts[2]  # 'on', 'off'
    channels = await repository.get_channel_settings()

    if target_action == "on":
        # Check if ID is configured before activating
        if channel_key == "ch1" and not channels.channel_1_id:
            await callback.answer(
                "⚠️ ID Channel 1 belum dikonfigurasi!\nSilakan atur ID Channel 1 terlebih dahulu di menu ⚙️ PENGATURAN CHANNEL.",
                show_alert=True,
            )
            return
        elif channel_key == "ch2" and not channels.channel_2_id:
            await callback.answer(
                "⚠️ ID Channel 2 belum dikonfigurasi!\nSilakan atur ID Channel 2 terlebih dahulu di menu ⚙️ PENGATURAN CHANNEL.",
                show_alert=True,
            )
            return

        await repository.set_channel_enabled(channel_key, True)
        label = "Channel 1" if channel_key == "ch1" else ("Channel 2" if channel_key == "ch2" else "Channel Poster")
        await callback.answer(f"🟢 {label} berhasil DIAKTIFKAN!", show_alert=False)
        await repository.log_activity(
            action="CHANNEL_TOGGLE",
            poster_id=None,
            user_id=user.id,
            details=f"{label} toggled ON by Admin",
        )
    else:
        # Turning OFF
        label = "Channel 1" if channel_key == "ch1" else ("Channel 2" if channel_key == "ch2" else "Channel Poster")
        await repository.set_channel_enabled(channel_key, False)

        # Rule C.7: If dispatch is ongoing, stop/cancel subsequent jobs for that channel
        target_cid = ""
        if channel_key == "ch1":
            target_cid = channels.channel_1_id
        elif channel_key == "ch2":
            target_cid = channels.channel_2_id
        elif channel_key == "poster":
            target_cid = channels.poster_id

        if target_cid:
            cancelled_count = await repository.cancel_pending_jobs_for_channel(target_cid)
            if cancelled_count > 0:
                logger.info(f"Cancelled {cancelled_count} pending jobs for {label} ({target_cid})")

        await callback.answer(f"🔴 {label} berhasil DINONAKTIFKAN!", show_alert=False)
        await repository.log_activity(
            action="CHANNEL_TOGGLE",
            poster_id=None,
            user_id=user.id,
            details=f"{label} toggled OFF by Admin",
        )

    # Refresh dashboard
    updated_channels = await repository.get_channel_settings()
    text = await render_channel_control_text(repository)
    kb = get_channel_control_keyboard(updated_channels)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass


@router.callback_query(F.data == "admin_act:sync_bots")
async def handle_sync_bots_callback(
    callback: CallbackQuery,
    repository: Repository,
    multi_bot_service: MultiBotService,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await callback.answer("Sedang mensinkronisasi dan memverifikasi izin semua bot...")
    audit_results = await multi_bot_service.sync_all_bots()

    summary_lines = ["🔄 *HASIL SINKRONISASI & AUDIT BOT*\n"]
    for r in audit_results:
        uname = r.get("username", "Unknown")
        role = r.get("role", "cadangan").upper()
        status = r.get("status", "UNKNOWN")
        ico = "🟢" if "OK" in status else "🔴"
        summary_lines.append(f"{ico} *@{uname}* [{role}]: `{status}`")

    summary_lines.append("\n_Semua bot telah diaudit pada seluruh channel yang aktif._")
    summary_text = "\n".join(summary_lines)

    await callback.message.answer(summary_text, parse_mode="Markdown")
    # Refresh dashboard
    channels = await repository.get_channel_settings()
    text = await render_channel_control_text(repository)
    kb = get_channel_control_keyboard(channels)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass


@router.callback_query(F.data == "admin_menu:chan_settings")
async def handle_channel_settings_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await state.clear()
    channels = await repository.get_channel_settings()

    ch1_val = f"`{channels.channel_1_id}`" if channels.channel_1_id else "_(Belum Diatur)_"
    ch2_val = f"`{channels.channel_2_id}`" if channels.channel_2_id else "_(Belum Diatur)_"

    text = (
        "⚙️ *PENGATURAN ID SALURAN PENYEBARAN*\n\n"
        "Atur ID Telegram untuk Channel 1 dan Channel 2 sesuai channel penyiaran Anda.\n\n"
        f"➤ *Channel 1:* {ch1_val}\n"
        f"➤ *Channel 2:* {ch2_val}\n"
        "➤ *Channel Utama:* `-1002123283346` _(Tetap)_\n"
        "➤ *Channel Poster:* `-1003512801822` _(Tetap)_\n\n"
        "⚠️ _Pastikan bot telah ditambahkan sebagai Administrator di channel sebelum mengaktifkan penyiaran._"
    )

    kb = get_channel_settings_keyboard(channels)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("chan_set_id:"))
async def handle_start_set_channel_id(
    callback: CallbackQuery,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    chan_key = callback.data.split(":")[1]  # 'ch1' or 'ch2'
    target_name = "Channel 1" if chan_key == "ch1" else "Channel 2"

    if chan_key == "ch1":
        await state.set_state(AdminChannelConfigStates.waiting_for_channel_1_id)
    else:
        await state.set_state(AdminChannelConfigStates.waiting_for_channel_2_id)

    prompt = (
        f"✏️ *MASUKKAN ID UNTUK {target_name.upper()}*\n\n"
        "Kirimkan ID Telegram channel tujuan (biasanya diawali `-100`, contoh: `-1002345678901`).\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    await callback.message.answer(prompt, parse_mode="Markdown")
    await callback.answer()


@router.message(AdminChannelConfigStates.waiting_for_channel_1_id)
async def handle_input_channel_1_id(
    message: Message,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = message.from_user
    if not user or not is_admin_check(user.id, settings):
        return

    raw_id = (message.text or "").strip()
    if raw_id.lower() == "/cancel":
        await state.clear()
        await message.answer("Batal mengatur ID Channel 1.")
        return

    if not re.match(r"^-?100\d+$|^-?\d+$", raw_id):
        await message.answer(
            "❌ *Format ID Tidak Valid!*\n"
            "ID Telegram channel harus berupa angka (contoh: `-1002345678901`). Silakan coba lagi atau /cancel:",
            parse_mode="Markdown",
        )
        return

    await repository.set_channel_id("1", raw_id)
    await repository.log_activity(
        action="CONFIG_CHANGE",
        poster_id=None,
        user_id=user.id,
        details=f"Channel 1 ID updated to {raw_id}",
    )
    await state.clear()

    channels = await repository.get_channel_settings()
    await message.answer(
        f"✅ *Berhasil!* ID Channel 1 telah diperbarui menjadi `{raw_id}`.",
        parse_mode="Markdown",
        reply_markup=get_channel_settings_keyboard(channels),
    )


@router.message(AdminChannelConfigStates.waiting_for_channel_2_id)
async def handle_input_channel_2_id(
    message: Message,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = message.from_user
    if not user or not is_admin_check(user.id, settings):
        return

    raw_id = (message.text or "").strip()
    if raw_id.lower() == "/cancel":
        await state.clear()
        await message.answer("Batal mengatur ID Channel 2.")
        return

    if not re.match(r"^-?100\d+$|^-?\d+$", raw_id):
        await message.answer(
            "❌ *Format ID Tidak Valid!*\n"
            "ID Telegram channel harus berupa angka (contoh: `-1002345678901`). Silakan coba lagi atau /cancel:",
            parse_mode="Markdown",
        )
        return

    await repository.set_channel_id("2", raw_id)
    await repository.log_activity(
        action="CONFIG_CHANGE",
        poster_id=None,
        user_id=user.id,
        details=f"Channel 2 ID updated to {raw_id}",
    )
    await state.clear()

    channels = await repository.get_channel_settings()
    await message.answer(
        f"✅ *Berhasil!* ID Channel 2 telah diperbarui menjadi `{raw_id}`.",
        parse_mode="Markdown",
        reply_markup=get_channel_settings_keyboard(channels),
    )


@router.callback_query(F.data.startswith("admin_menu:broadcast_history:"))
async def handle_broadcast_history_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    try:
        page = int(callback.data.split(":")[2])
    except Exception:
        page = 0

    limit = 5
    offset = page * limit
    total_count = await repository.get_broadcast_history_count()
    total_pages = max(1, math.ceil(total_count / limit))
    history_items = await repository.get_broadcast_history(limit=limit, offset=offset)

    lines = [
        "📊 *RIWAYAT PENYEBARAN PESAN & POSTER*",
        f"Total Aktivitas: *{total_count}* pekerjaan\n",
    ]

    if not history_items:
        lines.append("_Belum ada riwayat pengiriman tercatat._")
    else:
        for idx, h in enumerate(history_items, 1):
            ico = "✅" if h.status == "SUCCESS" else "❌"
            err_line = f"   └ Error: `{h.error_message}`\n" if h.error_message else ""
            lines.append(
                f"{ico} *{h.job_id}*\n"
                f"   ├ Target: *{h.target_channel_name or h.target_channel_id}*\n"
                f"   ├ Pengirim: `{h.bot_name}`\n"
                f"   ├ Jenis: *{h.content_type}*\n"
                f"   ├ Waktu: `{h.sent_at}` WIB\n"
                f"   ├ Status: *{h.status}*\n"
                f"{err_line}"
            )

    text = "\n".join(lines)
    kb = get_broadcast_history_keyboard(page, total_pages)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admin_menu:bot_mgmt")
async def handle_bot_management_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await state.clear()
    bots = await repository.get_all_broadcast_bots()

    text = (
        "🤖 *MANAJEMEN MULTI-BOT DISPATCHER*\n\n"
        "Daftar bot yang terdaftar untuk penyiaran. Admin dapat menambah bot baru, "
        "memverifikasi izin administrator, dan mengatur pembagian tugas.\n\n"
        f"Total Bot Terdaftar: *{len(bots)}*\n"
        "ᵎ!ᵎ _Pilih bot untuk mengatur peran (Channel 1, Channel 2, Poster, Cadangan):_"
    )

    kb = get_bot_management_keyboard(bots)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "bot_act:add")
async def handle_bot_add_start(
    callback: CallbackQuery,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    await state.set_state(AdminBotAddStates.waiting_for_bot_token)
    prompt = (
        "➕ *TAMBAH BOT PENYEBARAN BARU*\n\n"
        "Kirimkan *Bot API Token* dari @BotFather yang ingin Anda daftarkan.\n\n"
        "🔒 _Token akan disimpan dengan aman dan disamarkan (masked) di tampilan._\n"
        "Ketik /cancel untuk membatalkan."
    )
    await callback.message.answer(prompt, parse_mode="Markdown")
    await callback.answer()


@router.message(AdminBotAddStates.waiting_for_bot_token)
async def handle_bot_add_token_input(
    message: Message,
    repository: Repository,
    multi_bot_service: MultiBotService,
    settings: Settings,
    state: FSMContext,
):
    user = message.from_user
    if not user or not is_admin_check(user.id, settings):
        return

    raw_token = (message.text or "").strip()
    if raw_token.lower() == "/cancel":
        await state.clear()
        await message.answer("Batal menambahkan bot.")
        return

    if ":" not in raw_token or len(raw_token) < 20:
        await message.answer(
            "❌ *Format Token Tidak Valid!*\n"
            "Token bot biasanya berbentuk `123456789:AA...`. Silakan coba lagi atau /cancel:",
            parse_mode="Markdown",
        )
        return

    wait_msg = await message.answer("🔄 Memverifikasi token bot dengan Telegram API...")
    is_valid, me_info, err = await multi_bot_service.verify_bot_token(raw_token)
    if not is_valid or not me_info:
        await wait_msg.edit_text(
            f"❌ *Verifikasi Bot Gagal!*\nTelegram mengembalikan pesan: `{err}`\nPastikan token benar dan aktif.",
            parse_mode="Markdown",
        )
        return

    # Register in DB
    bot_record = BroadcastBotRecord(
        id=None,
        token=raw_token,
        bot_id=me_info["id"],
        bot_username=me_info["username"],
        bot_first_name=me_info.get("first_name"),
        role="cadangan",
        is_active=True,
        is_verified=False,
        last_status="BARU_DIDAFTARKAN",
    )
    await repository.upsert_broadcast_bot(bot_record)
    await repository.log_activity(
        action="BOT_ADDED",
        poster_id=None,
        user_id=user.id,
        details=f"Bot @{me_info['username']} added by Admin",
    )
    await state.clear()

    # Trigger auto sync permissions
    await multi_bot_service.sync_all_bots()

    bots = await repository.get_all_broadcast_bots()
    await wait_msg.edit_text(
        f"✅ *Bot Berhasil Didaftarkan!*\n\n"
        f"➤ *Username:* @{me_info['username']}\n"
        f"➤ *ID Bot:* `{me_info['id']}`\n"
        f"➤ *Peran Default:* `Bot Cadangan`\n\n"
        "Izin administrator telah diaudit otomatis.",
        parse_mode="Markdown",
        reply_markup=get_bot_management_keyboard(bots),
    )


@router.callback_query(F.data.startswith("bot_detail:"))
async def handle_bot_detail_menu(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    bot_id = int(callback.data.split(":")[1])
    bot = await repository.get_broadcast_bot_by_id(bot_id)
    if not bot:
        await callback.answer("Bot tidak ditemukan.", show_alert=True)
        return

    perms = bot.get_parsed_permissions()
    perm_lines = []
    for ch_name, p in perms.items():
        ok = p.get("ok", False)
        lbl = p.get("label", "UNKNOWN")
        ico = "✅" if ok else "⚠️"
        perm_lines.append(f"   ├ {ch_name}: {ico} `{lbl}`")

    perms_str = "\n".join(perm_lines) if perm_lines else "   └ _Belum diaudit (klik Sinkronisasi)_"

    text = (
        f"🤖 *DETAIL BOT: @{bot.bot_username}*\n\n"
        f"➤ *ID Bot:* `{bot.bot_id}`\n"
        f"➤ *Token:* `{bot.get_masked_token()}`\n"
        f"➤ *Peran Saat Ini:* *{bot.role.upper()}*\n"
        f"➤ *Status:* {'🟢 Terverifikasi' if bot.is_verified else '🟡 Perlu Hak Admin'}\n"
        f"➤ *Izin Saluran:*\n{perms_str}\n\n"
        "ᵎ!ᵎ _Pilih peran penugasan untuk bot ini:_"
    )

    kb = get_bot_detail_keyboard(bot.bot_id, bot.role)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("bot_set_role:"))
async def handle_bot_set_role(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    parts = callback.data.split(":")
    bot_id = int(parts[1])
    new_role = parts[2]

    await repository.set_broadcast_bot_role(bot_id, new_role)
    await repository.log_activity(
        action="BOT_ROLE_CHANGE",
        poster_id=None,
        user_id=user.id,
        details=f"Bot {bot_id} role updated to {new_role}",
    )

    await callback.answer(f"Peran bot diperbarui menjadi: {new_role.upper()}", show_alert=False)
    bot = await repository.get_broadcast_bot_by_id(bot_id)
    if bot:
        kb = get_bot_detail_keyboard(bot.bot_id, bot.role)
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass


@router.callback_query(F.data.startswith("bot_act:delete:"))
async def handle_bot_delete(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    bot_id = int(callback.data.split(":")[2])
    await repository.delete_broadcast_bot(bot_id)
    await repository.log_activity(
        action="BOT_DELETED",
        poster_id=None,
        user_id=user.id,
        details=f"Bot {bot_id} deleted by Admin",
    )

    await callback.answer("Bot berhasil dihapus.", show_alert=True)
    bots = await repository.get_all_broadcast_bots()
    kb = get_bot_management_keyboard(bots)
    try:
        await callback.message.edit_text(
            "🤖 *MANAJEMEN MULTI-BOT*\n\nBot telah dihapus. Daftar bot diperbarui:",
            reply_markup=kb,
            parse_mode="Markdown",
        )
    except Exception:
        pass


@router.callback_query(F.data == "admin_menu:broadcast_send")
async def handle_broadcast_send_start(
    callback: CallbackQuery,
    repository: Repository,
    settings: Settings,
    state: FSMContext,
):
    user = callback.from_user
    if not user or not is_admin_check(user.id, settings):
        await callback.answer("Akses ditolak.", show_alert=True)
        return

    channels = await repository.get_channel_settings()
    ch1_st = "🟢 ON" if (channels.channel_1_enabled and channels.channel_1_id) else "🔴 OFF / Belum Diatur"
    ch2_st = "🟢 ON" if (channels.channel_2_enabled and channels.channel_2_id) else "🔴 OFF / Belum Diatur"

    await state.set_state(AdminBroadcastSendStates.waiting_for_broadcast_content)
    text = (
        "📢 *KIRIM SIARAN PESAN KE CHANNEL*\n\n"
        "Pesan akan disebarkan berdasarkan aturan status channel saat ini:\n"
        f"➤ *Channel 1:* {ch1_st}\n"
        f"➤ *Channel 2:* {ch2_st}\n\n"
        "📌 *Ketentuan Logika Penyebaran (C.1 - C.4):*\n"
        "1. Jika Channel 1 ON & Channel 2 OFF -> hanya ke Channel 1.\n"
        "2. Jika Channel 1 OFF & Channel 2 ON -> hanya ke Channel 2.\n"
        "3. Jika Channel 1 ON & Channel 2 ON -> ke kedua channel.\n"
        "4. Jika kedua channel OFF -> pengiriman otomatis dibatalkan.\n\n"
        "Kirimkan teks pesan (atau foto dengan caption) yang ingin Anda sebarkan.\n"
        "Ketik /cancel untuk membatalkan."
    )
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@router.message(AdminBroadcastSendStates.waiting_for_broadcast_content)
async def handle_broadcast_content_input(
    message: Message,
    repository: Repository,
    multi_bot_service: MultiBotService,
    settings: Settings,
    state: FSMContext,
):
    user = message.from_user
    if not user or not is_admin_check(user.id, settings):
        return

    if message.text and message.text.strip().lower() == "/cancel":
        await state.clear()
        await message.answer("Batal mengirim siaran pesan.")
        return

    text_content = message.caption or message.text or ""
    photo_id = None
    media_type = None

    if message.photo:
        photo_id = message.photo[-1].file_id
        media_type = "photo"

    if not text_content and not photo_id:
        await message.answer("❌ Harap kirimkan pesan teks atau foto. Coba lagi atau /cancel:")
        return

    wait_msg = await message.answer("⏳ Memproses antrean dan menyebarkan ke channel aktif...")
    res = await multi_bot_service.broadcast_message_to_channels(
        text=text_content,
        media_file_id=photo_id,
        media_type=media_type,
        author_name=user.full_name or "Admin",
    )
    await state.clear()

    # Format result report
    if res.get("ok"):
        res_lines = ["✅ *SIARAN BERHASIL DISEBARKAN*\n"]
        for r in res.get("results", []):
            ch_name = r.get("channel")
            if r.get("ok"):
                res_lines.append(f"🟢 *{ch_name}*: Berhasil terkirim via `{r.get('bot')}` (Msg ID: `{r.get('message_id')}`)")
            else:
                res_lines.append(f"🔴 *{ch_name}*: Gagal (`{r.get('error')}`)")
        await wait_msg.edit_text("\n".join(res_lines), parse_mode="Markdown")
    else:
        await wait_msg.edit_text(
            f"❌ *Penyebaran Gagal!*\n{res.get('message', 'Tidak ada channel aktif.')}",
            parse_mode="Markdown",
        )
