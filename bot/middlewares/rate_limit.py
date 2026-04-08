import time
from collections import defaultdict
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message


class RateLimitMiddleware(BaseMiddleware):
    """Простой in-memory rate limiter. В продакшене заменить на Redis."""

    def __init__(self, rate: int = 10, period: int = 60):
        self.rate = rate        # макс. сообщений
        self.period = period    # за period секунд
        self._buckets: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is None:
            return await handler(event, data)

        uid = event.from_user.id
        now = time.time()
        window_start = now - self.period

        self._buckets[uid] = [t for t in self._buckets[uid] if t > window_start]

        if len(self._buckets[uid]) >= self.rate:
            await event.reply("Слишком много сообщений. Подождите немного.")
            return

        self._buckets[uid].append(now)
        return await handler(event, data)
