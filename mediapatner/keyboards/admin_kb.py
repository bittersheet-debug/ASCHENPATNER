"""
Admin Dashboard Keyboards for MEDIAPATNER BOT.
Provides interactive inline buttons for all admin management menus:
- Device Login & Active Devices Management
- Configurable Reporting Target Chat
- Request Poster History
- Operational Hours (WIB) Configuration
- Keep, Scheduled, Published, Failed Queues
- Bot Settings & Session Logout
"""

from typing import List, Optional, Tuple
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from mediapatner.database.models import (
    AdminDeviceRecord,
    OperationalHoursConfig,
    PosterReportRecord,
    BroadcastBotRecord,
    ChannelSettings,
)


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Main Admin Dashboard Navigation Menu with 8 Unified Management Systems."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Dashboard Overview", callback_data="admin_menu:overview"),
            ],
            [
                InlineKeyboardButton(text="📢 Kontrol Channel & Multi-Bot", callback_data="admin_menu:channel_control"),
            ],
            [
                InlineKeyboardButton(text="📱 Login Device", callback_data="admin_menu:login_device"),
                InlineKeyboardButton(text="👥 Daftar Device", callback_data="admin_menu:devices"),
            ],
            [
                InlineKeyboardButton(text="📩 Pilih Chat Pelaporan", callback_data="admin_menu:choose_report_chat"),
                InlineKeyboardButton(text="⏰ Jadwal Operasional", callback_data="admin_menu:op_hours"),
            ],
            [
                InlineKeyboardButton(text="📥 Keep Queue", callback_data="admin_menu:keep:0"),
                InlineKeyboardButton(text="🗓 Scheduled Posters", callback_data="admin_menu:scheduled:0"),
            ],
            [
                InlineKeyboardButton(text="✅ Published Posters", callback_data="admin_menu:published:0"),
                InlineKeyboardButton(text="❌ Failed Posters", callback_data="admin_menu:failed:0"),
            ],
            [
                InlineKeyboardButton(text="📑 Riwayat Request Poster", callback_data="admin_menu:requests:0"),
                InlineKeyboardButton(text="📜 User Activity", callback_data="admin_menu:activity:0"),
            ],
            [
                InlineKeyboardButton(text="📡 Ping Channel Siaran", callback_data="admin_menu:ping_channel"),
                InlineKeyboardButton(text="⚙️ Bot Settings", callback_data="admin_menu:settings"),
            ],
            [
                InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_menu:overview"),
                InlineKeyboardButton(text="🔒 Logout Sesi", callback_data="admin_act:logout"),
            ],
        ]
    )


def get_back_to_admin_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="🔙 Menu Admin", callback_data="admin_menu:home")


def get_login_phone_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Batal Login", callback_data="admin_login:cancel")]
        ]
    )


def get_login_otp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Kirim Ulang Kode", callback_data="admin_login:resend_code")],
            [InlineKeyboardButton(text="❌ Batal Login", callback_data="admin_login:cancel")],
        ]
    )


def get_login_2fa_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Batal Login", callback_data="admin_login:cancel")]
        ]
    )


def get_login_success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📩 Pilih Chat Pelaporan",
                    callback_data="admin_menu:choose_report_chat",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Dashboard Admin",
                    callback_data="admin_menu:home",
                ),
                InlineKeyboardButton(
                    text="📱 Daftar Device",
                    callback_data="admin_menu:devices",
                ),
            ],
        ]
    )


def get_device_list_keyboard(devices: List[AdminDeviceRecord]) -> InlineKeyboardMarkup:
    rows = []
    for d in devices:
        masked = d.phone_number
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"📱 {d.device_id} ({masked})",
                    callback_data=f"device_info:{d.device_id}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🚪 Logout {d.device_id[-4:]}",
                    callback_data=f"device_act:logout:{d.device_id}",
                ),
                InlineKeyboardButton(
                    text="🚫 Cabut Akses",
                    callback_data=f"device_act:revoke:{d.device_id}",
                ),
            ]
        )

    if devices:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🛑 Akhiri Seluruh Session Aktif",
                    callback_data="device_act:revoke_all",
                )
            ]
        )
    rows.append([get_back_to_admin_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_report_chat_keyboard(current_chat: str, current_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Channel Notifikasi (-1004479248551)",
                    callback_data="report_chat:set_permanent",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Set Chat Pribadi Saya",
                    callback_data="report_chat:set_private",
                ),
                InlineKeyboardButton(
                    text="👥 Set Chat Ini",
                    callback_data="report_chat:set_current",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Input Custom Chat / Group ID",
                    callback_data="report_chat:input_custom",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧪 Test Kirim Laporan ke Chat",
                    callback_data="report_chat:test_send",
                )
            ],
            [get_back_to_admin_button()],
        ]
    )


