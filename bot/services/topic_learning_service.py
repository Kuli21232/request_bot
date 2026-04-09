from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.llm_service import LLMService
from bot.services.topic_ai_engine import DOMINANT_KIND_MAP
from models.flow import FlowCase, FlowSignal
from models.topic import TelegramTopic, TopicAIProfile

logger = logging.getLogger(__name__)

LEARNING_SYSTEM_PROMPT = (
    "Ты настраиваешь AI-профиль Telegram-топика по его истории. "
    "Смотри на сигналы, кейсы, медиа и поведение потока. "
    "Твоя задача — не фантазировать, а компактно извлечь устойчивые правила. "
    "Верни только JSON."
)


class TopicLearningService:
    def __init__(self) -> None:
        self.llm = LLMService()

    async def retrain_topic(self, session: AsyncSession, topic_id: int) -> dict | None:
        topic_repo = TopicRepository(session)
        flow_repo = FlowRepository(session)

        topic = await topic_repo.get_topic(topic_id)
        if topic is None or topic.profile is None:
            return None

        profile = topic.profile
        signals = await flow_repo.list_topic_training_signals(topic_id=topic_id, limit=80)
        cases = await flow_repo.list_topic_cases(topic_id=topic_id, limit=20)
        insights = self._build_insights(topic, signals, cases)

        generated = None
        if profile.auto_learn_enabled and signals:
            generated = await self._generate_profile_update(topic, profile, insights)

        self._apply_learning(topic, profile, insights, generated)
        await session.flush()
        return self._serialize_result(topic, profile, insights, generated)

    async def retrain_active_topics(self, session: AsyncSession, *, limit: int = 30) -> list[dict]:
        topic_repo = TopicRepository(session)
        topics = await topic_repo.list_topics()
        results: list[dict] = []

        for topic in topics:
            profile = topic.profile
            if profile is None or not topic.is_active or not profile.auto_learn_enabled:
                continue
            if topic.last_message_at is None:
                continue
            if profile.last_retrained_at and profile.last_retrained_at >= topic.last_message_at:
                continue

            trained = await self.retrain_topic(session, topic.id)
            if trained:
                results.append(trained)
            if len(results) >= limit:
                break
        return results

    def _build_insights(self, topic: TelegramTopic, signals: list[FlowSignal], cases: list[FlowCase]) -> dict:
        kind_counts = Counter(signal.kind for signal in signals if signal.kind)
        action_counts = Counter(signal.actionability for signal in signals if signal.actionability)
        importance_counts = Counter(signal.importance for signal in signals if signal.importance)
        store_counts = Counter(signal.store for signal in signals if signal.store)
        digest_counts = Counter(signal.digest_bucket for signal in signals if signal.digest_bucket)
        tag_counts = Counter(
            tag
            for signal in signals
            for tag in (signal.ai_labels or {}).get("tags", [])
            if tag
        )
        media_kind_counts = Counter(
            media.kind
            for signal in signals
            for media in signal.media_items
            if media.kind
        )
        brightness_counts = Counter(
            media.storage_meta.get("brightness_bucket")
            for signal in signals
            for media in signal.media_items
            if media.storage_meta.get("brightness_bucket")
        )
        orientation_counts = Counter(
            media.storage_meta.get("orientation")
            for signal in signals
            for media in signal.media_items
            if media.storage_meta.get("orientation")
        )
        entity_key_counts = Counter(
            key
            for signal in signals
            for key, value in (signal.entities or {}).items()
            if value not in (None, "", [], {})
        )

        dominant_signal_type = kind_counts.most_common(1)[0][0] if kind_counts else (topic.topic_kind or "request")
        topic_kind_guess = DOMINANT_KIND_MAP.get(dominant_signal_type, topic.topic_kind or "mixed")

        ranked_signals = sorted(
            signals,
            key=lambda signal: (
                1 if signal.requires_attention else 0,
                1 if signal.has_media else 0,
                signal.ai_confidence or 0.0,
                signal.happened_at.timestamp() if signal.happened_at else 0.0,
            ),
            reverse=True,
        )
        examples = [
            {
                "summary": signal.summary or signal.body[:120],
                "signal_type": signal.kind,
                "importance": signal.importance,
                "action_needed": signal.actionability,
                "store": signal.store,
                "has_media": signal.has_media,
                "body_excerpt": signal.body[:220],
            }
            for signal in ranked_signals[:6]
        ]

        case_titles = [case.title for case in cases[:6]]
        critical_cases = sum(1 for case in cases if case.is_critical)
        open_cases = sum(1 for case in cases if case.status in {"open", "watching"})

        return {
            "signal_sample_size": len(signals),
            "case_sample_size": len(cases),
            "kind_counts": dict(kind_counts),
            "action_counts": dict(action_counts),
            "importance_counts": dict(importance_counts),
            "store_counts": dict(store_counts),
            "digest_counts": dict(digest_counts),
            "tag_counts": dict(tag_counts),
            "media_kind_counts": dict(media_kind_counts),
            "brightness_counts": dict(brightness_counts),
            "orientation_counts": dict(orientation_counts),
            "entity_key_counts": dict(entity_key_counts),
            "dominant_signal_type": dominant_signal_type,
            "topic_kind_guess": topic_kind_guess,
            "examples": examples,
            "case_titles": case_titles,
            "critical_cases": critical_cases,
            "open_cases": open_cases,
        }

    async def _generate_profile_update(self, topic: TelegramTopic, profile: TopicAIProfile, insights: dict) -> dict | None:
        compact_insights = self._build_compact_insights(insights)
        prompt = (
            f"Топик: {topic.title}\n"
            f"Текущий topic_kind: {topic.topic_kind}\n"
            f"Текущий summary: {profile.profile_summary or 'нет'}\n"
            f"Текущие allowed_signal_types: {profile.allowed_signal_types}\n"
            f"Текущие default_actions: {profile.default_actions}\n"
            f"Сжатая статистика истории: {json.dumps(compact_insights, ensure_ascii=False)}\n\n"
            "Верни JSON вида:\n"
            "{"
            "\"profile_summary\": str, "
            "\"topic_kind\": str, "
            "\"allowed_signal_types\": list[str], "
            "\"default_actions\": dict, "
            "\"priority_rules\": dict, "
            "\"behavior_rules\": dict, "
            "\"examples\": list[dict]"
            "}\n"
            "Не делай поля длинными. Примеры должны быть прикладными и короткими. "
            "Если данных мало, сохрани простые и аккуратные правила без выдумок."
        )

        return await self.llm.generate_json(
            system=LEARNING_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.15,
            timeout=settings.OLLAMA_BACKGROUND_TIMEOUT,
            max_tokens=240,
        )

    def _build_compact_insights(self, insights: dict) -> dict:
        return {
            "signal_sample_size": insights["signal_sample_size"],
            "case_sample_size": insights["case_sample_size"],
            "dominant_signal_type": insights["dominant_signal_type"],
            "topic_kind_guess": insights["topic_kind_guess"],
            "critical_cases": insights["critical_cases"],
            "open_cases": insights["open_cases"],
            "kind_counts": self._top_items(insights["kind_counts"], limit=5),
            "action_counts": self._top_items(insights["action_counts"], limit=5),
            "importance_counts": self._top_items(insights["importance_counts"], limit=4),
            "store_counts": self._top_items(insights["store_counts"], limit=5),
            "tag_counts": self._top_items(insights["tag_counts"], limit=6),
            "media_kind_counts": self._top_items(insights["media_kind_counts"], limit=4),
            "entity_key_counts": self._top_items(insights["entity_key_counts"], limit=6),
            "case_titles": insights["case_titles"][:4],
            "examples": insights["examples"][:3],
        }

    def _apply_learning(
        self,
        topic: TelegramTopic,
        profile: TopicAIProfile,
        insights: dict,
        generated: dict | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        dominant_signal_type = insights["dominant_signal_type"]

        topic.topic_kind = (generated or {}).get("topic_kind") or insights["topic_kind_guess"] or topic.topic_kind
        profile.profile_summary = (generated or {}).get(
            "profile_summary"
        ) or f"Топик '{topic.title}' чаще всего содержит сигналы типа '{dominant_signal_type}'."

        allowed = (generated or {}).get("allowed_signal_types") or list(insights["kind_counts"].keys())[:6]
        if dominant_signal_type and dominant_signal_type not in allowed:
            allowed = [dominant_signal_type, *allowed]
        profile.allowed_signal_types = list(dict.fromkeys(allowed))[:8]

        default_actions = dict(profile.default_actions or {})
        default_actions.update(
            {
                "fallback": max(insights["action_counts"], key=insights["action_counts"].get)
                if insights["action_counts"]
                else default_actions.get("fallback", "digest_only"),
                "media_only": "digest_only"
                if insights["media_kind_counts"].get("photo")
                else default_actions.get("media_only", "digest_only"),
            }
        )
        if generated and isinstance(generated.get("default_actions"), dict):
            default_actions.update(generated["default_actions"])
        profile.default_actions = default_actions

        priority_rules = dict(profile.priority_rules or {})
        priority_rules.update(
            {
                "default": max(insights["importance_counts"], key=insights["importance_counts"].get)
                if insights["importance_counts"]
                else priority_rules.get("default", "normal"),
                "with_media_boost": bool(insights["media_kind_counts"]),
                "critical_case_bias": insights["critical_cases"] > 0,
            }
        )
        if generated and isinstance(generated.get("priority_rules"), dict):
            priority_rules.update(generated["priority_rules"])
        profile.priority_rules = priority_rules

        behavior_rules = dict(profile.behavior_rules or {})
        behavior_rules.update(
            {
                "topic_kind": topic.topic_kind,
                "dominant_signal_type": dominant_signal_type,
                "learned_from_history": True,
                "open_case_count": insights["open_cases"],
                "critical_case_count": insights["critical_cases"],
                "top_stores": list(insights["store_counts"].keys())[:5],
                "top_tags": list(insights["tag_counts"].keys())[:8],
                "media_patterns": {
                    "kinds": insights["media_kind_counts"],
                    "brightness": insights["brightness_counts"],
                    "orientation": insights["orientation_counts"],
                },
            }
        )
        if generated and isinstance(generated.get("behavior_rules"), dict):
            behavior_rules.update(generated["behavior_rules"])
        profile.behavior_rules = behavior_rules

        example_records = (generated or {}).get("examples") or insights["examples"]
        profile.examples = example_records[:8]

        profile.learning_snapshot = {
            **dict(profile.learning_snapshot or {}),
            "trained_at": now.isoformat(),
            "signal_sample_size": insights["signal_sample_size"],
            "case_sample_size": insights["case_sample_size"],
            "kind_counts": insights["kind_counts"],
            "action_counts": insights["action_counts"],
            "importance_counts": insights["importance_counts"],
            "store_counts": insights["store_counts"],
            "digest_counts": insights["digest_counts"],
            "tag_counts": insights["tag_counts"],
            "media_kind_counts": insights["media_kind_counts"],
            "brightness_counts": insights["brightness_counts"],
            "orientation_counts": insights["orientation_counts"],
            "entity_key_counts": insights["entity_key_counts"],
            "case_titles": insights["case_titles"],
        }

        profile.system_prompt = self._compose_system_prompt(topic, profile)
        profile.last_retrained_at = now
        profile.last_rule_update_at = now
        topic.profile_version = (topic.profile_version or 1) + 1

    def _compose_system_prompt(self, topic: TelegramTopic, profile: TopicAIProfile) -> str:
        snapshot = dict(profile.learning_snapshot or {})
        top_stores = ", ".join(list(snapshot.get("store_counts", {}).keys())[:4]) or "не выделены"
        top_tags = ", ".join(list(snapshot.get("tag_counts", {}).keys())[:6]) or "нет"
        return (
            f"Ты анализируешь сообщения из топика '{topic.title}'. "
            f"Это operational-поток типа '{topic.topic_kind}'. "
            f"Чаще всего тут встречаются сигналы: {', '.join((profile.allowed_signal_types or [])[:5])}. "
            f"Типовые магазины/точки: {top_stores}. "
            f"Частые темы и теги: {top_tags}. "
            f"Действие по умолчанию: {profile.default_actions.get('fallback', 'digest_only')}."
        )

    def _serialize_result(self, topic: TelegramTopic, profile: TopicAIProfile, insights: dict, generated: dict | None) -> dict:
        return {
            "topic_id": topic.id,
            "title": topic.title,
            "topic_kind": topic.topic_kind,
            "profile_summary": profile.profile_summary,
            "dominant_signal_type": insights["dominant_signal_type"],
            "signal_sample_size": insights["signal_sample_size"],
            "case_sample_size": insights["case_sample_size"],
            "used_ai_generation": bool(generated),
            "top_stores": list(insights["store_counts"].keys())[:5],
            "media_kinds": insights["media_kind_counts"],
        }

    @staticmethod
    def _top_items(values: dict, *, limit: int) -> dict:
        if not values:
            return {}
        return dict(sorted(values.items(), key=lambda item: item[1], reverse=True)[:limit])
