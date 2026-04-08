from datetime import datetime, timezone

from models.topic import TelegramTopic, TopicAIProfile


TOPIC_HINTS = [
    ("егаис", {"signal_type": "compliance", "action": "create_case", "importance": "high", "topic_kind": "compliance"}),
    ("газ", {"signal_type": "problem", "action": "suggest_escalation", "importance": "critical", "topic_kind": "incident"}),
    ("фото", {"signal_type": "photo_report", "action": "digest_only", "importance": "low", "topic_kind": "reporting"}),
    ("отчет", {"signal_type": "photo_report", "action": "digest_only", "importance": "low", "topic_kind": "reporting"}),
    ("доставка", {"signal_type": "delivery", "action": "attach_to_case", "importance": "normal", "topic_kind": "logistics"}),
    ("возврат", {"signal_type": "finance", "action": "create_case", "importance": "high", "topic_kind": "finance"}),
    ("чек", {"signal_type": "finance", "action": "attach_to_case", "importance": "high", "topic_kind": "finance"}),
    ("тех", {"signal_type": "problem", "action": "route_to_topic", "importance": "high", "topic_kind": "support"}),
]


class TopicAIEngine:
    def bootstrap_profile(self, topic: TelegramTopic, profile: TopicAIProfile) -> TopicAIProfile:
        title = (topic.title or "").lower()
        defaults = {
            "signal_type": "request",
            "action": "digest_only",
            "importance": "normal",
            "topic_kind": "mixed",
        }
        for needle, rules in TOPIC_HINTS:
            if needle in title:
                defaults.update(rules)
                break

        topic.topic_kind = defaults["topic_kind"]
        profile.allowed_signal_types = profile.allowed_signal_types or [defaults["signal_type"], "status_update", "chat/noise"]
        profile.default_actions = profile.default_actions or {
            "fallback": defaults["action"],
            "media_only": "digest_only",
        }
        profile.priority_rules = profile.priority_rules or {
            "default": defaults["importance"],
            "with_media_boost": topic.topic_kind in {"incident", "support", "finance"},
        }
        profile.media_policy = profile.media_policy or {
            "store_preview_in_db": True,
            "image_max_side": 1280,
            "image_quality": 60,
        }
        profile.behavior_rules = profile.behavior_rules or {
            "topic_kind": topic.topic_kind,
            "title_hint": defaults["signal_type"],
            "strict_allowed_types": False,
        }
        profile.profile_summary = profile.profile_summary or f"AI профиль для топика '{topic.title}'"
        profile.system_prompt = profile.system_prompt or self._build_system_prompt(topic, profile, defaults)
        return profile

    def build_context(self, topic: TelegramTopic, profile: TopicAIProfile) -> dict:
        self.bootstrap_profile(topic, profile)
        return {
            "topic_title": topic.title,
            "topic_kind": topic.topic_kind,
            "allowed_signal_types": profile.allowed_signal_types,
            "default_actions": profile.default_actions,
            "priority_rules": profile.priority_rules,
            "behavior_rules": profile.behavior_rules,
            "profile_summary": profile.profile_summary,
        }

    def apply_profile(self, ai_result: dict | None, topic: TelegramTopic, profile: TopicAIProfile, *, has_media: bool) -> dict:
        self.bootstrap_profile(topic, profile)
        result = dict(ai_result or {})
        result.setdefault("signal_type", profile.behavior_rules.get("title_hint", "request"))
        result.setdefault("importance", profile.priority_rules.get("default", "normal"))
        result.setdefault("action_needed", profile.default_actions.get("fallback", "digest_only"))
        result.setdefault("summary", topic.title)
        result.setdefault("recommended_action", profile.default_actions.get("fallback", "digest_only"))

        if has_media:
            media_default = profile.default_actions.get("media_only")
            if result["signal_type"] in {"request", "status_update"} and media_default:
                result["signal_type"] = "photo_report"
                result["action_needed"] = media_default

        allowed = set(profile.allowed_signal_types or [])
        if allowed and result.get("signal_type") not in allowed and not profile.behavior_rules.get("strict_allowed_types"):
            allowed.add(result.get("signal_type"))
            profile.allowed_signal_types = sorted(allowed)

        if has_media and profile.priority_rules.get("with_media_boost") and result.get("importance") == "normal":
            result["importance"] = "high"

        return result

    def observe_signal(
        self,
        profile: TopicAIProfile,
        *,
        signal_type: str,
        action_needed: str,
        importance: str,
        has_media: bool,
    ) -> None:
        snapshot = dict(profile.learning_snapshot or {})
        snapshot["total_messages"] = snapshot.get("total_messages", 0) + 1
        snapshot["with_media"] = snapshot.get("with_media", 0) + (1 if has_media else 0)
        snapshot.setdefault("signal_types", {})
        snapshot["signal_types"][signal_type] = snapshot["signal_types"].get(signal_type, 0) + 1
        snapshot.setdefault("actions", {})
        snapshot["actions"][action_needed] = snapshot["actions"].get(action_needed, 0) + 1
        snapshot.setdefault("importance", {})
        snapshot["importance"][importance] = snapshot["importance"].get(importance, 0) + 1
        profile.learning_snapshot = snapshot
        profile.last_rule_update_at = datetime.now(timezone.utc)

    def _build_system_prompt(self, topic: TelegramTopic, profile: TopicAIProfile, defaults: dict) -> str:
        return (
            f"Ты анализируешь сообщения из топика '{topic.title}'. "
            f"Это operational поток типа '{defaults['topic_kind']}'. "
            f"Старайся использовать типы {', '.join(profile.allowed_signal_types or [defaults['signal_type']])} "
            f"и действие по умолчанию {defaults['action']}."
        )
