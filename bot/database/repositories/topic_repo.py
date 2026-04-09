from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.department import Department
from models.flow import FlowCase, FlowSignal
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

    async def list_groups_with_topics(self) -> list[TelegramGroup]:
        result = await self.session.execute(
            select(TelegramGroup)
            .options(selectinload(TelegramGroup.topics).selectinload(TelegramTopic.profile))
            .order_by(TelegramGroup.title)
        )
        return list(result.scalars().all())

    async def build_topic_metrics(self, group_id: int | None = None) -> dict[int, dict]:
        signal_query = (
            select(
                FlowSignal.topic_id.label("topic_id"),
                func.count(FlowSignal.id).label("signal_count"),
                func.count(case((FlowSignal.requires_attention == True, 1))).label("attention_count"),
                func.count(case((FlowSignal.has_media == True, 1))).label("media_signal_count"),
                func.max(FlowSignal.happened_at).label("last_signal_at"),
            )
            .where(FlowSignal.topic_id.is_not(None))
            .group_by(FlowSignal.topic_id)
        )
        case_query = (
            select(
                FlowCase.primary_topic_id.label("topic_id"),
                func.count(FlowCase.id).label("case_count"),
                func.count(case((FlowCase.is_critical == True, 1))).label("critical_case_count"),
                func.count(case((FlowCase.status.in_(["open", "watching"]), 1))).label("open_case_count"),
            )
            .where(FlowCase.primary_topic_id.is_not(None))
            .group_by(FlowCase.primary_topic_id)
        )

        if group_id is not None:
            signal_query = signal_query.where(FlowSignal.group_id == group_id)
            case_query = case_query.where(FlowCase.group_id == group_id)

        signal_rows = (await self.session.execute(signal_query)).all()
        case_rows = (await self.session.execute(case_query)).all()

        metrics: dict[int, dict] = {}
        for row in signal_rows:
            metrics[row.topic_id] = {
                "signal_count": row.signal_count or 0,
                "attention_count": row.attention_count or 0,
                "media_signal_count": row.media_signal_count or 0,
                "last_signal_at": row.last_signal_at,
                "case_count": 0,
                "critical_case_count": 0,
                "open_case_count": 0,
            }
        for row in case_rows:
            metrics.setdefault(
                row.topic_id,
                {
                    "signal_count": 0,
                    "attention_count": 0,
                    "media_signal_count": 0,
                    "last_signal_at": None,
                    "case_count": 0,
                    "critical_case_count": 0,
                    "open_case_count": 0,
                },
            )
            metrics[row.topic_id]["case_count"] = row.case_count or 0
            metrics[row.topic_id]["critical_case_count"] = row.critical_case_count or 0
            metrics[row.topic_id]["open_case_count"] = row.open_case_count or 0
        return metrics
