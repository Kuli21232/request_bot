from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.database import AsyncSessionLocal
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.topic_ai_engine import TopicAIEngine


class TopicResolverMiddleware(BaseMiddleware):
    """Auto-sync topic context and resolve legacy department binding."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        department = None
        topic = None
        topic_profile = None

        if getattr(event, "message_thread_id", None):
            async with AsyncSessionLocal() as session:
                repo = TopicRepository(session)
                department = await repo.get_department_by_topic(
                    chat_id=event.chat.id,
                    topic_id=event.message_thread_id,
                )
                topic, topic_profile = await repo.ensure_topic(
                    chat_id=event.chat.id,
                    chat_title=event.chat.title or "Telegram group",
                    topic_id=event.message_thread_id,
                    topic_title=department.name if department else f"Topic {event.message_thread_id}",
                    department=department,
                    seen_at=event.date,
                    has_media=bool(event.photo or event.document or event.voice or event.audio or getattr(event, "video", None)),
                )
                TopicAIEngine().bootstrap_profile(topic, topic_profile)
                await session.commit()

        data["department"] = department
        data["topic"] = topic
        data["topic_profile"] = topic_profile
        return await handler(event, data)
