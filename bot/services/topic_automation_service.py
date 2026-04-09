from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.topic_repo import TopicRepository

logger = logging.getLogger(__name__)


class TopicAutomationService:
    def __init__(self) -> None:
        self.flow_repo = None
        self.topic_repo = None

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

        if critical_case_count or any(signal.importance == "critical" for signal in signals):
            priority = "critical"
            recommended_action = "suggest_escalation"
        elif attention_count or open_case_count >= 2:
            priority = "high"
            recommended_action = "review_topic_queue"
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
            signals=signals,
            cases=cases,
            dominant_kind=dominant_kind,
            attention_count=attention_count,
            critical_case_count=critical_case_count,
            top_stores=top_stores,
            signal_examples=signal_examples,
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
        }

    def _build_summary(
        self,
        *,
        topic_title: str,
        signals: list,
        cases: list,
        dominant_kind: str | None,
        attention_count: int,
        critical_case_count: int,
        top_stores: list[str],
        signal_examples: list[str],
    ) -> str:
        if not signals:
            return f"Топик «{topic_title}» пока только собирает контекст."

        parts: list[str] = []
        if dominant_kind:
            parts.append(f"основной тип потока: {dominant_kind}")
        if attention_count:
            parts.append(f"есть {attention_count} сообщений, требующих внимания")
        if critical_case_count:
            parts.append(f"{critical_case_count} критичных ситуаций")
        if top_stores:
            parts.append(f"чаще всего упоминаются точки: {', '.join(top_stores[:3])}")
        if signal_examples:
            parts.append(f"последние темы: {'; '.join(signal_examples[:2])}")
        if not parts:
            parts.append(f"в топике «{topic_title}» идет обычный рабочий поток")
        return "В топике " + " и ".join(parts) + "."
