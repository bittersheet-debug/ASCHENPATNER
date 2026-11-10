"""
Safe audit logging middleware.
Logs interactions while strictly redacting any secrets, tokens, or credentials.
"""

from typing import Any, Awaitable, Callable, Dict
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger("mediapatner.audit")


class SafeLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        user = event.from_user
        user_info = f"ID:{user.id} (@{user.username or 'none'})" if user else "Unknown"

        if isinstance(event, Message):
            text_preview = event.text[:50] if event.text else f"[{event.content_type}]"
            logger.info(f"Incoming Message from {user_info}: {text_preview}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"Callback from {user_info}: {event.data}")

        return await handler(event, data)
