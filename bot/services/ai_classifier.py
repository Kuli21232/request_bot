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
    "пожар",
    "аврал",
    "стоит",
    "встала",
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
    "зависло",
    "сломался",
    "не открывается",
    "не включается",
    "не подключается",
    "не отвечает",
    "недоступен",
    "недоступно",
    "отказывает",
    "выдает ошибку",
    "не принимает",
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
    "продажи стоят",
    "работа встала",
    "очередь",
    "клиенты ждут",
    "покупатели ждут",
)

# Comprehensive noise word set — single words and short phrases that are pure chat
CHAT_NOISE_WORDS: frozenset[str] = frozenset({
    "спасибо", "спс", "спасибо большое", "благодарю", "благодарим",
    "понял", "поняла", "поняли", "понятно", "понятненько", "ясно",
    "ок", "окей", "ok", "o'k", "oke", "хорошо", "хор",
    "принял", "приняла", "приняли", "принято", "принято к сведению",
    "договорились", "договорились", "лады", "ладно", "добро", "збс",
    "+", "++", "+++", "ок+",
    "класс", "отлично", "отл", "супер", "👍", "✅", "💯", "🔥", "👌",
    "пожалуйста", "пжл", "пж", "нжл",
    "увидел", "увидела", "услышал", "услышала",
    "момент", "секунду", "минуту", "одну минуту",
    "всё понятно", "все понятно",
    "все", "всё", "ок всё", "ок все",
    "принято в работу", "взял в работу", "взяла в работу", "взяли в работу",
    "уже", "сейчас",
    "посмотрю", "посмотрим", "посмотрела", "посмотрел",
    "смотрю", "смотрим",
    "занимаемся", "занимаюсь",
    "узнаю", "узнаем", "узнала", "узнал",
    "уточню", "уточним", "уточнила", "уточнил",
    "спрошу", "спросим", "спросила", "спросил",
    "разберусь", "разберемся", "разберём",
    "буду", "будем",
})

# Regex patterns that definitively indicate pure noise
_NOISE_RE = re.compile(
    r"^(?:"
    r"\s*[👍✅💯🔥👌👀🙏😊😁👋✔️☑️🆗]+\s*"  # emoji only
    r"|[+\-]{1,5}"                              # just plus/minus signs
    r"|\d{1,2}"                                 # single 1-2 digit number
    r")\s*$",
    re.UNICODE,
)

NON_STORE_WORDS = {
    "спасибо", "добрый", "здравствуйте", "привет", "ок", "окей", "понял", "поняла",
    "всем", "всё", "уже", "сейчас", "хорошо",
}

STATUS_MARKERS = (
    "решается", "сделано", "сделали", "готово", "готов",
    "отправил", "отправила", "скинул", "скинула", "отправили", "скинули",
    "проверю", "проверим", "проверила", "проверил",
    "передали", "передал", "передала", "направили", "направил",
    "будет", "завтра", "сегодня", "к утру", "к вечеру",
    "перезагрузили", "перезагрузил", "перезапустили", "перезапустил",
    "исправили", "исправил", "починили", "починил", "устранили", "устранил",
    "закрыли", "закрыл", "закрыла",
    "приедет", "едет", "выехал", "выехала", "выехали", "в пути",
    "заказали", "заказал", "заказала",
    "дозвонились", "дозвонился", "связались", "связался",
    "уже работает", "заработало", "работает снова",
    "выполнено", "завершено", "загружено", "обновили", "обновил",
    "загрузили", "загрузил",
)

REQUEST_MARKERS = (
    "подскажите", "скажите", "можно", "нужно", "надо", "нужна", "нужен", "нужны",
    "скиньте", "отправьте", "когда", "куда", "как", "почему", "зачем",
    "можете ли", "можете помочь", "поможете",
    "не знаю", "не понимаю", "помогите разобраться",
    "где брать", "где взять", "откуда", "у кого",
)

