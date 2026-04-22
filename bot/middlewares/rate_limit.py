import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.access import can_receive_bot_responses


class RateLimitMiddleware(BaseMiddleware):
    """Simple in-memory rate limiter. Replace with Redis in production."""

    def __init__(self, rate: int = 10, period: int = 60):
        self.rate = rate
        self.period = period
        self._buckets: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        # Never throttle forum traffic: these messages must still be ingested.
        if getattr(event.chat, "type", None) == "supergroup":
            return await handler(event, data)

        if event.from_user is None:
            return await handler(event, data)

        uid = event.from_user.id
        now = time.time()
        window_start = now - self.period

        self._buckets[uid] = [t for t in self._buckets[uid] if t > window_start]

        if len(self._buckets[uid]) >= self.rate:
            if can_receive_bot_responses(data.get("db_user")):
                await event.reply("Слишком много сообщений. Подождите немного.")
            return None

        self._buckets[uid].append(now)
        return await handler(event, data)
