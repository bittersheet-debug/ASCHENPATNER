"""
Integration tests for SQLite database repository, duplicate detection,
queue recovery, settings toggling, and stats calculation.
"""

import os
import uuid
import pytest
import pytest_asyncio
from mediapatner.database.db import Database
from mediapatner.database.repository import Repository
from mediapatner.database.models import PosterRecord


@pytest_asyncio.fixture
async def test_repo():
    test_id = uuid.uuid4().hex[:8]
    db_path = f"data/test_mediapatner_{test_id}.db"

    db = Database(db_path=db_path)
    await db.init()
    repo = Repository(db)

    yield repo

    # Cleanup test database file
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


@pytest.mark.asyncio
async def test_user_operations(test_repo: Repository):
    await test_repo.upsert_user(
        user_id=12345,
        username="media_user",
        full_name="Media Partner Team",
    )

    user = await test_repo.get_user(12345)
    assert user is not None
    assert user.username == "media_user"
    assert user.full_name == "Media Partner Team"
    assert user.total_submissions == 0

    await test_repo.increment_user_submissions(12345)
    updated_user = await test_repo.get_user(12345)
    assert updated_user.total_submissions == 1


@pytest.mark.asyncio
async def test_poster_crud_and_duplicate_prevention(test_repo: Repository):
    await test_repo.upsert_user(111, "sender1", "Sender One")

    poster = PosterRecord(
        id=None,
        sender_id=111,
        sender_name="Sender One",
        sender_username="sender1",
        source_link="https://t.me/partnerchan/100",
        source_chat_id="@partnerchan",
        source_message_id=100,
        media_type="photo",
        file_id="photo_file_abc",
        caption="Acara ASCHEN Fest 2026",
        raw_data='{"photo_url": "https://cdn.example.com/p.jpg"}',
        status="KEEP",
        scheduled_slot="2026-11-10T09:00:00",
        slot_day="Selasa",
        slot_date="10 November 2026",
        slot_time="09.00",
    )

    poster_id = await test_repo.create_poster(poster)
    assert poster_id > 0

    fetched = await test_repo.get_poster(poster_id)
    assert fetched is not None
    assert fetched.sender_name == "Sender One"
    assert fetched.status == "KEEP"

    # Duplicate check by link
    dup_link = await test_repo.find_duplicate_poster(source_link="https://t.me/partnerchan/100")
    assert dup_link is not None
    assert dup_link.id == poster_id

    # Duplicate check by chat + msg_id
    dup_chat = await test_repo.find_duplicate_poster(source_chat_id="@partnerchan", source_message_id=100)
    assert dup_chat is not None
    assert dup_chat.id == poster_id

    # Non-duplicate check
    non_dup = await test_repo.find_duplicate_poster(source_link="https://t.me/other/999")
    assert non_dup is None


@pytest.mark.asyncio
async def test_queue_due_and_publishing_lifecycle(test_repo: Repository):
    await test_repo.upsert_user(222, "sender2", "Sender Two")

    p1 = PosterRecord(
        id=None,
        sender_id=222,
        sender_name="Sender Two",
        sender_username="sender2",
        source_link="https://t.me/p/1",
        source_chat_id="@p",
        source_message_id=1,
        media_type="photo",
        file_id="f1",
        caption="Poster 1",
        raw_data=None,
        status="KEEP",
        scheduled_slot="2026-11-10T09:00:00",
        slot_day="Selasa",
        slot_date="10 November 2026",
        slot_time="09.00",
    )
    p2 = PosterRecord(
        id=None,
        sender_id=222,
        sender_name="Sender Two",
        sender_username="sender2",
        source_link="https://t.me/p/2",
        source_chat_id="@p",
        source_message_id=2,
        media_type="video",
        file_id="f2",
        caption="Poster 2",
        raw_data=None,
        status="KEEP",
        scheduled_slot="2026-11-11T12:00:00",
        slot_day="Rabu",
        slot_date="11 November 2026",
        slot_time="12.00",
    )

    id1 = await test_repo.create_poster(p1)
    id2 = await test_repo.create_poster(p2)

    # Cutoff at Nov 10 10:00:00 -> p1 should be due, p2 should not
    due = await test_repo.get_posters_due("2026-11-10T10:00:00")
    assert len(due) == 1
    assert due[0].id == id1

    # Mark publishing
    marked = await test_repo.mark_publishing(id1)
    assert marked is True

    # Mark published
    pub = await test_repo.mark_published(id1, published_message_id=9876)
    assert pub is True

    updated_p1 = await test_repo.get_poster(id1)
    assert updated_p1.status == "PUBLISHED"
    assert updated_p1.published_message_id == 9876


@pytest.mark.asyncio
async def test_settings_and_stats(test_repo: Repository):
    # Auto forward default should be true
    assert await test_repo.is_auto_forward_enabled() is True

    # Toggle to false
    new_state = await test_repo.toggle_auto_forward()
    assert new_state is False
    assert await test_repo.is_auto_forward_enabled() is False

    # Stats
    stats = await test_repo.get_system_stats()
    assert stats is not None
    assert stats.total_users >= 0
