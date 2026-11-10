"""
Unit tests for ASCHEN MEDIAPATNER schedule calculator and Indonesian date formatters.
Verifies all scheduling rules and edge cases from Section 5 & 6 of USER_REQUEST.
"""

from datetime import datetime
import pytz
import pytest
from mediapatner.services.scheduler_service import (
    calculate_next_wib_slot,
    format_indonesian_date,
    format_indonesian_day,
    format_indonesian_time,
    WIB_TZ,
)


def make_wib(year, month, day, hour, minute):
    return WIB_TZ.localize(datetime(year, month, day, hour, minute, 0))


class TestSchedulerCalculations:
    def test_senin_to_selasa(self):
        """Senin -> Selasa pukul 09.00 WIB"""
        # Monday 2026-11-09 at 14:00
        now = make_wib(2026, 11, 9, 14, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Selasa"
        assert time == "09.00"
        assert slot_dt.year == 2026 and slot_dt.month == 11 and slot_dt.day == 10
        assert slot_dt.hour == 9 and slot_dt.minute == 0

    def test_selasa_before_slot(self):
        """Selasa 08:30 -> Selasa pukul 09.00 WIB"""
        now = make_wib(2026, 11, 10, 8, 30)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Selasa"
        assert time == "09.00"
        assert slot_dt.day == 10

    def test_selasa_exact_slot(self):
        """Selasa 09:00 -> Selasa pukul 09.00 WIB (masuk slot saat proses memungkinkan)"""
        now = make_wib(2026, 11, 10, 9, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Selasa"
        assert time == "09.00"
        assert slot_dt.day == 10

    def test_selasa_after_slot_to_rabu(self):
        """Selasa pukul 10.00 -> Rabu pukul 12.00 WIB"""
        now = make_wib(2026, 11, 10, 10, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Rabu"
        assert time == "12.00"
        assert slot_dt.day == 11

    def test_rabu_after_slot_to_kamis(self):
        """Rabu pukul 13.00 -> Kamis pukul 09.00 WIB"""
        now = make_wib(2026, 11, 11, 13, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Kamis"
        assert time == "09.00"
        assert slot_dt.day == 12

    def test_kamis_after_slot_to_jumat(self):
        """Kamis pukul 11.00 -> Jumat pukul 12.00 WIB"""
        now = make_wib(2026, 11, 12, 11, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Jumat"
        assert time == "12.00"
        assert slot_dt.day == 13

    def test_jumat_after_slot_to_sabtu(self):
        """Jumat pukul 15.00 -> Sabtu pukul 20.00 WIB"""
        now = make_wib(2026, 11, 13, 15, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Sabtu"
        assert time == "20.00"
        assert slot_dt.day == 14

    def test_sabtu_before_slot(self):
        """Sabtu pukul 18.00 -> Sabtu pukul 20.00 WIB"""
        now = make_wib(2026, 11, 14, 18, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Sabtu"
        assert time == "20.00"
        assert slot_dt.day == 14

    def test_sabtu_after_slot_to_next_selasa(self):
        """Sabtu pukul 21.00 -> Selasa pukul 09.00 WIB"""
        now = make_wib(2026, 11, 14, 21, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Selasa"
        assert time == "09.00"
        # Tuesday next week is Nov 17
        assert slot_dt.day == 17

    def test_minggu_to_next_selasa(self):
        """Minggu pukul 12.00 -> Selasa pukul 09.00 WIB"""
        now = make_wib(2026, 11, 15, 12, 0)
        slot_dt, day, date, time = calculate_next_wib_slot(now)

        assert day == "Selasa"
        assert time == "09.00"
        assert slot_dt.day == 17


class TestIndonesianFormatting:
    def test_indonesian_date_format(self):
        dt = make_wib(2026, 11, 10, 9, 0)
        assert format_indonesian_date(dt) == "10 November 2026"
        assert format_indonesian_day(dt) == "Selasa"
        assert format_indonesian_time(dt) == "09.00"
