"""
Unit tests for notification message layouts, templates, and keyboards.
Ensures exact compliance with sections 2, 7, 8, 9, 10 in USER_REQUEST.
"""

import pytest
from mediapatner.keyboards.user_kb import (
    get_start_keyboard,
    get_submission_menu_keyboard,
    get_view_channel_keyboard,
)
from mediapatner.keyboards.admin_kb import (
    get_admin_main_keyboard,
    get_settings_keyboard,
)


class TestKeyboards:
    def test_start_keyboard(self):
        kb = get_start_keyboard()
        buttons = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "📩 MENGIRIM POSTER" in buttons

    def test_submission_menu_keyboard(self):
        kb = get_submission_menu_keyboard()
        buttons = [btn.text for row in kb.inline_keyboard for btn in row]
        # Button 'MENGIRIM POSTER' is removed from message 2 as requested
        assert "📩 MENGIRIM POSTER" not in buttons
        # Replaced with hours buttons and Menu Utama
        assert any("09.00" in b for b in buttons)
        assert any("12.00" in b for b in buttons)
        assert any("20.00" in b for b in buttons)
        assert "🏠 MENU UTAMA" in buttons

    def test_view_channel_keyboard(self):
        kb = get_view_channel_keyboard("https://t.me/ASCHENEO")
        btn = kb.inline_keyboard[0][0]
        assert "LIHAT CHANNEL @ASCHENEO" in btn.text
        assert btn.url == "https://t.me/ASCHENEO"

    def test_admin_main_keyboard(self):
        kb = get_admin_main_keyboard()
        texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("Dashboard Overview" in t for t in texts)
        assert any("Login Device" in t for t in texts)
        assert any("Daftar Device" in t for t in texts)
        assert any("Pilih Chat Pelaporan" in t for t in texts)
        assert any("Jadwal Operasional" in t for t in texts)
        assert any("Keep Queue" in t for t in texts)
        assert any("Scheduled Posters" in t for t in texts)
        assert any("Published Posters" in t for t in texts)
        assert any("Failed Posters" in t for t in texts)
        assert any("Riwayat Request Poster" in t for t in texts)
        assert any("User Activity" in t for t in texts)
        assert any("Bot Settings" in t for t in texts)

    def test_permanent_notification_channel_locked(self):
        kb = get_settings_keyboard(auto_forward_enabled=True)
        texts = [btn.text for row in kb.inline_keyboard for btn in row]
        # Must show PERMANENT lock
        assert any("PERMANENT" in t for t in texts)