def get_operational_settings_keyboard(config: OperationalHoursConfig) -> InlineKeyboardMarkup:
    sun_label = "🏖 Hari Minggu: [ TUTUP ✅ ]" if config.sunday_closed else "🏖 Hari Minggu: [ BUKA ❌ ]"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⏰ Jam Buka: {config.open_hour:02d}.00 WIB",
                    callback_data="noop_open_info",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Buka 06.00",
                    callback_data="op_set:open:6",
                ),
                InlineKeyboardButton(
                    text="Buka 07.00",
                    callback_data="op_set:open:7",
                ),
                InlineKeyboardButton(
                    text="Buka 08.00",
                    callback_data="op_set:open:8",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"⏰ Jam Tutup Saat Ini: {config.close_hour:02d}.00 WIB",
                    callback_data="noop_close_info",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Tutup 20.00",
                    callback_data="op_set:close:20",
                ),
                InlineKeyboardButton(
                    text="Tutup 21.00",
                    callback_data="op_set:close:21",
                ),
                InlineKeyboardButton(
                    text="Tutup 22.00",
                    callback_data="op_set:close:22",
                ),
                InlineKeyboardButton(
                    text="Tutup 23.00",
                    callback_data="op_set:close:23",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=sun_label,
                    callback_data="op_set:toggle_sunday",
                )
            ],
            [get_back_to_admin_button()],
        ]
    )


def get_request_list_keyboard(
    items: List[Tuple[int, str]], page: int, total_pages: int
) -> InlineKeyboardMarkup:
    keyboard = []
    for report_id, label in items:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"request_detail:{report_id}:{page}",
                )
            ]
        )

    nav_row = get_pagination_row("requests", page, total_pages)
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([get_back_to_admin_button()])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_request_detail_keyboard(
    report_id: int, status: str, page: int, poster_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    buttons = []
    p_id = poster_id if poster_id is not None else 0
    if status in ("Menunggu Diproses", "Diterima", "KEEP"):
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🚀 Sebar Duluan ke Channel",
                    callback_data=f"rpt_act:{report_id}:publish_now:{p_id}",
                )
            ]
        )
    if status == "Menunggu Diproses":
        buttons.append(
            [
                InlineKeyboardButton(
                    text="✅ Terima Pengajuan",
                    callback_data=f"rpt_act:{report_id}:accept",
                ),
                InlineKeyboardButton(
                    text="❌ Tolak Pengajuan",
                    callback_data=f"rpt_act:{report_id}:reject",
                ),
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📌 Tandai Selesai",
                    callback_data=f"rpt_act:{report_id}:complete",
                ),
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Kembali ke Daftar Request",
                callback_data=f"admin_menu:requests:{page}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pagination_row(
    menu_name: str, current_page: int, total_pages: int
) -> List[InlineKeyboardButton]:
    """Generates standard pagination controls for lists."""
    row = []
    if current_page > 0:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"admin_menu:{menu_name}:{current_page - 1}",
            )
        )

    row.append(
        InlineKeyboardButton(
            text=f"📄 {current_page + 1}/{max(1, total_pages)}",
            callback_data="noop",
        )
    )

    if current_page + 1 < total_pages:
        row.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"admin_menu:{menu_name}:{current_page + 1}",
            )
        )
    return row


