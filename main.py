"""
Main entry point for MEDIAPATNER BOT.
ASCHEN EVENT ORGANIZER - AUTOMATIC MEDIA PARTNER MANAGEMENT SYSTEM
"""

import sys
import asyncio
import logging
from dotenv import load_dotenv

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Set Windows Selector loop policy to prevent Proactor loop hangs on Windows
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# Load .env file securely
load_dotenv()

from mediapatner.config import get_settings
from mediapatner.bot import MediaPatnerApplication

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("mediapatner")


async def main():
    try:
        settings = get_settings()
    except Exception as e:
        logger.critical(
            "\n" + "=" * 70 + "\n"
            "[!] FATAL CONFIGURATION ERROR:\n"
            "BOT_TOKEN belum disetel atau masih berupa placeholder.\n\n"
            "Silakan ikuti langkah berikut:\n"
            "1. Buat token baru di Telegram via @BotFather (karena token lama sudah terekspos).\n"
            "2. Buka file .env dan ubah BOT_TOKEN menjadi token baru Anda.\n"
            "   Contoh: BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRstuVWXyz\n"
            "3. Jalankan kembali: python main.py\n"
            + "=" * 70
        )
        return

    app = MediaPatnerApplication(settings)

    try:
        await app.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution stopped by user or system.")
    except Exception as e:
        logger.critical(f"Unexpected error in bot execution: {e}", exc_info=True)
    finally:
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