ESCALATION_MARKERS = (
    "эскалация", "эскалирую", "эскалируем",
    "директор", "руководитель", "начальник",
    "подключите", "подключитесь",
    "невозможно решить", "не можем решить",
    "второй день", "третий день", "уже давно",
    "написали несколько раз", "снова та же",
    "ничего не меняется", "без результата",
    "неприемлемо", "так дальше нельзя",
)

DOMAIN_MARKERS = {
    "compliance": ("егаис", "честный знак", "маркировк", "акциз", "фсрар", "алкогол"),
    "delivery": ("доставк", "маршрут", "курьер", "водител", "привез", "поставк", "тн ", "ttн", "накладная"),
    "finance": ("возврат", "чек", "оплат", "накладн", "сверк", "касс", "инкассац", "выручк", "z-отчет", "икс-отчет"),
    "inventory": ("товар", "остатк", "нет цены", "не бьется", "фасовк", "розлив", "цена", "штрихкод"),
    "incident": ("тех", "пк", "принтер", "сканер", "терминал", "интернет", "роутер", "считыватель"),
    "news": ("новости", "дни рождения", "открытие", "объявление", "информируем", "напоминаем"),
    "hr": ("сотрудник", "увольнени", "принят", "стажер", "замен", "отпуск", "больничн"),
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
- signal_type: one of [problem, request, status_update, photo_report, delivery, finance, compliance, inventory, incident, chat/noise, escalation, news, hr]
- summary: краткая выжимка до 12 слов — конкретная, не "сообщение про..."
- importance: one of [low, normal, high, critical]
- action_needed: one of [ignore, digest_only, attach_to_case, create_case, suggest_escalation, suggest_reply, route_to_topic]
- store: магазин, точка или филиал если можно извлечь, иначе null
- topic_label: короткая тема кейса
- entities: JSON object с произвольными сущностями, например product, people, issue, deadline
- case_key: короткий стабильный ключ для объединения похожих сообщений
- recommended_action: краткая рекомендация для оператора
- tags: массив коротких тегов
- confidence: число от 0 до 1

Правила классификации:
- chat/noise + ignore: короткие ответы ("ок", "спасибо", "понял"), эмодзи, подтверждения без действия.
- status_update + digest_only: "сделали", "отправили", "едет", "готово", "перезагрузили".
- photo_report + digest_only: фото или видео отчет без явной проблемы.
- request + suggest_reply: вопрос, просьба, уточнение без блокера.
- problem + attach_to_case: поломка, ошибка, "не работает", не критично.
- incident + create_case: касса стоит, торговля стоит, все не работает.
- escalation + suggest_escalation: несколько дней без решения, подключите руководство.
- compliance + create_case: ЕГАИС, честный знак, акциз не бьется.
- finance + create_case: возврат чека, проблема с кассой, сверка.
- delivery + attach_to_case: проблема с поставкой, курьер не приехал.
- inventory + attach_to_case: нет цены, не бьется товар, нет остатков.
- ЕГАИС, финансы, газ, поставки, не бьется товар — никогда не noise.
"""


class AIClassifier:
    def __init__(self) -> None:
        self.llm = LLMService()

    @staticmethod
    def is_definitely_noise(text: str, *, has_media: bool = False) -> bool:
        """Fast pre-filter. Returns True only if message is certainly chat/noise.
        Safe to skip entirely — will not match any operational signal."""
        if has_media:
            return False
        if not text:
            return True
        stripped = text.strip()
        # Emoji/symbol only
        if _NOISE_RE.match(stripped):
            return True
        normalized = " ".join(stripped.lower().replace("ё", "е").split())
        # Entire message is a known noise phrase
        if normalized in CHAT_NOISE_WORDS:
            return True
        # Very short (≤3 words) and contains no operational indicators
        words = re.findall(r"[a-zA-Zа-яА-Я0-9]+", normalized)
        if len(words) <= 3:
            op_words = [w for w in words if w not in CHAT_NOISE_WORDS and len(w) > 2]
            has_question = "?" in stripped
            has_domain = any(
                any(m in normalized for m in markers)
                for markers in DOMAIN_MARKERS.values()
            )
            if not op_words and not has_question and not has_domain:
                return True
        return False

    async def classify(self, text: str, topic_context: dict | None = None) -> dict | None:
        if not text:
            return None

        fallback = self._fallback_classification(text, topic_context=topic_context)
        if not self.llm.enabled:
            logger.debug(
                "LLM disabled, fallback: type=%s importance=%s action=%s",
                fallback.get("signal_type"), fallback.get("importance"), fallback.get("action_needed"),
            )
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
            max_tokens=300,
        )
        if parsed is None:
            logger.debug("LLM returned no result, using heuristic fallback")
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
        result = self._merge_with_fallback(parsed, fallback)
        logger.debug(
            "LLM classified: type=%s importance=%s confidence=%.2f",
            result.get("signal_type"), result.get("importance"), result.get("confidence", 0),
        )
        return result

    def _apply_text_heuristics(self, parsed: dict, *, text: str, topic_context: dict | None) -> dict:
        normalized_text = self._normalize(text)
        topic_title = self._normalize((topic_context or {}).get("topic_title") or "")
        topic_kind = self._normalize((topic_context or {}).get("topic_kind") or "")

        has_urgent = any(marker in normalized_text for marker in URGENT_MARKERS)
        has_blocker = any(marker in normalized_text for marker in BLOCKER_MARKERS)
        has_impact = any(marker in normalized_text for marker in PROBLEM_IMPACT_MARKERS)
        has_escalation = any(marker in normalized_text for marker in ESCALATION_MARKERS)
        is_delivery_topic = "достав" in topic_title or topic_kind == "logistics"
        is_finance_topic = "возврат" in topic_title or topic_kind == "finance"
        is_compliance_topic = "егаис" in topic_title or topic_kind == "compliance"

        if has_escalation:
            parsed["signal_type"] = "escalation"
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            parsed["action_needed"] = "suggest_escalation"

        if has_urgent:
            parsed["importance"] = self._raise_importance(parsed.get("importance"), "high")
            if parsed.get("action_needed") in {"ignore", "digest_only"}:
                parsed["action_needed"] = "attach_to_case"

        if has_blocker or has_impact:
            if parsed.get("signal_type") in {"request", "status_update", "chat/noise"}:
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
        has_escalation = any(marker in normalized_text for marker in ESCALATION_MARKERS)
        is_media_topic = topic_kind == "reporting"

        # Noise detection: non-operational words only, short message
        op_words = [
            w for w in words
            if w not in CHAT_NOISE_WORDS
            and len(w) > 2
            and not any(m in w for m in ("спасибо", "хорош", "принят", "понял", "поняла", "договор"))
        ]
        has_domain = any(
            any(m in normalized_text or m in topic_title for m in markers)
            for markers in DOMAIN_MARKERS.values()
        )

        looks_like_noise = (
            not op_words
            and not has_question
            and not has_domain
            and not has_blocker
            and not has_impact
            and not has_urgent
        )

        domain = self._detect_domain(normalized_text, topic_title=topic_title, topic_kind=topic_kind)
        signal_type = "request"
        importance = "normal"
        action_needed = "digest_only"
        topic_label = (topic_context or {}).get("topic_title") or "Операционный поток"
        tags: list[str] = []

        if looks_like_noise:
            signal_type = "chat/noise"
            importance = "low"
            action_needed = "ignore"

        elif has_escalation:
            signal_type = "escalation"
            importance = "high"
            action_needed = "suggest_escalation"

        elif has_impact or (has_blocker and has_urgent):
            # Critical operational blocker
            signal_type = self._domain_to_signal_type(domain, default="incident")
            importance = "critical" if has_urgent else "high"
            action_needed = "create_case"

        elif has_blocker:
            signal_type = self._domain_to_signal_type(domain, default="problem")
            importance = "high" if has_urgent else "normal"
            action_needed = "create_case" if domain in {"compliance", "finance"} else "attach_to_case"

        elif has_status and not has_blocker:
            signal_type = "status_update"
            # Distinguish "закрыли/исправили" (low) from "скоро сделаем" (normal)
            done_words = {"сделано", "сделали", "готово", "готов", "исправили", "починили", "устранили", "закрыли", "заработало", "работает"}
            is_done = any(w in normalized_text for w in done_words)
            importance = "low" if is_done else "normal"
            action_needed = "digest_only"

        elif is_media_topic or (not text.strip() and topic_kind == "reporting"):
            signal_type = "photo_report"
            importance = "low"
            action_needed = "digest_only"

        elif has_request:
            signal_type = self._domain_to_signal_type(domain, default="request")
            importance = "high" if has_urgent else "normal"
            action_needed = "suggest_reply" if signal_type == "request" else "attach_to_case"

        elif topic_kind in {"incident", "support"}:
            signal_type = self._domain_to_signal_type(domain, default="incident")
            importance = "normal"
            action_needed = "attach_to_case"

        elif topic_kind in {"compliance", "finance"}:
            signal_type = topic_kind
            importance = "normal"
            action_needed = "attach_to_case"

        elif domain:
            signal_type = self._domain_to_signal_type(domain)
            importance = "normal"
            action_needed = "digest_only"

        # Upgrade importance for urgent signals regardless of type
        if has_urgent and signal_type != "chat/noise":
            importance = self._raise_importance(importance, "high")
            if action_needed in {"ignore", "digest_only", "suggest_reply"}:
                action_needed = "attach_to_case"

        if domain:
            tags.append(domain)
            topic_label = self._domain_to_topic_label(domain, topic_label)

        # "не можем работать" = escalate regardless of other signals
        if "не можем работать" in normalized_text or "тяжело работать" in normalized_text:
            importance = self._raise_importance(importance, "high")
            if action_needed in {"ignore", "digest_only", "suggest_reply"}:
                action_needed = "attach_to_case"

        summary = self._build_summary(text, signal_type=signal_type, topic_label=topic_label, domain=domain)
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
            "confidence": self._calc_fallback_confidence(signal_type, domain, has_blocker, has_urgent),
        }

    def _merge_with_fallback(self, parsed: dict, fallback: dict) -> dict:
        result = dict(parsed)
        parsed_confidence = float(parsed.get("confidence") or 0.0)
        fallback_confidence = float(fallback.get("confidence") or 0.0)
        overridden = False

        # Override LLM signal_type only when it's vague AND fallback is more specific
        if parsed.get("signal_type") in {"request", "status_update"} and fallback.get("signal_type") not in {"request", "status_update"}:
            if parsed_confidence < 0.65 or self._is_more_urgent(fallback, parsed):
                result["signal_type"] = fallback["signal_type"]
                overridden = True

        # Only override importance/action if fallback is significantly more urgent
        if self._is_more_urgent(fallback, result) and fallback_confidence >= parsed_confidence * 0.8:
            result["importance"] = fallback["importance"]
            result["action_needed"] = fallback["action_needed"]
            result["recommended_action"] = fallback["recommended_action"]
            overridden = True

        for field in ("summary", "topic_label", "case_key"):
            current_value = result.get(field)
            fallback_value = fallback.get(field)
            if fallback_value and (not current_value or current_value in {"request", "Операционный поток"}):
                result[field] = fallback_value

        if not result.get("recommended_action"):
            result["recommended_action"] = fallback.get("recommended_action")

        # Merge entities: fallback may extract store/issues that LLM missed
        merged_entities = dict(fallback.get("entities") or {})
        merged_entities.update({k: v for k, v in (result.get("entities") or {}).items() if v})
        result["entities"] = merged_entities

        merged_tags = list(dict.fromkeys([*(result.get("tags") or []), *(fallback.get("tags") or [])]))
        result["tags"] = merged_tags

        base_confidence = max(parsed_confidence, fallback_confidence)
        result["confidence"] = round(base_confidence * 0.92, 3) if overridden else round(base_confidence, 3)
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
        if topic_kind in {"compliance", "finance", "inventory", "incident"}:
            return topic_kind
        if topic_kind == "logistics":
            return "delivery"
        if topic_kind in {"support"}:
            return "incident"
        if topic_kind == "reporting":
            return "photo_report"
        if topic_kind == "hr":
            return "hr"
        return None

    @staticmethod
    def _domain_to_signal_type(domain: str | None, default: str = "problem") -> str:
        mapping = {
            "compliance": "compliance",
            "delivery": "delivery",
            "finance": "finance",
            "inventory": "inventory",
            "incident": "incident",
            "news": "news",
            "hr": "hr",
            "photo_report": "photo_report",
            "problem": "problem",
        }
        return mapping.get(domain or "", default)

    @staticmethod
    def _domain_to_topic_label(domain: str, fallback: str) -> str:
        return {
            "compliance": "ЕГАИС и маркировка",
            "finance": "Финансы и касса",
            "delivery": "Доставка и поставки",
            "inventory": "Товар и остатки",
            "photo_report": "Фотоотчет",
            "incident": "Технический инцидент",
            "problem": "Операционная проблема",
            "news": "Объявление",
            "hr": "Кадровый вопрос",
        }.get(domain, fallback)

    _SIGNAL_TYPE_PREFIXES: dict[str, str] = {
        "problem": "Проблема: ",
        "incident": "Инцидент: ",
        "compliance": "ЕГАИС/маркировка: ",
        "finance": "Финансы: ",
        "delivery": "Доставка: ",
        "escalation": "Эскалация: ",
        "inventory": "Остатки: ",
        "hr": "Кадры: ",
    }

    @classmethod
    def _build_summary(cls, text: str, *, signal_type: str, topic_label: str, domain: str | None = None) -> str:
        clean = " ".join(text.split())
        if signal_type == "chat/noise":
            return "Сообщение без действия"
        if signal_type == "photo_report":
            return f"Фотоотчёт: {topic_label}"
        if signal_type == "news":
            first = re.split(r"(?<=[.!?\n])", clean)[0].strip()
            return (first[:90] + "…") if len(first) > 91 else (first or topic_label)
        if signal_type == "status_update":
            first = re.split(r"(?<=[.!?])\s+", clean)[0].strip()
            result = (first[:88] + "…") if len(first) > 89 else first
            return result or f"Статус: {topic_label}"
        # Operational signals: use first meaningful sentence
        first_sentence = re.split(r"(?<=[.!?])\s+", clean)[0].strip() if clean else topic_label
        if len(first_sentence) > 90:
            first_sentence = first_sentence[:89].rstrip() + "…"
        if len(first_sentence.split()) <= 2:
            prefix = cls._SIGNAL_TYPE_PREFIXES.get(signal_type, "")
            return f"{prefix}{topic_label}" if prefix else topic_label
        prefix = cls._SIGNAL_TYPE_PREFIXES.get(signal_type, "")
        if prefix and not first_sentence.lower().startswith(prefix.lower().rstrip(": ")):
            return f"{prefix}{first_sentence}"
        return first_sentence or topic_label

    @staticmethod
    def _build_recommendation(*, signal_type: str, action_needed: str, topic_label: str, importance: str) -> str:
        if action_needed == "create_case":
            if importance == "critical":
                return f"Срочно открыть ситуацию: {topic_label}"
            if signal_type in {"compliance", "finance"}:
                return f"Открыть кейс и назначить ответственного: {topic_label}"
            return f"Открыть ситуацию по теме: {topic_label}"
        if action_needed == "attach_to_case":
            if signal_type == "delivery":
                return f"Добавить к разбору поставки: {topic_label}"
            if signal_type == "inventory":
                return f"Проверить остатки и привязать к кейсу: {topic_label}"
            return f"Добавить в разбор по теме: {topic_label}"
        if action_needed == "suggest_escalation":
            return f"Эскалировать руководителю: {topic_label}"
        if action_needed == "suggest_reply":
            if signal_type in {"compliance", "finance"}:
                return f"Запросить документы и детали: {topic_label}"
            if signal_type == "delivery":
                return "Уточнить статус доставки и адрес"
            if signal_type == "inventory":
                return "Уточнить код товара и точку"
            return "Подготовить ответ и уточнить детали"
        if action_needed == "route_to_topic":
            return f"Перенаправить в тематический топик: {topic_label}"
        if signal_type == "chat/noise":
            return "Не требует действия"
        if signal_type == "photo_report":
            return "Добавить в фотодайджест"
        if signal_type == "news":
            return "Распространить по команде"
        if signal_type == "status_update":
            return "Отметить как статусное обновление"
        if importance == "critical":
            return f"Требует немедленного внимания: {topic_label}"
        if importance == "high":
            return f"Проверить вручную: {topic_label}"
        return "Оставить в сводке"

    @staticmethod
    def _build_case_key(*, domain: str | None, topic_label: str, entities: dict) -> str:
        base = domain or "operations"
        store = re.sub(r"\s+", "-", str(entities.get("store") or "all").lower().strip())
        label = re.sub(r"[^a-z0-9а-я]+", "-", topic_label.lower()).strip("-")
        return f"{base}:{store}:{label[:40]}"

    @staticmethod
    def _extract_entities(text: str, *, normalized_text: str, domain: str | None) -> dict:
        entities: dict = {}

        # 1. Store name at start of message (highest confidence)
        store_match = re.match(r"^\s*([А-ЯA-Z][\w-]{2,}(?:\s+[А-ЯA-Z][\w-]{2,}){0,2})[\s,:.-]", text)
        if store_match:
            candidate = store_match.group(1).strip()
            if candidate.lower() not in NON_STORE_WORDS:
                entities["store"] = candidate

        # 2. Explicit store mention in text
        if "store" not in entities:
            mid_match = re.search(
                r"(?:магазин|точка|объект|филиал|адрес|ТЦ|тц)\s+[«\"']?([А-ЯA-Za-zа-яёЁ][\w\s-]{2,20})[»\"']?",
                text,
                re.IGNORECASE,
            )
            if mid_match:
                entities["store"] = mid_match.group(1).strip()

        # 3. Number-coded store
        if "store" not in entities:
            num_match = re.search(r"(?:магазин|точка|объект|филиал)\s*[№#]?\s*(\d{1,4})\b", text, re.IGNORECASE)
            if num_match:
                entities["store"] = f"№{num_match.group(1)}"

        matched_issues = [m for m in (*BLOCKER_MARKERS, *PROBLEM_IMPACT_MARKERS) if m in normalized_text]
        if matched_issues:
            entities["issue"] = matched_issues[:3]
        if domain:
            entities["domain"] = domain

        # Extract deadline hints
        deadline_match = re.search(r"(к\s+\d+[.:]\d+|до\s+\d+[.:]\d+|к\s+(?:утру|вечеру|обеду)|завтра|сегодня)", normalized_text)
        if deadline_match:
            entities["deadline_hint"] = deadline_match.group(1)

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
        return target if target_rank > current_rank else (current or target)

    @staticmethod
    def _calc_fallback_confidence(signal_type: str, domain: str | None, has_blocker: bool, has_urgent: bool) -> float:
        if signal_type == "chat/noise":
            return 0.88
        if signal_type in {"compliance", "finance", "delivery"} and domain:
            return 0.82
        if has_blocker or has_urgent:
            return 0.78
        if signal_type in {"status_update", "photo_report", "news"}:
            return 0.80
        if signal_type in {"incident", "escalation"}:
            return 0.75
        return 0.62
