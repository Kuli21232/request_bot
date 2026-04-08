from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.database import AsyncSessionLocal
from bot.database.repositories.department_repo import DepartmentRepository


class TopicResolverMiddleware(BaseMiddleware):
    """Разрешает message_thread_id → department из БД."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        department = None

        if getattr(event, "message_thread_id", None):
            async with AsyncSessionLocal() as session:
                repo = DepartmentRepository(session)
                department = await repo.get_by_topic(
                    chat_id=event.chat.id,
                    topic_id=event.message_thread_id,
                )

        data["department"] = department
        return await handler(event, data)
