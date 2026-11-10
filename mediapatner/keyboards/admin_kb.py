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
from mediapatner.database.models import AdminDeviceRecord, OperationalHoursConfig, PosterReportRecord


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Main Admin Dashboard Navigation Menu with 8 Unified Management Systems."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Dashboard Overview", callback_data="admin_menu:overview"),
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
    report_id: int, status: str, page: int
) -> InlineKeyboardMarkup:
    buttons = []
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
    poster_id: int, status: str, return_menu: str, page: int
) -> InlineKeyboardMarkup:
    """Management action buttons for a single poster."""
    keyboard = []

    # Publish now button (if not already published)
    if status in ("KEEP", "SCHEDULED", "FAILED"):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="🚀 Publikasi Sekarang",
                    callback_data=f"poster_act:publish:{poster_id}",
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