def get_poster_list_keyboard(
    items: List[tuple], menu_name: str, page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """
    Builds keyboard for list of posters with clickable items and pagination.
    items: list of (poster_id, label)
    """
    keyboard = []
    for poster_id, label in items:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"poster_detail:{poster_id}:{menu_name}:{page}",
                )
            ]
        )

    # Pagination controls
    nav_row = get_pagination_row(menu_name, page, total_pages)
    if nav_row:
        keyboard.append(nav_row)

    # Back button
    keyboard.append([get_back_to_admin_button()])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_poster_detail_keyboard(
    poster_id: int, status: str, return_menu: str, page: int, target_label: str = ""
) -> InlineKeyboardMarkup:
    """Management action buttons for a single poster with channel selection."""
    keyboard = []

    # Publish now buttons with channel selection
    if status in ("KEEP", "SCHEDULED", "FAILED"):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🚀 Sebar Duluan (Pilih Saluran)",
                    callback_data=f"poster_act:choose_channel:{poster_id}",
                )
            ]
        )
        display_tgt = target_label if target_label else "Sesuai Pengaturan Otomatis"
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"🎯 Target Saluran: [{display_tgt}]",
                    callback_data=f"poster_act:set_target_menu:{poster_id}",
                )
            ]
        )

    # Reschedule button (if not published)
    if status in ("KEEP", "SCHEDULED", "FAILED"):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🗓 Ubah Jadwal",
                    callback_data=f"poster_act:reschedule_menu:{poster_id}",
                )
            ]
        )

    # Retry button if failed
    if status == "FAILED":
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🔄 Coba Ulang (Retry)",
                    callback_data=f"poster_act:retry:{poster_id}",
                )
            ]
        )

    # Delete / Cancel button
    keyboard.append(
        [
            InlineKeyboardButton(
                text="🗑 Hapus dari Antrean",
                callback_data=f"poster_act:delete:{poster_id}",
            )
        ]
    )

    # Back to list
    keyboard.append(
        [
            InlineKeyboardButton(
                text="🔙 Kembali ke Daftar",
                callback_data=f"admin_menu:{return_menu}:{page}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_poster_publish_target_keyboard(poster_id: int) -> InlineKeyboardMarkup:
    """Interactive inline keyboard to choose destination channel when publishing immediately."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Sebar ke Channel Utama (-1002123283346)",
                    callback_data=f"poster_publish_to:{poster_id}:main",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼️ Sebar ke Channel Sebar/Poster (-1003512801822)",
                    callback_data=f"poster_publish_to:{poster_id}:poster",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Sebar ke Utama & Sebar (Keduanya)",
                    callback_data=f"poster_publish_to:{poster_id}:both",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Sebar ke Semua Saluran Aktif (Multi-Channel)",
                    callback_data=f"poster_publish_to:{poster_id}:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Batal / Kembali",
                    callback_data=f"poster_detail:{poster_id}:keep:0",
                )
            ],
        ]
    )


def get_target_selection_keyboard(
    current_target: str, context: str = "global", poster_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """Inline keyboard for setting the auto-publish target (global or per-poster)."""
    def mark(t: str) -> str:
        return " (Dipilih ✅)" if t == current_target else ""

    prefix = f"poster_set_target:{poster_id}" if context == "poster" else "chan_set_target"
    back_cb = f"poster_detail:{poster_id}:keep:0" if context == "poster" else "admin_menu:channel_control"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📢 Hanya Channel Utama{mark('main')}",
                    callback_data=f"{prefix}:main",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🖼️ Hanya Channel Sebar (Poster){mark('poster')}",
                    callback_data=f"{prefix}:poster",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🌐 Channel Utama & Channel Sebar{mark('both')}",
                    callback_data=f"{prefix}:both",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⚡ Semua Channel Aktif (Multi-Channel){mark('all')}",
                    callback_data=f"{prefix}:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Kembali",
                    callback_data=back_cb,
                )
            ],
        ]
    )


def get_reschedule_options_keyboard(poster_id: int) -> InlineKeyboardMarkup:
    """Options for rescheduling a poster to one of the upcoming official slots."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏭ Slot Resmi Terdekat Berikutnya",
                    callback_data=f"resched_set:{poster_id}:next",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Selasa 09.00 WIB",
                    callback_data=f"resched_set:{poster_id}:tue_09",
                ),
                InlineKeyboardButton(
                    text="Rabu 12.00 WIB",
                    callback_data=f"resched_set:{poster_id}:wed_12",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Kamis 09.00 WIB",
                    callback_data=f"resched_set:{poster_id}:thu_09",
                ),
                InlineKeyboardButton(
                    text="Jumat 12.00 WIB",
                    callback_data=f"resched_set:{poster_id}:fri_12",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Sabtu 20.00 WIB",
                    callback_data=f"resched_set:{poster_id}:sat_20",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Batal",
                    callback_data=f"poster_detail:{poster_id}:keep:0",
                )
            ],
        ]
    )


