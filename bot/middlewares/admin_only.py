from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware

from bot.access import can_receive_bot_responses


class AdminOnlyInteractionMiddleware(BaseMiddleware):
    """Silence interactive handlers for everyone except admins when enabled."""

    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        if can_receive_bot_responses(data.get("db_user")):
            return await handler(event, data)
        return None
