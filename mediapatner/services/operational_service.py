"""
Operational Hours Service for MEDIAPATNER BOT.
Enforces Asia/Jakarta (WIB) submission operating schedule:
- Senin–Sabtu starting at 06.00 WIB until configured closing hour (default 22.00 WIB).
- Minggu: TUTUP SEHARIAN.
"""

from typing import Tuple, Optional
from datetime import datetime
import pytz
from mediapatner.database.models import OperationalHoursConfig

WIB_TZ = pytz.timezone("Asia/Jakarta")

MSG_SUNDAY_CLOSED = (
    "𓄲 REQUEST POSTER CLOSED 𓈒\n\n"
    "Halo! Mohon maaf, layanan Request Poster sedang libur pada hari Minggu.\n\n"
    "Pengajuan akan kembali dibuka pada hari Senin pukul 06.00 WIB.\n\n"
    "Silakan ajukan kembali poster Anda pada jadwal yang telah ditentukan.\n\n"
    "Sampai jumpa di hari Senin!\n\n"
    "𓄲 ASCHEN EVENT ORGANIZER\n"
    "Elegant Collaboration, Memorable Celebration."
)

MSG_BEFORE_HOURS = (
    "𓄲 REQUEST POSTER BELUM DIBUKA 𓈒\n\n"
    "Halo! Pengajuan Media Partner saat ini belum dapat diproses karena berada di luar jam operasional.\n\n"
    "Jadwal pengajuan dimulai setiap hari Senin–Sabtu pukul 06.00 WIB.\n\n"
    "Silakan kembali pada jam operasional untuk mengirimkan poster kerja sama Anda.\n\n"
    "Terima kasih atas pengertian dan kerja sama Anda.\n\n"
    "𓄲 ASCHEN EVENT ORGANIZER\n"
    "Elegant Collaboration, Memorable Celebration."
)


def get_current_wib() -> datetime:
    return datetime.now(WIB_TZ)


def check_submission_allowed(
    config: OperationalHoursConfig, now_dt: Optional[datetime] = None
) -> Tuple[bool, str, str]:
    """
    Checks if poster submission is allowed right now in WIB.
    Returns:
        (is_allowed: bool, reason: str, message: str)
    """
    if now_dt is None:
        now_dt = get_current_wib()
    elif now_dt.tzinfo is None:
        now_dt = WIB_TZ.localize(now_dt)
    else:
        now_dt = now_dt.astimezone(WIB_TZ)

    # Sunday check (weekday() == 6)
    if now_dt.weekday() == 6 and config.sunday_closed:
        return False, "SUNDAY_CLOSED", MSG_SUNDAY_CLOSED

    # Before opening hour (e.g. before 06:00 WIB)
    if now_dt.hour < config.open_hour:
        return False, "BEFORE_HOURS", MSG_BEFORE_HOURS

    # After closing hour (e.g. >= 22:00 WIB)
    if now_dt.hour >= config.close_hour:
        msg_after_hours = (
            "𓄲 REQUEST POSTER TELAH DITUTUP 𓈒\n\n"
            f"Halo! Jam operasional pengajuan poster Media Partner untuk hari ini telah ditutup "
            f"(pukul {config.close_hour:02d}.00 WIB).\n\n"
            f"Jadwal pengajuan akan kembali dibuka besok pukul {config.open_hour:02d}.00 WIB.\n\n"
            "Silakan kembali pada jam operasional untuk mengirimkan poster kerja sama Anda.\n\n"
            "Terima kasih atas pengertian dan kerja sama Anda.\n\n"
            "𓄲 ASCHEN EVENT ORGANIZER\n"
            "Elegant Collaboration, Memorable Celebration."
        )
        return False, "AFTER_HOURS", msg_after_hours

    return True, "OPEN", ""
