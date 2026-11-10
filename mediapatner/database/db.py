"""
Database connection manager and schema initialization using aiosqlite.
Ensures persistent storage, WAL mode, foreign keys, and safe recovery.
"""

import os
import aiosqlite
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

INIT_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    total_submissions INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS posters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    sender_name TEXT NOT NULL,
    sender_username TEXT,
    source_link TEXT,
    source_chat_id TEXT,
    source_message_id INTEGER,
    media_type TEXT,
    file_id TEXT,
    caption TEXT,
    raw_data TEXT,
    status TEXT NOT NULL DEFAULT 'KEEP',
    scheduled_slot TEXT NOT NULL,
    slot_day TEXT NOT NULL,
    slot_date TEXT NOT NULL,
    slot_time TEXT NOT NULL,
    published_at TEXT,
    published_message_id INTEGER,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(sender_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_posters_status ON posters(status);
CREATE INDEX IF NOT EXISTS idx_posters_scheduled_slot ON posters(scheduled_slot);
CREATE INDEX IF NOT EXISTS idx_posters_source_link ON posters(source_link);
CREATE INDEX IF NOT EXISTS idx_posters_source_msg ON posters(source_chat_id, source_message_id);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poster_id INTEGER,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_date ON activity_logs(timestamp);

CREATE TABLE IF NOT EXISTS admin_devices (
    device_id TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    admin_name TEXT NOT NULL,
    admin_username TEXT,
    phone_number TEXT NOT NULL,
    device_model TEXT DEFAULT 'Telegram Client',
    session_token TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active',
    login_at TEXT NOT NULL,
    last_active TEXT NOT NULL,
    FOREIGN KEY(admin_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_admin_devices_status ON admin_devices(status);

CREATE TABLE IF NOT EXISTS poster_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poster_id INTEGER NOT NULL,
    report_chat_id TEXT NOT NULL,
    report_message_id INTEGER,
    sender_id INTEGER NOT NULL,
    sender_name TEXT NOT NULL,
    sender_username TEXT,
    institution_name TEXT,
    status TEXT NOT NULL DEFAULT 'Menunggu Diproses',
    processed_by_id INTEGER,
    processed_by_name TEXT,
    processed_at TEXT,
    action_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY(poster_id) REFERENCES posters(id)
);

CREATE INDEX IF NOT EXISTS idx_poster_reports_status ON poster_reports(status);
CREATE INDEX IF NOT EXISTS idx_poster_reports_poster_id ON poster_reports(poster_id);
"""


class Database:
    def __init__(self, db_path: str = "data/mediapatner.db"):
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self):
        dir_name = os.path.dirname(self.db_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

    async def init(self):
        """Initializes tables, indexes, and default settings."""
        if os.getenv("VERCEL") or os.getenv("NOW_REGION"):
            try:
                from mediapatner.database.blob_sync import restore_from_blob
                if not os.path.exists(self.db_path):
                    restore_from_blob(self.db_path)
            except Exception as e:
                logger.warning(f"Blob restore error: {e}")

        logger.info(f"Initializing database at {self.db_path}")
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(INIT_SQL)
            defaults = [
                ("auto_forward_enabled", "true"),
                ("report_chat_id", "-1004479248551"),
                ("report_chat_type", "PERMANENT_CHANNEL"),
                ("operational_open_hour", "6"),
                ("operational_close_hour", "22"),
                ("operational_sunday_closed", "true"),
            ]
            for key, val in defaults:
                await db.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val)
                )
            await db.commit()
        logger.info("Database initialized successfully.")

    @asynccontextmanager
    async def connection(self):
        """Async context manager yielding a configured connection and closing it cleanly."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