def get_settings_keyboard(auto_forward_enabled: bool) -> InlineKeyboardMarkup:
    """Settings screen keyboard (Notification channel is permanently locked and non-editable)."""
    toggle_text = "🔁 Auto Forward: [ AKTIF ✅ ]" if auto_forward_enabled else "🔁 Auto Forward: [ NONAKTIF ❌ ]"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data="admin_act:toggle_auto_forward",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Notification Channel: PERMANENT",
                    callback_data="noop_permanent_info",
                )
            ],
            [get_back_to_admin_button()],
        ]
    )


def get_ping_channel_keyboard() -> InlineKeyboardMarkup:
    """Diagnostic keyboard for broadcast channel ping."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Cek Ulang Ping Channel",
                    callback_data="admin_menu:ping_channel",
                )
            ],
            [get_back_to_admin_button()],
        ]
    )


# ------------------ CHANNEL CONTROL & MULTI-BOT KEYBOARDS ------------------

def get_channel_control_keyboard(channels: ChannelSettings) -> InlineKeyboardMarkup:
    """
    Dashboard Kontrol Channel with dynamic toggle labels matching requirement B:
    - 🟢 AKTIFKAN CHANNEL 1 / 🔴 NONAKTIFKAN CHANNEL 1
    - 🟢 AKTIFKAN CHANNEL 2 / 🔴 NONAKTIFKAN CHANNEL 2
    - 🟢 AKTIFKAN CHANNEL POSTER / 🔴 NONAKTIFKAN CHANNEL POSTER
    - 🔄 SINKRONISASI BOT
    - ⚙️ PENGATURAN CHANNEL
    - 📊 RIWAYAT PENYEBARAN
    """
    # Button 1: Channel 1
    btn_ch1 = (
        InlineKeyboardButton(text="🔴 NONAKTIFKAN CHANNEL 1", callback_data="chan_toggle:ch1:off")
        if channels.channel_1_enabled
        else InlineKeyboardButton(text="🟢 AKTIFKAN CHANNEL 1", callback_data="chan_toggle:ch1:on")
    )

    # Button 2: Channel 2
    btn_ch2 = (
        InlineKeyboardButton(text="🔴 NONAKTIFKAN CHANNEL 2", callback_data="chan_toggle:ch2:off")
        if channels.channel_2_enabled
        else InlineKeyboardButton(text="🟢 AKTIFKAN CHANNEL 2", callback_data="chan_toggle:ch2:on")
    )

    # Button 3: Channel Poster
    btn_poster = (
        InlineKeyboardButton(text="🔴 NONAKTIFKAN CHANNEL POSTER", callback_data="chan_toggle:poster:off")
        if channels.poster_enabled
        else InlineKeyboardButton(text="🟢 AKTIFKAN CHANNEL POSTER", callback_data="chan_toggle:poster:on")
    )

    target_labels = {
        "main": "Hanya Utama 📢",
        "poster": "Hanya Sebar 🖼️",
        "both": "Utama & Sebar 🌐",
        "all": "Semua Saluran ⚡",
    }
    tgt_text = target_labels.get(channels.auto_publish_target, "Utama & Sebar 🌐")

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn_ch1],
            [btn_ch2],
            [btn_poster],
            [
                InlineKeyboardButton(
                    text=f"🎯 Target Sebar Otomatis: [{tgt_text}]",
                    callback_data="chan_menu:target_select",
                )
            ],
            [
                InlineKeyboardButton(text="🔄 SINKRONISASI BOT", callback_data="admin_act:sync_bots"),
                InlineKeyboardButton(text="⚙️ PENGATURAN CHANNEL", callback_data="admin_menu:chan_settings"),
            ],
            [
                InlineKeyboardButton(text="📊 RIWAYAT PENYEBARAN", callback_data="admin_menu:broadcast_history:0"),
                InlineKeyboardButton(text="🤖 MANAJEMEN BOT", callback_data="admin_menu:bot_mgmt"),
            ],
            [
                InlineKeyboardButton(text="📢 KIRIM SIARAN PESAN", callback_data="admin_menu:broadcast_send"),
            ],
            [get_back_to_admin_button()],
        ]
    )


def get_channel_settings_keyboard(channels: ChannelSettings) -> InlineKeyboardMarkup:
    """Settings menu for Channel 1 and Channel 2 IDs."""
    ch1_label = f"ID: {channels.channel_1_id}" if channels.channel_1_id else "Belum Diatur"
    ch2_label = f"ID: {channels.channel_2_id}" if channels.channel_2_id else "Belum Diatur"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✏️ Atur Channel 1 ({ch1_label})",
                    callback_data="chan_set_id:ch1",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"✏️ Atur Channel 2 ({ch2_label})",
                    callback_data="chan_set_id:ch2",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Channel Utama: -1002123283346 (Tetap)",
                    callback_data="noop_channel_main_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Channel Poster: -1003512801822 (Tetap)",
                    callback_data="noop_channel_poster_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Kembali ke Kontrol Channel",
                    callback_data="admin_menu:channel_control",
                )
            ],
        ]
    )


def get_broadcast_history_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Paginated navigation for broadcast history monitoring."""
    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Sebelumnya", callback_data=f"admin_menu:broadcast_history:{page - 1}"
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"Hal {page + 1}/{max(1, total_pages)}",
            callback_data="noop_history_page",
        )
    )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Berikutnya ▶️", callback_data=f"admin_menu:broadcast_history:{page + 1}"
            )
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            nav_row,
            [
                InlineKeyboardButton(
                    text="🔄 Segarkan Riwayat",
                    callback_data=f"admin_menu:broadcast_history:{page}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Kembali ke Kontrol Channel",
                    callback_data="admin_menu:channel_control",
                )
            ],
        ]
    )


