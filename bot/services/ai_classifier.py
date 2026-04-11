"""AI classification of operational flow signals."""

from __future__ import annotations

import logging
import re

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
    "не пробива",
)

PROBLEM_IMPACT_MARKERS = (
    "тяжело работать",
    "не можем работать",
    "неудобно работать",
    "торговля стоит",
    "касса стоит",
    "не пробиваются",
    "не пробивается",
    "не проходит",
    "не бьется",
)

CHAT_MARKERS = (
    "спасибо",
    "спс",
    "благодарю",
    "понял",
    "поняла",
    "ок",
    "окей",
    "хорошо",
    "ясно",
    "принял",
    "приняла",
    "+",
)

NON_STORE_WORDS = {
    "спасибо",
    "добрый",
    "здравствуйте",
    "привет",
    "ок",
    "окей",
    "понял",
    "поняла",
}

STATUS_MARKERS = (
    "решается",
    "сделано",
    "сделали",
    "готово",
    "готов",
    "отправил",
    "отправила",
    "скинул",
    "скинула",
    "проверю",
    "проверим",
    "передали",
    "передал",
    "направили",
    "будет",
    "завтра",
    "сегодня",
    "перезагрузите",
)

REQUEST_MARKERS = (
    "подскажите",
    "скажите",
    "можно",
    "нужно",
    "надо",
    "нужна",
    "нужен",
    "нужны",
    "скиньте",
    "отправьте",
    "когда",
    "куда",
    "как",
)

DOMAIN_MARKERS = {
    "compliance": ("егаис", "честный знак", "маркировк", "акциз"),
    "delivery": ("доставк", "маршрут", "курьер", "водител", "привез"),
    "finance": ("возврат", "чек", "оплат", "накладн", "сверк", "касс"),
    "inventory": ("товар", "остатк", "нет цены", "не бьется", "фасовк", "розлив"),
    "problem": ("тех", "пк", "принтер", "сканер", "терминал", "карта лояльности"),
    "news": ("новости", "дни рождения", "открытие"),
}

