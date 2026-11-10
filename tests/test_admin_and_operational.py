"""
Unit tests for Operational Hours Service, Admin Device Management,
Reporting Target Chat configuration, and Interactive Poster Reports.
"""

import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime
import pytz

from mediapatner.database.db import Database
from mediapatner.database.repository import Repository
from mediapatner.database.models import (
    AdminDeviceRecord,
    PosterReportRecord,
    OperationalHoursConfig,
    PosterRecord,
)
from mediapatner.services.operational_service import check_submission_allowed, WIB_TZ


@pytest_asyncio.fixture
async def test_repo():
    test_id = uuid.uuid4().hex[:8]
    db_path = f"data/test_repo_{test_id}.db"

    db = Database(db_path=db_path)
    await db.init()
    repo = Repository(db)

    yield repo

    # Cleanup test database file safely
    for ext in ("", "-wal", "-shm"):
        fpath = db_path + ext
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except OSError:
                pass


class TestOperationalHours:
    def test_sunday_closed(self):
        config = OperationalHoursConfig(open_hour=6, close_hour=22, sunday_closed=True)
        sunday_dt = WIB_TZ.localize(datetime(2026, 11, 15, 12, 0, 0))
        assert sunday_dt.weekday() == 6

        allowed, reason, msg = check_submission_allowed(config, sunday_dt)
        assert allowed is False
        assert reason == "SUNDAY_CLOSED"
        assert "REQUEST POSTER CLOSED" in msg
        assert "Senin pukul 06.00 WIB" in msg

    def test_sunday_open_if_configured(self):
        config = OperationalHoursConfig(open_hour=6, close_hour=22, sunday_closed=False)
        sunday_dt = WIB_TZ.localize(datetime(2026, 11, 15, 12, 0, 0))
        allowed, reason, msg = check_submission_allowed(config, sunday_dt)
        assert allowed is True
        assert reason == "OPEN"

    def test_before_open_hours_monday(self):
        config = OperationalHoursConfig(open_hour=6, close_hour=22, sunday_closed=True)
        monday_dt = WIB_TZ.localize(datetime(2026, 11, 16, 5, 30, 0))
        allowed, reason, msg = check_submission_allowed(config, monday_dt)
        assert allowed is False
        assert reason == "BEFORE_HOURS"
        assert "REQUEST POSTER BELUM DIBUKA" in msg
        assert "pukul 06.00 WIB" in msg

    def test_exact_open_hour_monday(self):
        config = OperationalHoursConfig(open_hour=6, close_hour=22, sunday_closed=True)
        monday_open = WIB_TZ.localize(datetime(2026, 11, 16, 6, 0, 0))
        allowed, reason, msg = check_submission_allowed(config, monday_open)
        assert allowed is True
        assert reason == "OPEN"

    def test_during_operating_hours(self):
        config = OperationalHoursConfig(open_hour=6, close_hour=22, sunday_closed=True)
        wed_noon = WIB_TZ.localize(datetime(2026, 11, 11, 14, 0, 0))
        allowed, reason, msg = check_submission_allowed(config, wed_noon)
        assert allowed is True
        assert reason == "OPEN"

    def test_after_close_hour_saturday(self):
        config = OperationalHoursConfig(open_hour=6, close_hour=22, sunday_closed=True)
        sat_night = WIB_TZ.localize(datetime(2026, 11, 14, 22, 1, 0))
        allowed, reason, msg = check_submission_allowed(config, sat_night)
        assert allowed is False
        assert reason == "AFTER_HOURS"
        assert "REQUEST POSTER TELAH DITUTUP" in msg


