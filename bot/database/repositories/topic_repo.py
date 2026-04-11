from datetime import datetime, timezone
import re

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.department import Department
from models.flow import FlowCase, FlowSignal
from models.telegram_group import TelegramGroup
from models.topic import TelegramTopic, TopicAIProfile


class TopicRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _load_topic(self, *, group_id: int, topic_id: int) -> TelegramTopic | None:
        result = await self.session.execute(
            select(TelegramTopic)
            .options(selectinload(TelegramTopic.profile))
            .where(TelegramTopic.group_id == group_id)
            .where(TelegramTopic.telegram_topic_id == topic_id)
        )
        return result.scalar_one_or_none()

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
        topic = await self._load_topic(group_id=group.id, topic_id=topic_id)
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
            try:
                await self.session.flush()
            except IntegrityError:
                await self.session.rollback()
                group = await self.ensure_group(chat_id, chat_title)
                topic = await self._load_topic(group_id=group.id, topic_id=topic_id)
                if topic is None:
                    raise
                profile = topic.profile
            else:
                profile = TopicAIProfile(
                    topic_id=topic.id,
                    preferred_department_id=department.id if department else None,
                )
                self.session.add(profile)
                topic.profile = profile
                try:
                    await self.session.flush()
                except IntegrityError:
                    await self.session.rollback()
                    group = await self.ensure_group(chat_id, chat_title)
                    topic = await self._load_topic(group_id=group.id, topic_id=topic_id)
                    if topic is None:
                        raise
                    profile = topic.profile
        else:
            if resolved_title and (topic.title.startswith("Topic ") or topic.title != resolved_title):
                topic.title = resolved_title
            if icon_emoji and not topic.icon_emoji:
                topic.icon_emoji = icon_emoji
            topic.last_seen_at = seen_at or datetime.now(timezone.utc)
            topic.last_message_at = seen_at or datetime.now(timezone.utc)
            profile = topic.profile

        topic.message_count += 1
        if has_media:
            topic.media_count += 1

        if profile is None:
            profile = TopicAIProfile(
                topic_id=topic.id,
                preferred_department_id=department.id if department else None,
            )
            self.session.add(profile)
            topic.profile = profile
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

    async def search_relevant_topics(self, text: str, *, limit: int = 5) -> list[TelegramTopic]:
        topics = await self.list_topics()
        if not text:
            return []

        normalized_text = self._normalize_text(text)
        query_words = self._split_words(normalized_text)
        ranked: list[tuple[int, datetime | None, TelegramTopic]] = []

        for topic in topics:
            if not topic.is_active:
                continue

            title_normalized = self._normalize_text(topic.title)
            title_words = self._split_words(title_normalized)
            score = 0

            if title_normalized and title_normalized in normalized_text:
                score += 12
            overlap = len(query_words & title_words)
            score += overlap * 4
            score += self._fuzzy_word_score(query_words, title_words)

            profile_summary = self._normalize_text((topic.profile.profile_summary if topic.profile else "") or "")
            if profile_summary:
                summary_words = self._split_words(profile_summary)
                score += len(query_words & summary_words)
                score += self._fuzzy_word_score(query_words, summary_words, weight=1)

            top_tags = []
            if topic.profile and topic.profile.learning_snapshot:
                top_tags = list(dict(topic.profile.learning_snapshot).get("tag_counts", {}).keys())
            for tag in top_tags[:6]:
                if self._normalize_text(tag) in normalized_text:
                    score += 2

            if score > 0:
                ranked.append((score, topic.last_seen_at or topic.last_message_at, topic))

        ranked.sort(key=lambda item: (item[0], item[1] or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return [item[2] for item in ranked[:limit]]

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.lower().replace("ё", "е").split())

    @staticmethod
    def _split_words(text: str) -> set[str]:
        return {word for word in re.findall(r"[a-zA-Zа-яА-Я0-9]+", text) if len(word) >= 3}

    @staticmethod
    def _fuzzy_word_score(query_words: set[str], candidate_words: set[str], *, weight: int = 2) -> int:
        score = 0
        for query_word in query_words:
            for candidate_word in candidate_words:
                if len(query_word) < 5 or len(candidate_word) < 5:
                    continue
                if query_word in candidate_word or candidate_word in query_word:
                    score += weight
                    continue
                if query_word[:5] == candidate_word[:5]:
                    score += weight
        return score

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
