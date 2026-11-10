"""
Scheduler service for MEDIAPATNER BOT.
Handles WIB slot calculations, Indonesian date/time formatting,
persistent queue checks, automated publishing, and queue recovery on startup.
"""

from datetime import datetime, timedelta
import pytz
from typing import Tuple, Optional, Callable, Awaitable, List
import asyncio
import logging
from mediapatner.database.repository import Repository
from mediapatner.database.models import PosterRecord

logger = logging.getLogger(__name__)

WIB_TZ = pytz.timezone("Asia/Jakarta")

INDONESIAN_DAYS = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu",
}

INDONESIAN_MONTHS = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}

# Official Publication Schedule (WIB):
# - Selasa: 09.00 WIB
# - Rabu: 12.00 WIB
# - Kamis: 09.00 WIB
# - Jumat: 12.00 WIB
# - Sabtu: 20.00 WIB
# (weekday: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday)
OFFICIAL_SLOTS = [
    (1, 9, 0),   # Selasa 09:00
    (2, 12, 0),  # Rabu 12:00
    (3, 9, 0),   # Kamis 09:00
    (4, 12, 0),  # Jumat 12:00
    (5, 20, 0),  # Sabtu 20:00
]


def get_current_wib() -> datetime:
    """Returns current datetime in Asia/Jakarta timezone."""
    return datetime.now(WIB_TZ)


def format_indonesian_date(dt: datetime) -> str:
    """Formats datetime to Indonesian date string: '10 November 2026'."""
    day = dt.day
    month = INDONESIAN_MONTHS.get(dt.month, str(dt.month))
    year = dt.year
    return f"{day} {month} {year}"


def format_indonesian_day(dt: datetime) -> str:
    """Returns day name in Indonesian: 'Selasa'."""
    return INDONESIAN_DAYS.get(dt.weekday(), "Hari")


def format_indonesian_time(dt: datetime) -> str:
    """Formats time as '09.00'."""
    return dt.strftime("%H.%M")


def calculate_next_wib_slot(now_dt: Optional[datetime] = None) -> Tuple[datetime, str, str, str]:
    """
    Calculates the nearest official publication slot according to ASCHEN schedule:
    - Selasa: 09.00 WIB
    - Rabu: 12.00 WIB
    - Kamis: 09.00 WIB
    - Jumat: 12.00 WIB
    - Sabtu: 20.00 WIB

    Returns:
        (slot_datetime_wib, slot_day_str, slot_date_str, slot_time_str)
    """
    if now_dt is None:
        now_dt = get_current_wib()
    elif now_dt.tzinfo is None:
        now_dt = WIB_TZ.localize(now_dt)
    else:
        now_dt = now_dt.astimezone(WIB_TZ)

    # Calculate Monday of current week at 00:00:00
    monday = (now_dt - timedelta(days=now_dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    candidate_slots: List[datetime] = []

    # Check slots for current week and next week
    for week_offset in (0, 7):
        for weekday, hour, minute in OFFICIAL_SLOTS:
            slot_candidate = monday + timedelta(days=weekday + week_offset, hours=hour, minutes=minute)
            # If candidate is in future or exact current minute
            if slot_candidate >= now_dt.replace(second=0, microsecond=0):
                candidate_slots.append(slot_candidate)

    if not candidate_slots:
        # Fallback to next Tuesday if something unexpected occurs
        fallback = monday + timedelta(days=7 + 1, hours=9, minutes=0)
        candidate_slots.append(fallback)

    candidate_slots.sort()
    chosen_slot = candidate_slots[0]

    day_str = format_indonesian_day(chosen_slot)
    date_str = format_indonesian_date(chosen_slot)
    time_str = format_indonesian_time(chosen_slot)

    return chosen_slot, day_str, date_str, time_str


class SchedulerService:
    def __init__(
        self,
        repository: Repository,
        publish_handler: Callable[[PosterRecord], Awaitable[bool]],
        interval_seconds: int = 30,
        post_delay_seconds: int = 8,
    ):
        self.repository = repository
        self.publish_handler = publish_handler
        self.interval_seconds = interval_seconds
        self.post_delay_seconds = post_delay_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the scheduler background task and performs queue recovery."""
        if self._running:
            return

        self._running = True
        logger.info("Starting SchedulerService (WIB Asia/Jakarta)...")

        # Perform queue recovery on startup
        await self.recover_queue()

        # Start continuous loop
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stops the scheduler loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("SchedulerService stopped.")

    async def recover_queue(self):
        """
        Recovers pending KEEP and SCHEDULED posters from database upon startup/restart.
        Ensures no poster is lost or forgotten.
        """
        try:
            pending = await self.repository.get_all_pending_posters()
            logger.info(f"Queue Recovery: Found {len(pending)} pending posters in KEEP/SCHEDULED status.")
            now_wib = get_current_wib()
            for poster in pending:
                logger.info(
                    f"Recovered Poster #{poster.id} | Submitter: {poster.sender_name} | "
                    f"Slot: {poster.slot_day}, {poster.slot_date} {poster.slot_time} WIB"
                )
        except Exception as e:
            logger.error(f"Error during queue recovery: {e}", exc_info=True)

    async def _scheduler_loop(self):
        """Background loop executing due poster publications."""
        while self._running:
            try:
                await self.check_and_publish_due_posters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Exception in scheduler loop: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def check_and_publish_due_posters(self):
        """Checks if any posters are due for publication at the current WIB time."""
        now_wib = get_current_wib()
        # ISO string format for comparison: YYYY-MM-DDTHH:MM:SS
        cutoff_iso = now_wib.strftime("%Y-%m-%dT%H:%M:%S")

        due_posters = await self.repository.get_posters_due(cutoff_iso)
        if not due_posters:
            return

        logger.info(f"Scheduler: Found {len(due_posters)} poster(s) due for publication.")

        for poster in due_posters:
            if not self._running:
                break

            # Atomically mark as PUBLISHING to prevent race conditions
            marked = await self.repository.mark_publishing(poster.id)
            if not marked:
                continue

            try:
                logger.info(f"Publishing poster #{poster.id} to main channel...")
                success = await self.publish_handler(poster)
                if success:
                    logger.info(f"Poster #{poster.id} published successfully.")
                else:
                    logger.warning(f"Poster #{poster.id} publish handler returned false.")
            except Exception as e:
                logger.error(f"Error publishing poster #{poster.id}: {e}", exc_info=True)
                await self.repository.mark_failed(poster.id, str(e))

            # Delay between multiple publications to prevent Telegram rate-limiting
            if len(due_posters) > 1:
                await asyncio.sleep(self.post_delay_seconds)