CLASSIFY_SYSTEM_PROMPT = (
    "Ты operational AI-аналитик BeerShop. "
    "Понимай сообщение по смыслу, а не по шаблону. "
    "Различай проблему, обычное общение, статус, просьбу, эскалацию и отчеты. "
    "Если в тексте уже есть поломка, блокер или боль в работе, это не просто request. "
    "Верни только строгий JSON."
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
- Фото или видео отчет без явной проблемы обычно photo_report + digest_only.
- Короткие ответы, благодарности, подтверждения, уточнения без действия обычно chat/noise или status_update.
- Если в тексте уже есть поломка, блокер, жалоба на работу процесса или операционная боль, это problem/compliance/finance/delivery, а не просто request.
- ЕГАИС, финансы, газ, поставки, не бьется товар, поломки и критичные остатки не являются noise.
- Если нужно разбирать проблему и вести ее дальше, выбирай attach_to_case/create_case.
"""


class AIClassifier:
    def __init__(self) -> None:
        self.llm = LLMService()

    async def classify(self, text: str, topic_context: dict | None = None) -> dict | None:
        if not text:
            return None

        fallback = self._fallback_classification(text, topic_context=topic_context)
        if not self.llm.enabled:
            return fallback

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
            max_tokens=260,
        )
        if parsed is None:
            return fallback

        parsed.setdefault("signal_type", "request")
        if parsed.get("signal_type") == "chat_noise":
            parsed["signal_type"] = "chat/noise"
        parsed.setdefault("summary", text[:120])
        parsed.setdefault("importance", "normal")
        parsed.setdefault("action_needed", "digest_only")
        parsed.setdefault("entities", {})
        parsed.setdefault("tags", [])
        parsed.setdefault("confidence", 0.5)

        parsed = self._apply_text_heuristics(parsed, text=text, topic_context=topic_context)
        return self._merge_with_fallback(parsed, fallback)

    def _apply_text_heuristics(self, parsed: dict, *, text: str, topic_context: dict | None) -> dict:
        normalized_text = self._normalize(text)
        topic_title = self._normalize((topic_context or {}).get("topic_title") or "")
        topic_kind = self._normalize((topic_context or {}).get("topic_kind") or "")

        has_urgent = any(marker in normalized_text for marker in URGENT_MARKERS)
        has_blocker = any(marker in normalized_text for marker in BLOCKER_MARKERS)
        has_impact = any(marker in normalized_text for marker in PROBLEM_IMPACT_MARKERS)
        is_delivery_topic = "достав" in topic_title or topic_kind == "logistics"
        is_finance_topic = "возврат" in topic_title or topic_kind == "finance"
        is_compliance_topic = "егаис" in topic_title or topic_kind == "compliance"

        if has_urgent:
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            if parsed.get("action_needed") in {"ignore", "digest_only"}:
                parsed["action_needed"] = "attach_to_case"

        if has_blocker or has_impact:
            if parsed.get("signal_type") in {"request", "status_update"}:
                parsed["signal_type"] = "problem"
            if parsed.get("action_needed") in {"ignore", "digest_only", "suggest_reply"}:
                parsed["action_needed"] = "attach_to_case"

        if is_delivery_topic and (has_urgent or has_blocker or has_impact):
            parsed["signal_type"] = "delivery"
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            parsed["action_needed"] = "attach_to_case"

        if is_finance_topic and (has_blocker or has_impact):
            parsed["signal_type"] = "finance"
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            parsed["action_needed"] = "create_case"

        if is_compliance_topic and (has_blocker or has_impact or "честный знак" in normalized_text):
            parsed["signal_type"] = "compliance"
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            parsed["action_needed"] = "create_case" if has_urgent else "attach_to_case"

        if not parsed.get("recommended_action") or parsed.get("recommended_action") in {"digest_only", "ignore"}:
            parsed["recommended_action"] = parsed.get("action_needed")

        return parsed

    def _fallback_classification(self, text: str, *, topic_context: dict | None) -> dict:
        normalized_text = self._normalize(text)
        topic_title = self._normalize((topic_context or {}).get("topic_title") or "")
        topic_kind = self._normalize((topic_context or {}).get("topic_kind") or "")
        words = self._split_words(normalized_text)

        has_question = "?" in text
        has_urgent = any(marker in normalized_text for marker in URGENT_MARKERS)
        has_blocker = any(marker in normalized_text for marker in BLOCKER_MARKERS)
        has_impact = any(marker in normalized_text for marker in PROBLEM_IMPACT_MARKERS)
        has_status = any(marker in normalized_text for marker in STATUS_MARKERS)
        has_request = has_question or any(marker in normalized_text for marker in REQUEST_MARKERS)
        looks_like_chat = len(words) <= 4 and any(marker in normalized_text for marker in CHAT_MARKERS)

        domain = self._detect_domain(normalized_text, topic_title=topic_title, topic_kind=topic_kind)
        signal_type = "request"
        importance = "normal"
        action_needed = "digest_only"
        topic_label = (topic_context or {}).get("topic_title") or "Операционный поток"
        tags: list[str] = []

        if looks_like_chat:
            signal_type = "chat/noise"
            importance = "low"
            action_needed = "ignore"
        elif has_status and not (has_blocker or has_impact):
            signal_type = "status_update"
            importance = "low" if len(words) <= 6 else "normal"
            action_needed = "digest_only"
        elif has_blocker or has_impact:
            signal_type = self._domain_to_signal_type(domain)
            importance = "high" if has_urgent or has_impact else "normal"
            action_needed = "create_case" if has_urgent or domain in {"compliance", "finance"} else "attach_to_case"
        elif has_request:
            signal_type = self._domain_to_signal_type(domain, default="request")
            importance = "high" if has_urgent else "normal"
            action_needed = "suggest_reply" if signal_type == "request" else "attach_to_case"
        elif topic_kind == "reporting":
            signal_type = "photo_report"
            importance = "low"
            action_needed = "digest_only"
        elif topic_kind in {"incident", "support", "compliance", "finance"}:
            signal_type = self._domain_to_signal_type(domain)
            importance = "normal"
            action_needed = "attach_to_case"

        if domain:
            tags.append(domain)
            topic_label = self._domain_to_topic_label(domain, topic_label)

        if "не можем работать" in normalized_text or "тяжело работать" in normalized_text:
            importance = self._raise_importance(importance, "high")
            if action_needed in {"ignore", "digest_only", "suggest_reply"}:
                action_needed = "attach_to_case"

        summary = self._build_summary(text, signal_type=signal_type, topic_label=topic_label)
        recommended_action = self._build_recommendation(
            signal_type=signal_type,
            action_needed=action_needed,
            topic_label=topic_label,
            importance=importance,
        )
        entities = self._extract_entities(text, normalized_text=normalized_text, domain=domain)

        return {
            "signal_type": signal_type,
            "summary": summary,
            "importance": importance,
            "action_needed": action_needed,
            "store": entities.get("store"),
            "topic_label": topic_label,
            "entities": entities,
            "case_key": self._build_case_key(domain=domain, topic_label=topic_label, entities=entities),
            "recommended_action": recommended_action,
            "tags": tags,
            "confidence": 0.74 if signal_type not in {"request", "chat/noise"} else 0.63,
        }

    def _merge_with_fallback(self, parsed: dict, fallback: dict) -> dict:
        result = dict(parsed)
        parsed_confidence = float(parsed.get("confidence") or 0.0)
        fallback_confidence = float(fallback.get("confidence") or 0.0)

        if parsed.get("signal_type") in {"request", "status_update"} and fallback.get("signal_type") not in {"request", "status_update"}:
            if parsed_confidence < 0.8 or self._is_more_urgent(fallback, parsed):
                result["signal_type"] = fallback["signal_type"]

        if self._is_more_urgent(fallback, result):
            result["importance"] = fallback["importance"]
            result["action_needed"] = fallback["action_needed"]
            result["recommended_action"] = fallback["recommended_action"]

        for field in ("summary", "topic_label", "case_key"):
            current_value = result.get(field)
            fallback_value = fallback.get(field)
            if fallback_value and (not current_value or current_value in {"request", "Операционный поток"}):
                result[field] = fallback_value

        if not result.get("recommended_action"):
            result["recommended_action"] = fallback.get("recommended_action")
        if not result.get("entities"):
            result["entities"] = fallback.get("entities", {})

        merged_tags = list(dict.fromkeys([*(result.get("tags") or []), *(fallback.get("tags") or [])]))
        result["tags"] = merged_tags
        result["confidence"] = max(parsed_confidence, fallback_confidence)
        return result

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().replace("ё", "е").split())

    @staticmethod
    def _split_words(text: str) -> list[str]:
        return re.findall(r"[a-zA-Zа-яА-Я0-9]+", text)

    def _detect_domain(self, normalized_text: str, *, topic_title: str, topic_kind: str) -> str | None:
        for domain, markers in DOMAIN_MARKERS.items():
            if any(marker in normalized_text or marker in topic_title for marker in markers):
                return domain
        if topic_kind in {"compliance", "finance", "inventory"}:
            return topic_kind
        if topic_kind == "logistics":
            return "delivery"
        if topic_kind in {"support", "incident"}:
            return "problem"
        if topic_kind == "reporting":
            return "photo_report"
        return None

    @staticmethod
    def _domain_to_signal_type(domain: str | None, default: str = "problem") -> str:
        if domain in {"compliance", "delivery", "finance", "inventory", "news"}:
            return domain
        if domain == "photo_report":
            return "photo_report"
        if domain == "problem":
            return "problem"
        return default

    @staticmethod
    def _domain_to_topic_label(domain: str, fallback: str) -> str:
        return {
            "compliance": "ЕГАИС и маркировка",
            "finance": "Финансовый вопрос",
            "delivery": "Доставка",
            "inventory": "Товар и остатки",
            "photo_report": "Фотоотчет",
            "problem": "Операционная проблема",
            "news": "Новости",
        }.get(domain, fallback)

    @staticmethod
    def _build_summary(text: str, *, signal_type: str, topic_label: str) -> str:
        clean = " ".join(text.split())
        if signal_type == "chat/noise":
            return "Короткое обсуждение без действия"
        first_sentence = re.split(r"(?<=[.!?])\s+", clean)[0].strip() if clean else topic_label
        if len(first_sentence) > 90:
            first_sentence = first_sentence[:89].rstrip() + "…"
        if len(first_sentence.split()) <= 2:
            return topic_label
        return first_sentence or topic_label

    @staticmethod
    def _build_recommendation(*, signal_type: str, action_needed: str, topic_label: str, importance: str) -> str:
        if action_needed == "create_case":
            return f"Открыть ситуацию по теме: {topic_label}"
        if action_needed == "attach_to_case":
            return f"Добавить в разбор по теме: {topic_label}"
        if action_needed == "suggest_escalation":
            return f"Эскалировать тему: {topic_label}"
        if action_needed == "suggest_reply":
            return "Подготовить ответ и уточнить детали"
        if signal_type == "chat/noise":
            return "Не требует отдельного действия"
        if importance in {"high", "critical"}:
            return f"Проверить вручную: {topic_label}"
        return "Оставить в сводке"

    @staticmethod
    def _build_case_key(*, domain: str | None, topic_label: str, entities: dict) -> str:
        base = domain or "operations"
        store = str(entities.get("store") or "all").lower()
        label = re.sub(r"[^a-z0-9а-я]+", "-", topic_label.lower()).strip("-")
        return f"{base}:{store}:{label[:40]}"

    @staticmethod
    def _extract_entities(text: str, *, normalized_text: str, domain: str | None) -> dict:
        entities: dict = {}
        store_match = re.match(r"^\s*([А-ЯA-Z][\w-]{2,}(?:\s+[А-ЯA-Z][\w-]{2,}){0,2})[\s,:.-]", text)
        if store_match:
            candidate = store_match.group(1).strip()
            if candidate.lower() not in NON_STORE_WORDS:
                entities["store"] = candidate

        matched_issues = [marker for marker in (*BLOCKER_MARKERS, *PROBLEM_IMPACT_MARKERS) if marker in normalized_text]
        if matched_issues:
            entities["issue"] = matched_issues[:3]
        if domain:
            entities["domain"] = domain
        return entities

    def _is_more_urgent(self, candidate: dict, current: dict) -> bool:
        current_rank = IMPORTANCE_RANK.get(str(current.get("importance") or "normal").lower(), 1)
        candidate_rank = IMPORTANCE_RANK.get(str(candidate.get("importance") or "normal").lower(), 1)
        if candidate_rank > current_rank:
            return True

        urgent_actions = {"attach_to_case", "create_case", "suggest_escalation", "route_to_topic"}
        return candidate.get("action_needed") in urgent_actions and current.get("action_needed") not in urgent_actions

    @staticmethod
    def _raise_importance(current: str | None, target: str) -> str:
        current_rank = IMPORTANCE_RANK.get((current or "normal").lower(), 1)
        target_rank = IMPORTANCE_RANK.get(target.lower(), 1)
        if target_rank > current_rank:
            return target
        return current or target
