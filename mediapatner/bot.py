"""
Bot initialization, dependency wiring, dispatcher configuration,
and lifecycle management for MEDIAPATNER BOT.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from mediapatner.config import Settings, get_settings
from mediapatner.database.db import Database
from mediapatner.database.repository import Repository
from mediapatner.services.poster_processor import PosterProcessor
from mediapatner.services.notification_service import NotificationService
from mediapatner.services.publisher_service import PublisherService
from mediapatner.services.scheduler_service import SchedulerService
from mediapatner.services.report_service import ReportService
from mediapatner.middlewares.rate_limit import RateLimitMiddleware
from mediapatner.middlewares.logging_mw import SafeLoggingMiddleware
from mediapatner.handlers.user import router as user_router
from mediapatner.handlers.admin import router as admin_router

logger = logging.getLogger(__name__)


class MediaPatnerApplication:
    def __init__(self, settings: Settings):
        self.settings = settings

        # Telegram Bot API instance
        self.bot = Bot(
            token=self.settings.get_token_plain(),
            default=DefaultBotProperties(parse_mode=None),
        )

        # Dispatcher
        self.dp = Dispatcher()

        # Database and Repositories
        self.db = Database(db_path=self.settings.database_path)
        self.repository = Repository(self.db)

        # Services
        self.processor = PosterProcessor(self.repository)
        self.notification_service = NotificationService(self.bot, self.settings)
        self.publisher_service = PublisherService(
            bot=self.bot,
            settings=self.settings,
            repository=self.repository,
            notification_service=self.notification_service,
        )
        self.report_service = ReportService(
            bot=self.bot,
            repository=self.repository,
            settings=self.settings,
            publisher_service=self.publisher_service,
        )
        self.scheduler_service = SchedulerService(
            repository=self.repository,
            publish_handler=self.publisher_service.publish_poster,
            interval_seconds=30,
            post_delay_seconds=self.settings.post_interval_seconds,
        )

        self._setup_wiring()

    def _setup_wiring(self):
        """Registers middlewares, dependency injections, and routers."""
        # Inject dependencies into dispatcher workflow context
        self.dp["settings"] = self.settings
        self.dp["repository"] = self.repository
        self.dp["processor"] = self.processor
        self.dp["notification_service"] = self.notification_service
        self.dp["report_service"] = self.report_service
        self.dp["publisher_service"] = self.publisher_service
        self.dp["scheduler_service"] = self.scheduler_service

        # Middlewares
        self.dp.message.middleware(SafeLoggingMiddleware())
        self.dp.callback_query.middleware(SafeLoggingMiddleware())
        rate_limiter = RateLimitMiddleware()
        self.dp.message.middleware(rate_limiter)
        self.dp.callback_query.middleware(rate_limiter)

        # Routers: Admin router has precedence for /admin and administrative callbacks
        self.dp.include_router(admin_router)
        self.dp.include_router(user_router)

    async def start(self):
        """Initializes components and runs long polling."""
        logger.info("Starting MEDIAPATNER BOT for ASCHEN EVENT ORGANIZER...")

        # 1. Initialize database
        await self.db.init()

        # 2. Start scheduler service and queue recovery
        await self.scheduler_service.start()

        # 3. Delete webhook if set and start polling
        await self.bot.delete_webhook(drop_pending_updates=False)

        bot_info = await self.bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username} (ID: {bot_info.id})")
        logger.info(
            f"Configured Main Channel: {self.settings.channel_username} | "
            f"Notification Channel: {self.settings.notification_channel_id} (PERMANENT)"
        )

        try:
            await self.dp.start_polling(self.bot)
        finally:
            await self.stop()

    async def stop(self):
        """Graceful shutdown of scheduler and bot session."""
        logger.info("Stopping MEDIAPATNER BOT...")
        await self.scheduler_service.stop()
        await self.bot.session.close()
        logger.info("Shutdown completed.")