def get_bot_management_keyboard(bots: List[BroadcastBotRecord]) -> InlineKeyboardMarkup:
    """Lists registered bots and shows add/sync options."""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Tambah Bot Baru", callback_data="bot_act:add"),
            InlineKeyboardButton(text="🔄 Sinkronisasi Izin", callback_data="admin_act:sync_bots"),
        ]
    ]

    for b in bots:
        status_ico = "🟢" if b.is_verified else "🟡"
        role_map = {
            "channel_1": "CH 1",
            "channel_2": "CH 2",
            "poster": "POSTER",
            "cadangan": "CADANGAN",
        }
        role_label = role_map.get(b.role, b.role.upper())
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{status_ico} @{b.bot_username} — [{role_label}]",
                    callback_data=f"bot_detail:{b.bot_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="🔙 Kembali ke Kontrol Channel",
                callback_data="admin_menu:channel_control",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_bot_detail_keyboard(bot_id: int, current_role: str) -> InlineKeyboardMarkup:
    """Role assignment and removal options for a specific bot."""
    def check_mark(r: str) -> str:
        return " (Aktif)" if r == current_role else ""

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎯 Jadikan Bot Channel 1{check_mark('channel_1')}",
                    callback_data=f"bot_set_role:{bot_id}:channel_1",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 Jadikan Bot Channel 2{check_mark('channel_2')}",
                    callback_data=f"bot_set_role:{bot_id}:channel_2",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 Jadikan Bot Poster{check_mark('poster')}",
                    callback_data=f"bot_set_role:{bot_id}:poster",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🛡 Jadikan Bot Cadangan{check_mark('cadangan')}",
                    callback_data=f"bot_set_role:{bot_id}:cadangan",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Hapus Bot dari Sistem",
                    callback_data=f"bot_act:delete:{bot_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Kembali ke Daftar Bot",
                    callback_data="admin_menu:bot_mgmt",
                ),
            ],
        ]
    )