class TestAdminDeviceManagement:
    @pytest.mark.asyncio
    async def test_device_registration_and_revocation(self, test_repo: Repository):
        await test_repo.upsert_user(999, "admin_user", "Admin Master")

        device = AdminDeviceRecord(
            device_id="DEV-ASCHEN-A1B2",
            admin_id=999,
            admin_name="Admin Master",
            admin_username="admin_user",
            phone_number="+62812****5678",
            device_model="Telegram Desktop",
            session_token="secret_token_123",
            status="Active",
            login_at="10 November 2026, 11.00",
            last_active="2026-11-10 11:00:00",
        )
        await test_repo.register_device(device)

        devices = await test_repo.get_active_devices()
        assert len(devices) == 1
        assert devices[0].device_id == "DEV-ASCHEN-A1B2"
        assert devices[0].phone_number == "+62812****5678"

        revoked = await test_repo.revoke_device("DEV-ASCHEN-A1B2")
        assert revoked is True

        devices_after = await test_repo.get_active_devices()
        assert len(devices_after) == 0

    @pytest.mark.asyncio
    async def test_revoke_all_devices(self, test_repo: Repository):
        await test_repo.upsert_user(999, "admin_user", "Admin Master")

        d1 = AdminDeviceRecord(
            device_id="DEV-ASCHEN-0001",
            admin_id=999,
            admin_name="Admin Master",
            admin_username="admin_user",
            phone_number="+62812****0001",
            device_model="Telegram Mobile",
            session_token="tok1",
            status="Active",
            login_at="10 Nov 2026",
            last_active="2026-11-10",
        )
        d2 = AdminDeviceRecord(
            device_id="DEV-ASCHEN-0002",
            admin_id=999,
            admin_name="Admin Master",
            admin_username="admin_user",
            phone_number="+62812****0002",
            device_model="Telegram Web",
            session_token="tok2",
            status="Active",
            login_at="10 Nov 2026",
            last_active="2026-11-10",
        )
        await test_repo.register_device(d1)
        await test_repo.register_device(d2)

        active = await test_repo.get_active_devices()
        assert len(active) == 2

        count = await test_repo.revoke_all_devices()
        assert count == 2

        active_after = await test_repo.get_active_devices()
        assert len(active_after) == 0


class TestPosterReportsAndAntiDoubleProcessing:
    @pytest.mark.asyncio
    async def test_report_lifecycle_and_anti_double_processing(self, test_repo: Repository):
        await test_repo.upsert_user(777, "partner777", "Partner 777")

        poster = PosterRecord(
            id=None,
            sender_id=777,
            sender_name="Partner 777",
            sender_username="partner777",
            source_link=None,
            source_chat_id="@mychan",
            source_message_id=50,
            media_type="photo",
            file_id="photo123",
            caption="Poster Event",
            raw_data=None,
            status="KEEP",
            scheduled_slot="2026-11-10T09:00:00",
            slot_day="Selasa",
            slot_date="10 November 2026",
            slot_time="09.00",
        )
        poster_id = await test_repo.create_poster(poster)

        report = PosterReportRecord(
            id=None,
            poster_id=poster_id,
            report_chat_id="-1004479248551",
            report_message_id=1234,
            sender_id=777,
            sender_name="Partner 777",
            sender_username="partner777",
            institution_name="Komunitas Mahasiswa",
            status="Menunggu Diproses",
        )
        report_id = await test_repo.create_poster_report(report)
        assert report_id > 0

        # First admin accepts
        accepted = await test_repo.update_poster_report_status(
            report_id=report_id,
            status="✅ Diterima",
            admin_id=1,
            admin_name="Admin One",
            action_note="Accepted by Admin One",
        )
        assert accepted is True

        # Second admin tries to reject or accept -> should fail (anti double-processing)
        double_action = await test_repo.update_poster_report_status(
            report_id=report_id,
            status="❌ Ditolak",
            admin_id=2,
            admin_name="Admin Two",
            action_note="Attempted double action",
        )
        assert double_action is False

        # Status remains "✅ Diterima"
        fetched_report = await test_repo.get_poster_report(report_id)
        assert fetched_report.status == "✅ Diterima"
        assert fetched_report.processed_by_id == 1
        assert fetched_report.processed_by_name == "Admin One"


class TestConfigurableSettings:
    @pytest.mark.asyncio
    async def test_report_chat_settings(self, test_repo: Repository):
        default_chat = await test_repo.get_report_chat_id()
        assert default_chat == "-1004479248551"

        await test_repo.set_report_chat_id("-100999888777", "CUSTOM_GROUP")
        updated_chat = await test_repo.get_report_chat_id()
        assert updated_chat == "-100999888777"
        assert await test_repo.get_report_chat_type() == "CUSTOM_GROUP"

    @pytest.mark.asyncio
    async def test_operational_settings_persistence(self, test_repo: Repository):
        default_cfg = await test_repo.get_operational_config()
        assert default_cfg.open_hour == 6
        assert default_cfg.close_hour == 22
        assert default_cfg.sunday_closed is True

        await test_repo.set_operational_config(open_hour=7, close_hour=20, sunday_closed=False)
        updated_cfg = await test_repo.get_operational_config()
        assert updated_cfg.open_hour == 7
        assert updated_cfg.close_hour == 20
        assert updated_cfg.sunday_closed is False

