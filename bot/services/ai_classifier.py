"""AI classification of operational flow signals."""
import logging

from bot.config import settings
from bot.services.llm_service import LLMService

logger = logging.getLogger(__name__)

IMPORTANCE_RANK = {
    "low": 0,
    "normal": 1,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

URGENT_MARKERS = (
    "срочно",
    "очень срочно",
    "срочная",
    "срочный",
    "срочняк",
    "немедленно",
    "нужна помощь",
    "помогите",
    "помощь",
    "не успеваем",
    "критично",
    "горит",
    "asap",
)

BLOCKER_MARKERS = (
    "не работает",
    "не можем",
    "не получается",
    "ошибка",
    "слом",
    "проблем",
    "не бьется",
    "не проходит",
    "нет цены",
    "завис",
    "не достав",
)

CLASSIFY_SYSTEM_PROMPT = (
    "Ты operational AI-аналитик BeerShop. "
    "Твоя задача не просто сработать по шаблону, а понять смысл сообщения в рабочем потоке. "
    "Сначала подумай о контексте, рисках, срочности и полезном действии, потом верни строгий JSON. "
    "Никакого текста вне JSON."
)

CLASSIFY_PROMPT = """Проанализируй сообщение из операционного чата и верни JSON.

Нужно понять это не как тикет, а как сигнал инфопотока.

Верни ТОЛЬКО JSON со следующими полями:
- signal_type: one of [problem, request, status_update, photo_report, delivery, finance, compliance, inventory, chat/noise, escalation, news]
- summary: краткая выжимка до 12 слов
- importance: one of [low, normal, high, critical]
- action_needed: one of [ignore, digest_only, attach_to_case, create_case, suggest_escalation, suggest_reply, route_to_topic]
- store: магазин, точка или филиал если можно извлечь, иначе null
- topic_label: короткая тема кейса
- entities: JSON object с произвольными сущностями, например product, people, issue, deadline
- case_key: короткий стабильный ключ для объединения похожих сообщений
- recommended_action: краткая рекомендация для оператора
- tags: массив коротких тегов
- confidence: число от 0 до 1

Правила:
- Фото/видео отчет без явной проблемы обычно photo_report + digest_only.
- Болтовня, уточнения без действия и шум обычно chat/noise + ignore/digest_only.
- ЕГАИС, финансы, газ, поставки, не бьется товар, поломки, критичные остатки — это не noise.
- Если есть повторяющаяся проблема или нужен разбор, выбирай attach_to_case/create_case.
"""


class AIClassifier:
    def __init__(self):
        self.llm = LLMService()

    async def classify(self, text: str, topic_context: dict | None = None) -> dict | None:
        if not self.llm.enabled or not text:
            return None

        context_block = ""
        if topic_context:
            context_block = (
                "Контекст топика:\n"
                f"- title: {topic_context.get('topic_title')}\n"
                f"- topic_kind: {topic_context.get('topic_kind')}\n"
                f"- allowed_signal_types: {topic_context.get('allowed_signal_types')}\n"
                f"- default_actions: {topic_context.get('default_actions')}\n"
                f"- priority_rules: {topic_context.get('priority_rules')}\n"
                f"- behavior_rules: {topic_context.get('behavior_rules')}\n"
                f"- profile_summary: {topic_context.get('profile_summary')}\n"
                f"- examples: {topic_context.get('examples')}\n"
                f"- learning_snapshot: {topic_context.get('learning_snapshot')}\n\n"
            )

        prompt = f"{CLASSIFY_PROMPT}\n\n{context_block}Сообщение:\n{text[:3000]}"
        parsed = await self.llm.generate_json(
            system=CLASSIFY_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.15,
            timeout=min(settings.OLLAMA_BACKGROUND_TIMEOUT, 14),
            max_tokens=220,
        )
        if parsed is None:
            return None

        parsed.setdefault("signal_type", "request")
        if parsed.get("signal_type") == "chat_noise":
            parsed["signal_type"] = "chat/noise"
        parsed.setdefault("summary", text[:120])
        parsed.setdefault("importance", "normal")
        parsed.setdefault("action_needed", "digest_only")
        parsed.setdefault("entities", {})
        parsed.setdefault("tags", [])
        parsed.setdefault("confidence", 0.5)
        return self._apply_text_heuristics(parsed, text=text, topic_context=topic_context)

    def _apply_text_heuristics(self, parsed: dict, *, text: str, topic_context: dict | None) -> dict:
        normalized_text = " ".join(text.lower().replace("ё", "е").split())
        topic_title = ((topic_context or {}).get("topic_title") or "").lower().replace("ё", "е")
        topic_kind = ((topic_context or {}).get("topic_kind") or "").lower()

        has_urgent = any(marker in normalized_text for marker in URGENT_MARKERS)
        has_blocker = any(marker in normalized_text for marker in BLOCKER_MARKERS)
        is_operational_topic = topic_kind in {"logistics", "support", "incident", "compliance", "finance", "operations"}
        is_delivery_topic = "достав" in topic_title or topic_kind == "logistics"
        is_critical_domain = topic_kind in {"incident", "compliance", "finance"} or any(
            needle in normalized_text for needle in ("егаис", "газ", "чеки", "возврат")
        )

        if has_urgent:
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            if parsed.get("action_needed") in {"ignore", "digest_only"}:
                parsed["action_needed"] = "attach_to_case"

        if has_urgent and has_blocker:
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            parsed["action_needed"] = "create_case" if is_critical_domain else "attach_to_case"

        if is_delivery_topic and has_urgent:
            parsed["signal_type"] = "delivery"
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            if parsed.get("action_needed") in {"ignore", "digest_only"}:
                parsed["action_needed"] = "attach_to_case"

        if is_critical_domain and has_urgent and has_blocker:
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "critical")
            parsed["action_needed"] = "suggest_escalation"

        if is_operational_topic and normalized_text and not parsed.get("summary"):
            parsed["summary"] = text[:120]

        if not parsed.get("recommended_action") or parsed.get("recommended_action") in {"digest_only", "ignore"}:
            parsed["recommended_action"] = parsed.get("action_needed")

        return parsed

    @staticmethod
    def _raise_importance(current: str | None, target: str) -> str:
        current_rank = IMPORTANCE_RANK.get((current or "normal").lower(), 1)
        target_rank = IMPORTANCE_RANK.get(target.lower(), 1)
        if target_rank > current_rank:
            return target
        return current or target
