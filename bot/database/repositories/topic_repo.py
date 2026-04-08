from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.department import Department
from models.telegram_group import TelegramGroup
from models.topic import TelegramTopic, TopicAIProfile


class TopicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_group(self, chat_id: int, title: str) -> TelegramGroup:
        result = await self.session.execute(
            select(TelegramGroup).where(TelegramGroup.telegram_chat_id == chat_id)
        )
        group = result.scalar_one_or_none()
        if group is None:
            group = TelegramGroup(telegram_chat_id=chat_id, title=title)
            self.session.add(group)
            await self.session.flush()
        elif title and group.title != title:
            group.title = title
        return group

    async def get_department_by_topic(self, chat_id: int, topic_id: int) -> Department | None:
        result = await self.session.execute(
            select(Department)
            .join(TelegramGroup, TelegramGroup.id == Department.group_id)
            .where(TelegramGroup.telegram_chat_id == chat_id)
            .where(Department.telegram_topic_id == topic_id)
            .where(Department.is_active == True)
        )
        return result.scalar_one_or_none()

    async def ensure_topic(
        self,
        *,
        chat_id: int,
        chat_title: str,
        topic_id: int,
        topic_title: str,
        icon_emoji: str | None = None,
        department: Department | None = None,
        seen_at: datetime | None = None,
        has_media: bool = False,
    ) -> tuple[TelegramTopic, TopicAIProfile]:
        group = await self.ensure_group(chat_id, chat_title)
        result = await self.session.execute(
            select(TelegramTopic)
            .options(selectinload(TelegramTopic.profile))
            .where(TelegramTopic.group_id == group.id)
            .where(TelegramTopic.telegram_topic_id == topic_id)
        )
        topic = result.scalar_one_or_none()
        resolved_title = topic_title or (department.name if department else f"Topic {topic_id}")
        if topic is None:
            topic = TelegramTopic(
                group_id=group.id,
                telegram_topic_id=topic_id,
                title=resolved_title,
                icon_emoji=icon_emoji or (department.icon_emoji if department else None),
                last_seen_at=seen_at,
                last_message_at=seen_at,
            )
            self.session.add(topic)
            await self.session.flush()
        else:
            if resolved_title and (topic.title.startswith("Topic ") or topic.title != resolved_title):
                topic.title = resolved_title
            if icon_emoji and not topic.icon_emoji:
                topic.icon_emoji = icon_emoji
            topic.last_seen_at = seen_at or datetime.now(timezone.utc)
            topic.last_message_at = seen_at or datetime.now(timezone.utc)

        topic.message_count += 1
        if has_media:
            topic.media_count += 1

        profile = topic.profile
        if profile is None:
            profile = TopicAIProfile(
                topic_id=topic.id,
                preferred_department_id=department.id if department else None,
            )
            self.session.add(profile)
            await self.session.flush()
        elif department and profile.preferred_department_id is None:
            profile.preferred_department_id = department.id

        return topic, profile

    async def mark_signal_recorded(self, topic: TelegramTopic) -> None:
        topic.signal_count += 1
        await self.session.flush()

    async def list_topics(self, group_id: int | None = None) -> list[TelegramTopic]:
        query = (
            select(TelegramTopic)
            .options(selectinload(TelegramTopic.profile), selectinload(TelegramTopic.group))
            .order_by(TelegramTopic.last_seen_at.desc().nullslast())
        )
        if group_id is not None:
            query = query.where(TelegramTopic.group_id == group_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_topic(self, topic_id: int) -> TelegramTopic | None:
        result = await self.session.execute(
            select(TelegramTopic)
            .options(selectinload(TelegramTopic.profile), selectinload(TelegramTopic.group))
            .where(TelegramTopic.id == topic_id)
        )
        return result.scalar_one_or_none()
