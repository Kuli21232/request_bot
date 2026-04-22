from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.topic_ai_engine import TopicAIEngine

logger = logging.getLogger(__name__)


class TopicAutomationService:
    def __init__(self) -> None:
        self.engine = TopicAIEngine()

    async def refresh_active_topics(self, session: AsyncSession, *, limit: int = 20) -> list[dict]:
        topic_repo = TopicRepository(session)
        topics = await topic_repo.list_topics()
        results: list[dict] = []

        for topic in topics:
            if not topic.is_active or topic.profile is None:
                continue
            result = await self.refresh_topic(session, topic.id)
            if result:
                results.append(result)
            if len(results) >= limit:
                break
        return results

    async def refresh_topic(self, session: AsyncSession, topic_id: int) -> dict | None:
        topic_repo = TopicRepository(session)
        flow_repo = FlowRepository(session)
        topic = await topic_repo.get_topic(topic_id)
        if topic is None or topic.profile is None:
            return None

        signals = await flow_repo.list_topic_signal_briefs(topic_id=topic_id, limit=8)
        cases = await flow_repo.list_topic_cases(topic_id=topic_id, limit=5)
        snapshot = self._build_snapshot(topic, signals, cases)

        behavior_rules = dict(topic.profile.behavior_rules or {})
        behavior_rules["automation"] = snapshot
        topic.profile.behavior_rules = behavior_rules

        learning_snapshot = dict(topic.profile.learning_snapshot or {})
        learning_snapshot["automation"] = {
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "priority": snapshot["priority"],
            "recommended_action": snapshot["recommended_action"],
            "attention_count": snapshot["attention_count"],
            "open_case_count": snapshot["open_case_count"],
            "follow_up_needed": snapshot["follow_up_needed"],
        }
        topic.profile.learning_snapshot = learning_snapshot
        topic.profile.last_rule_update_at = datetime.now(timezone.utc)
        await session.flush()
        return {
            "topic_id": topic.id,
            "title": topic.title,
            "priority": snapshot["priority"],
            "recommended_action": snapshot["recommended_action"],
        }

    async def build_topic_sections(
        self,
        session: AsyncSession,
        *,
        kind: str | None = None,
        requires_attention: bool | None = None,
        limit_topics: int = 12,
        signals_per_topic: int = 4,
        cases_per_topic: int = 3,
    ) -> list[dict]:
        flow_repo = FlowRepository(session)
        ranked_topics = await self._rank_topics(session)

        sections: list[dict] = []
        for item in ranked_topics:
            topic = item["topic"]
            profile = item["profile"]
            signals = await flow_repo.list_topic_signal_briefs(
                topic_id=topic.id,
                limit=signals_per_topic,
                kind=kind,
                requires_attention=requires_attention,
            )
            cases = await flow_repo.list_topic_cases(topic_id=topic.id, limit=cases_per_topic)
            if not signals and not cases:
                continue

            automation = dict(profile.behavior_rules or {}).get("automation", {})
            if not automation:
                automation = self._build_snapshot(topic, signals, cases)
            sections.append(
                {
                    "topic_id": topic.id,
                    "topic_title": topic.title,
                    "group_id": topic.group_id,
                    "group_title": item.get("group_title"),
                    "icon_emoji": topic.icon_emoji,
                    "topic_kind": topic.topic_kind,
                    "priority": item["priority"],
                    "score": item["score"],
                    "reasons": item["reasons"],
                    "stats": {
                        **item["metrics"],
                        "message_count": topic.message_count,
                        "media_count": topic.media_count,
                    },
                    "profile_summary": profile.profile_summary,
                    "automation": automation,
                    "signals": signals,
                    "cases": cases,
                }
            )
            if len(sections) >= limit_topics:
                break
        return sections

    async def build_action_board(self, session: AsyncSession, *, limit: int = 8) -> list[dict]:
        sections = await self.build_topic_sections(
            session,
            limit_topics=max(limit * 3, 18),
            signals_per_topic=3,
            cases_per_topic=3,
        )
        items: list[dict] = []
        for section in sections:
            automation = section.get("automation") or {}
            score = self._action_score(section)
            if score <= 0:
                continue

            items.append(
                {
                    "topic_id": section["topic_id"],
                    "topic_title": section["topic_title"],
                    "group_id": section["group_id"],
                    "group_title": section["group_title"],
                    "priority": section["priority"],
                    "recommended_action": automation.get("recommended_action") or "watch_topic",
                    "summary": automation.get("summary") or section.get("profile_summary"),
                    "attention_count": automation.get("attention_count", 0),
                    "open_case_count": automation.get("open_case_count", 0),
                    "critical_case_count": automation.get("critical_case_count", 0),
                    "follow_up_needed": automation.get("follow_up_needed", False),
                    "last_signal_at": automation.get("last_signal_at"),
                    "score": score,
                }
            )

        items.sort(
            key=lambda item: (
                item["score"],
                item["critical_case_count"],
                item["attention_count"],
                item["open_case_count"],
            ),
            reverse=True,
        )
        return items[:limit]

    async def build_group_digests(self, session: AsyncSession, *, limit_groups: int = 8) -> list[dict]:
        sections = await self.build_topic_sections(
            session,
            limit_topics=24,
            signals_per_topic=3,
            cases_per_topic=2,
        )
        grouped: dict[tuple[int | None, str], list[dict]] = {}
        for section in sections:
            key = (section["group_id"], section["group_title"] or "Группа")
            grouped.setdefault(key, []).append(section)

        digests: list[dict] = []
        for (group_id, group_title), items in grouped.items():
            attention_count = sum(item["stats"].get("attention_count", 0) for item in items)
            critical_case_count = sum(item["stats"].get("critical_case_count", 0) for item in items)
            open_case_count = sum(item["stats"].get("open_case_count", 0) for item in items)
            signal_count = sum(item["stats"].get("signal_count", 0) for item in items)
            follow_up_topics = sum(1 for item in items if (item.get("automation") or {}).get("follow_up_needed"))
            recommended_focus = self._build_group_focus(
                critical_case_count=critical_case_count,
                attention_count=attention_count,
                follow_up_topics=follow_up_topics,
                open_case_count=open_case_count,
            )
            top_topics = items[:4]
            digests.append(
                {
                    "group_id": group_id,
                    "group_title": group_title,
                    "signal_count": signal_count,
                    "attention_count": attention_count,
                    "critical_case_count": critical_case_count,
                    "open_case_count": open_case_count,
                    "follow_up_topics": follow_up_topics,
                    "recommended_focus": recommended_focus,
                    "top_topics": [
                        {
                            "topic_id": item["topic_id"],
                            "topic_title": item["topic_title"],
                            "priority": item["priority"],
                            "recommended_action": (item.get("automation") or {}).get("recommended_action"),
                            "summary": (item.get("automation") or {}).get("summary") or item.get("profile_summary"),
                        }
                        for item in top_topics
                    ],
                }
            )

        digests.sort(
            key=lambda item: (
                item["critical_case_count"],
                item["attention_count"],
                item["signal_count"],
            ),
            reverse=True,
        )
        return digests[:limit_groups]

    async def _rank_topics(self, session: AsyncSession) -> list[dict]:
        topic_repo = TopicRepository(session)
        groups = await topic_repo.list_groups_with_topics()
        metrics = await topic_repo.build_topic_metrics()
        ranked_topics: list[dict] = []
        for group in groups:
            active_topics = [topic for topic in group.topics if topic.is_active]
            ranked_topics.extend(
                {
                    **item,
                    "group_title": group.title,
                }
                for item in self.engine.sort_topics(active_topics, metrics)
            )

        ranked_topics.sort(
            key=lambda item: (
                item["score"],
                item["metrics"]["attention_count"],
                item["metrics"]["open_case_count"],
                item["metrics"]["signal_count"],
                -item["topic"].id,
            ),
            reverse=True,
        )
        return ranked_topics

    def _build_snapshot(self, topic, signals, cases) -> dict:
        kind_counts = Counter(signal.kind for signal in signals if signal.kind)
        attention_count = sum(1 for signal in signals if signal.requires_attention)
        open_case_count = sum(1 for case in cases if case.status in {"open", "watching"})
        critical_case_count = sum(1 for case in cases if case.is_critical or case.priority == "critical")
        top_stores = [store for store, _ in Counter(signal.store for signal in signals if signal.store).most_common(4)]
        signal_examples = [
            (signal.summary or " ".join(signal.body.split())[:110] or topic.title)
            for signal in signals[:4]
        ]
        dominant_kind = kind_counts.most_common(1)[0][0] if kind_counts else None
        follow_up_needed = self._needs_follow_up(signals, cases)

        if critical_case_count or any(signal.importance == "critical" for signal in signals):
            priority = "critical"
            recommended_action = "suggest_escalation"
        elif attention_count or open_case_count >= 2:
            priority = "high"
            recommended_action = "review_topic_queue"
        elif follow_up_needed:
            priority = "high"
            recommended_action = "follow_up"
        elif kind_counts.get("photo_report", 0) >= max(2, len(signals) // 2) and attention_count == 0:
            priority = "normal"
            recommended_action = "digest_only"
        elif signals:
            priority = "normal"
            recommended_action = "watch_topic"
        else:
            priority = "low"
            recommended_action = "collect_context"

        summary = self._build_summary(
            topic_title=topic.title,
            dominant_kind=dominant_kind,
            attention_count=attention_count,
            critical_case_count=critical_case_count,
            top_stores=top_stores,
            signal_examples=signal_examples,
            follow_up_needed=follow_up_needed,
        )

        return {
            "priority": priority,
            "recommended_action": recommended_action,
            "summary": summary,
            "attention_count": attention_count,
            "open_case_count": open_case_count,
            "critical_case_count": critical_case_count,
            "dominant_kind": dominant_kind,
            "top_stores": top_stores,
            "signal_examples": signal_examples,
            "case_titles": [case.title for case in cases[:3]],
            "last_signal_at": signals[0].happened_at.isoformat() if signals else None,
            "follow_up_needed": follow_up_needed,
        }

    _DOMINANT_KIND_LABELS: dict[str, str] = {
        "problem": "технические проблемы",
        "compliance": "вопросы ЕГАИС и маркировки",
        "finance": "финансовые вопросы",
        "delivery": "поставки и доставки",
        "photo_report": "фотоотчёты",
        "inventory": "остатки и товар",
        "escalation": "эскалации",
        "request": "операционные запросы",
        "status_update": "статусные обновления",
        "news": "новости",
        "chat/noise": "рабочие переписки",
    }

    def _build_summary(
        self,
        *,
        topic_title: str,
        dominant_kind: str | None,
        attention_count: int,
        critical_case_count: int,
        top_stores: list[str],
        signal_examples: list[str],
        follow_up_needed: bool,
    ) -> str:
        if not signal_examples:
            return f"Топик «{topic_title}» пока накапливает контекст — новых сигналов нет."

        # Critical path: short punchy text for urgent topics
        if critical_case_count and attention_count:
            stores_hint = f" ({', '.join(top_stores[:2])})" if top_stores else ""
            return (
                f"«{topic_title}»{stores_hint}: {critical_case_count} крит. кейса, "
                f"{attention_count} сигналов требуют разбора. {signal_examples[0]}"
            )
        if critical_case_count:
            return f"«{topic_title}»: {critical_case_count} критичных ситуаций — требуется немедленный разбор."
        if attention_count >= 3:
            examples_hint = f" Последнее: {signal_examples[0]}" if signal_examples else ""
            return f"«{topic_title}»: накопилось {attention_count} сигналов без реакции.{examples_hint}"
        if follow_up_needed:
            return f"«{topic_title}»: открытые кейсы без обновления более 6 часов — нужен follow-up."

        kind_label = self._DOMINANT_KIND_LABELS.get(dominant_kind or "", dominant_kind or "сигналы")
        stores_hint = f", точки: {', '.join(top_stores[:2])}" if top_stores else ""
        examples_hint = f" Последнее: {signal_examples[0]}" if signal_examples else ""
        return f"«{topic_title}»: активный поток ({kind_label}{stores_hint}).{examples_hint}"

    @staticmethod
    def _build_group_focus(
        *,
        critical_case_count: int,
        attention_count: int,
        follow_up_topics: int,
        open_case_count: int,
    ) -> str:
        if critical_case_count:
            return "Сначала разберите критичные темы в этой группе."
        if attention_count >= 3:
            return "В группе накопились сообщения, требующие быстрого разбора."
        if follow_up_topics:
            return "По части тем в группе нужен follow-up и проверка обратной связи."
        if open_case_count:
            return "В группе есть активные ситуации, которые стоит держать под контролем."
        return "В группе сейчас спокойный поток, достаточно наблюдения."

    @staticmethod
    def _needs_follow_up(signals: list, cases: list) -> bool:
        if not signals:
            return False
        latest_signal_time = signals[0].happened_at
        if latest_signal_time is None:
            return False
        age_hours = (datetime.now(timezone.utc) - latest_signal_time).total_seconds() / 3600
        has_open_cases = any(case.status in {"open", "watching"} for case in cases)
        return has_open_cases and age_hours >= 6

    @staticmethod
    def _action_score(section: dict) -> int:
        automation = section.get("automation") or {}
        score = 0
        priority = section.get("priority")
        if priority == "critical":
            score += 100
        elif priority == "high":
            score += 70
        elif priority == "normal":
            score += 30
        score += automation.get("critical_case_count", 0) * 20
        score += automation.get("attention_count", 0) * 10
        score += automation.get("open_case_count", 0) * 6
        if automation.get("follow_up_needed"):
            score += 18
        return score
