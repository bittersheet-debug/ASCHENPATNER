"""
Data models and dataclasses for MEDIAPATNER bot database records.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any
import json


@dataclass
class UserRecord:
    user_id: int
    username: Optional[str]
    full_name: str
    first_seen: str
    last_seen: str
    total_submissions: int = 0


@dataclass
class PosterRecord:
    id: Optional[int]
    sender_id: int
    sender_name: str
    sender_username: Optional[str]
    source_link: Optional[str]
    source_chat_id: Optional[str]
    source_message_id: Optional[int]
    media_type: Optional[str]  # 'photo', 'video', 'document', 'forward', 'text'
    file_id: Optional[str]
    caption: Optional[str]
    raw_data: Optional[str]
    status: str  # 'KEEP', 'SCHEDULED', 'PUBLISHING', 'PUBLISHED', 'FAILED', 'CANCELLED'
    scheduled_slot: str  # ISO string in WIB
    slot_day: str  # e.g., 'Selasa'
    slot_date: str  # e.g., '10 November 2026'
    slot_time: str  # e.g., '09.00'
    published_at: Optional[str] = None
    published_message_id: Optional[int] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def get_parsed_raw(self) -> dict:
        if not self.raw_data:
            return {}
        try:
            return json.loads(self.raw_data)
        except Exception:
            return {}


@dataclass
class ActivityLogRecord:
    id: Optional[int]
    poster_id: Optional[int]
    user_id: Optional[int]
    action: str
    details: Optional[str]
    timestamp: str


@dataclass
class SystemStats:
    total_links_received: int
    total_posters_accepted: int
    total_posters_keep: int
    total_posters_published: int
    total_posters_failed: int
    total_users: int
    total_activity_today: int


@dataclass
class AdminDeviceRecord:
    device_id: str
    admin_id: int
    admin_name: str
    admin_username: Optional[str]
    phone_number: str
    device_model: str
    session_token: str
    status: str  # 'Active', 'Logged Out', 'Revoked'
    login_at: str
    last_active: str


@dataclass
class PosterReportRecord:
    id: Optional[int]
    poster_id: int
    report_chat_id: str
    report_message_id: Optional[int]
    sender_id: int
    sender_name: str
    sender_username: Optional[str]
    institution_name: Optional[str]
    status: str  # 'Menunggu Diproses', 'Diterima', 'Ditolak', 'Selesai'
    processed_by_id: Optional[int] = None
    processed_by_name: Optional[str] = None
    processed_at: Optional[str] = None
    action_note: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class OperationalHoursConfig:
    open_hour: int = 6  # 06.00 WIB
    close_hour: int = 22  # 22.00 WIB
    sunday_closed: bool = True  # Minggu TUTUP

