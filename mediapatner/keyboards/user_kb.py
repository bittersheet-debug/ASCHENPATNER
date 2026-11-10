"""
User keyboards and inline layouts for MEDIAPATNER BOT.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard() -> InlineKeyboardMarkup:
    """
    Section 2.A Start Button:
    [ 📩 MENGIRIM POSTER ]
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📩 MENGIRIM POSTER",
                    callback_data="cmd_submit_poster",
                )
            ]
        ]
    )


def get_submission_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Message 2 Keyboard:
    Removes redundant 'MENGIRIM POSTER' button and displays official schedule hours buttons
    along with 'MENU UTAMA' button.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏰ 09.00 WIB (Sel & Kam)",
                    callback_data="sched_info:09",
                ),
                InlineKeyboardButton(
                    text="⏰ 12.00 WIB (Rab & Jum)",
                    callback_data="sched_info:12",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏰ 20.00 WIB (Sabtu)",
                    callback_data="sched_info:20",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 MENU UTAMA",
                    callback_data="cmd_main_menu",
                )
            ],
        ]
    )


def get_view_channel_keyboard(channel_url: str = "https://t.me/ASCHENEO") -> InlineKeyboardMarkup:
    """
    Section 8 Channel Button:
    [ LIHAT CHANNEL @ASCHENEO ]
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="LIHAT CHANNEL @ASCHENEO",
                    url=channel_url,
                )
            ]
        ]
    )
