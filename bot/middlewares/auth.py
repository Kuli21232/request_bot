from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from bot.database import AsyncSessionLocal
from bot.database.repositories.user_repo import UserRepository


class AuthMiddleware(BaseMiddleware):
    """Авторегистрация пользователя при первом сообщении."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is None or event.from_user.is_bot:
            data["db_user"] = None
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.upsert_telegram_user(
                telegram_user_id=event.from_user.id,
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name,
                username=event.from_user.username,
                language_code=event.from_user.language_code or "ru",
            )
            data["db_user"] = user

        return await handler(event, data)
