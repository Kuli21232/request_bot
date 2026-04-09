from datetime import datetime, timezone

from models.topic import TelegramTopic, TopicAIProfile


TOPIC_HINTS = [
    ("егаис", {"signal_type": "compliance", "action": "create_case", "importance": "high", "topic_kind": "compliance"}),
    ("газ", {"signal_type": "problem", "action": "suggest_escalation", "importance": "critical", "topic_kind": "incident"}),
    ("фото", {"signal_type": "photo_report", "action": "digest_only", "importance": "low", "topic_kind": "reporting"}),
    ("отчет", {"signal_type": "photo_report", "action": "digest_only", "importance": "low", "topic_kind": "reporting"}),
    ("доставка", {"signal_type": "delivery", "action": "attach_to_case", "importance": "normal", "topic_kind": "logistics"}),
    ("возврат", {"signal_type": "finance", "action": "create_case", "importance": "high", "topic_kind": "finance"}),
    ("чеки", {"signal_type": "finance", "action": "attach_to_case", "importance": "high", "topic_kind": "finance"}),
    ("тех", {"signal_type": "problem", "action": "route_to_topic", "importance": "high", "topic_kind": "support"}),
]

DOMINANT_KIND_MAP = {
    "compliance": "compliance",
    "finance": "finance",
    "delivery": "logistics",
    "photo_report": "reporting",
    "problem": "support",
    "escalation": "incident",
    "inventory": "inventory",
    "request": "operations",
    "status_update": "operations",
    "chat/noise": "mixed",
    "news": "news",
}


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

        topic.topic_kind = topic.topic_kind or defaults["topic_kind"]
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
            "dominant_signal_type": defaults["signal_type"],
        }
        profile.profile_summary = profile.profile_summary or f"AI-профиль для топика '{topic.title}'"
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
            "examples": (profile.examples or [])[:4],
            "learning_snapshot": {
                "store_counts": dict(profile.learning_snapshot or {}).get("store_counts", {}),
                "tag_counts": dict(profile.learning_snapshot or {}).get("tag_counts", {}),
                "media_kind_counts": dict(profile.learning_snapshot or {}).get("media_kind_counts", {}),
                "case_titles": dict(profile.learning_snapshot or {}).get("case_titles", [])[:5],
            },
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
        topic: TelegramTopic,
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
        self.refresh_topic_shape(topic, profile)

    def refresh_topic_shape(self, topic: TelegramTopic, profile: TopicAIProfile) -> None:
        snapshot = dict(profile.learning_snapshot or {})
        signal_types = snapshot.get("signal_types") or {}
        if not signal_types:
            return

        dominant_signal_type = max(signal_types.items(), key=lambda item: item[1])[0]
        behavior_rules = dict(profile.behavior_rules or {})
        behavior_rules["dominant_signal_type"] = dominant_signal_type
        profile.behavior_rules = behavior_rules
        topic.topic_kind = DOMINANT_KIND_MAP.get(dominant_signal_type, topic.topic_kind or "mixed")
        profile.profile_summary = (
            f"Топик '{topic.title}' чаще всего содержит сообщения типа "
            f"'{dominant_signal_type}' и ведет себя как поток '{topic.topic_kind}'."
        )
        topic.profile_version = (topic.profile_version or 1) + 1

    def sort_topics(self, topics: list[TelegramTopic], metrics: dict[int, dict]) -> list[dict]:
        ranked: list[dict] = []
        now = datetime.now(timezone.utc)

        for topic in topics:
            profile = topic.profile
            if profile is None:
                continue

            self.bootstrap_profile(topic, profile)
            stat = metrics.get(topic.id, {})
            signal_count = stat.get("signal_count", topic.signal_count or 0)
            attention_count = stat.get("attention_count", 0)
            media_signal_count = stat.get("media_signal_count", topic.media_count or 0)
            critical_case_count = stat.get("critical_case_count", 0)
            open_case_count = stat.get("open_case_count", 0)
            last_signal_at = stat.get("last_signal_at") or topic.last_seen_at or topic.last_message_at

            score = 0
            reasons: list[str] = []

            score += attention_count * 8
            if attention_count:
                reasons.append(f"требуют внимания: {attention_count}")

            score += critical_case_count * 12
            if critical_case_count:
                reasons.append(f"критичных ситуаций: {critical_case_count}")

            score += open_case_count * 5
            if open_case_count:
                reasons.append(f"активных ситуаций: {open_case_count}")

            score += min(signal_count, 20)
            if media_signal_count:
                score += min(media_signal_count, 5)

            if last_signal_at:
                age_hours = max((now - last_signal_at).total_seconds() / 3600, 0)
                if age_hours <= 2:
                    score += 8
                    reasons.append("свежая активность")
                elif age_hours <= 24:
                    score += 4
                elif age_hours <= 72:
                    score += 2

            dominant_signal = (profile.behavior_rules or {}).get("dominant_signal_type") or (
                profile.behavior_rules or {}
            ).get("title_hint")
            if dominant_signal in {"escalation", "problem", "compliance", "finance"}:
                score += 6
            if dominant_signal == "chat/noise" and attention_count == 0 and open_case_count == 0:
                score -= 6
                reasons.append("в основном шум")
            if topic.topic_kind == "reporting" and attention_count == 0:
                score -= 3

            if score >= 26:
                priority = "critical"
            elif score >= 16:
                priority = "high"
            elif score >= 8:
                priority = "normal"
            else:
                priority = "low"

            ranked.append(
                {
                    "topic": topic,
                    "profile": profile,
                    "score": score,
                    "priority": priority,
                    "dominant_signal_type": dominant_signal,
                    "metrics": {
                        "signal_count": signal_count,
                        "attention_count": attention_count,
                        "media_signal_count": media_signal_count,
                        "critical_case_count": critical_case_count,
                        "open_case_count": open_case_count,
                        "last_signal_at": last_signal_at,
                    },
                    "reasons": reasons,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["metrics"]["attention_count"],
                item["metrics"]["open_case_count"],
                item["metrics"]["signal_count"],
            ),
            reverse=True,
        )
        return ranked

    def _build_system_prompt(self, topic: TelegramTopic, profile: TopicAIProfile, defaults: dict) -> str:
        return (
            f"Ты анализируешь сообщения из топика '{topic.title}'. "
            f"Это operational поток типа '{defaults['topic_kind']}'. "
            f"Старайся использовать типы {', '.join(profile.allowed_signal_types or [defaults['signal_type']])} "
            f"и действие по умолчанию {defaults['action']}."
        )
