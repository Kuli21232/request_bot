from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from bot.config import settings
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.llm_service import LLMService
from bot.services.topic_automation_service import TopicAutomationService
from bot.services.user_profile_ai_service import UserProfileAIService
from models.user import User

ASSISTANT_SYSTEM_PROMPT = (
    "Ты AI-помощник BeerShop по операционному потоку. "
    "Отвечай по-русски. "
    "Говори коротко, по делу и только на основе переданных данных. "
    "Не выдумывай регламенты, роли и факты, которых нет в доказательствах."
)

SUMMARY_MARKERS = (
    "сводк",
    "дайджест",
    "итог",
    "обзор",
    "что происходит",
    "что по",
    "что сейчас",
    "расскажи по",
)

ACTION_MARKERS = (
    "что делать",
    "что сделать",
    "что сейчас делать",
    "приоритет",
    "срочн",
    "критич",
    "на что смотреть",
    "next",
)

TOPIC_LIST_MARKERS = (
    "какие топики",
    "какие темы",
    "какие разделы",
    "покажи топики",
    "покажи темы",
)

PERSONAL_MARKERS = (
    "что мне делать",
    "что делать мне",
    "мои задачи",
    "мои проблемы",
    "за что я отвечаю",
    "что у меня на контроле",
    "что у меня сейчас",
    "моя загрузка",
)

ACTION_LABELS = {
    "digest_only": "в сводку",
    "attach_to_case": "добавить в ситуацию",
    "create_case": "открыть ситуацию",
    "suggest_escalation": "эскалировать",
    "suggest_reply": "подготовить ответ",
    "route_to_topic": "перенаправить в нужный топик",
    "shadow_request": "отдать в работу",
    "review_topic_queue": "разобрать очередь топика",
    "watch_topic": "наблюдать",
    "collect_context": "собрать контекст",
    "follow_up": "сделать follow-up",
}


@dataclass
class AssistantAnswer:
    answer: str
    mode: str
    used_llm: bool = False


class AssistantService:
    def __init__(self, session) -> None:
        self.session = session
        self.topic_repo = TopicRepository(session)
        self.automation = TopicAutomationService()
        self.llm = LLMService()
        self.profile_ai = UserProfileAIService()

    async def answer(
        self,
        query: str,
        *,
        current_chat_id: int | None = None,
        requester_user_id: int | None = None,
    ) -> AssistantAnswer:
        normalized_query = " ".join((query or "").lower().replace("ё", "е").split())

        if requester_user_id and self._is_personal_query(normalized_query):
            payload = await self._build_personal_payload(requester_user_id)
            generated = await self._generate_answer(query, payload, mode="personal_summary")
            return AssistantAnswer(answer=generated or payload, mode="personal_summary", used_llm=bool(generated))

        groups = await self.topic_repo.list_groups_with_topics()
        current_group = None
        if current_chat_id is not None:
            current_group = next((group for group in groups if group.telegram_chat_id == current_chat_id), None)

        group_match = self._match_group(normalized_query, groups) or current_group
        topic_matches = await self.topic_repo.search_relevant_topics(query, limit=6)
        if group_match is not None:
            topic_matches = [topic for topic in topic_matches if topic.group_id == group_match.id] or topic_matches

        sections = await self.automation.build_topic_sections(
            self.session,
            limit_topics=18,
            signals_per_topic=4,
            cases_per_topic=3,
        )
        action_board = await self.automation.build_action_board(self.session, limit=8)
        group_digests = await self.automation.build_group_digests(self.session, limit_groups=8)

        scoped_sections = sections
        scoped_action_board = action_board
        if group_match is not None:
            scoped_sections = [section for section in sections if section["group_id"] == group_match.id] or sections
            scoped_action_board = [item for item in action_board if item["group_id"] == group_match.id] or action_board

        topic_sections = self._pick_matching_sections(topic_matches, scoped_sections)
        intent = self._detect_intent(normalized_query)

        if intent == "next_steps":
            payload = self._build_next_steps_payload(scoped_action_board, group_match)
            generated = await self._generate_answer(query, payload, mode="next_steps")
            return AssistantAnswer(answer=generated or payload, mode="next_steps", used_llm=bool(generated))

        if intent == "topic_list":
            payload = self._build_topic_list_payload(group_match, scoped_sections)
            generated = await self._generate_answer(query, payload, mode="topic_list")
            return AssistantAnswer(answer=generated or payload, mode="topic_list", used_llm=bool(generated))

        if topic_sections:
            payload = self._build_topic_summary_payload(topic_sections[:3], group_match)
            generated = await self._generate_answer(query, payload, mode="topic_summary")
            return AssistantAnswer(answer=generated or payload, mode="topic_summary", used_llm=bool(generated))

        if group_match is not None:
            digest = next((item for item in group_digests if item["group_id"] == group_match.id), None)
            payload = self._build_group_summary_payload(group_match.title, digest, scoped_sections[:4], scoped_action_board[:4])
            generated = await self._generate_answer(query, payload, mode="group_summary")
            return AssistantAnswer(answer=generated or payload, mode="group_summary", used_llm=bool(generated))

        payload = self._build_global_summary_payload(group_digests[:3], action_board[:5], sections[:5])
        generated = await self._generate_answer(query, payload, mode="global_summary")
        return AssistantAnswer(answer=generated or payload, mode="global_summary", used_llm=bool(generated))

    @staticmethod
    def _detect_intent(normalized_query: str) -> str:
        if any(marker in normalized_query for marker in ACTION_MARKERS):
            return "next_steps"
        if any(marker in normalized_query for marker in TOPIC_LIST_MARKERS):
            return "topic_list"
        return "summary"

    @staticmethod
    def _is_personal_query(normalized_query: str) -> bool:
        return any(marker in normalized_query for marker in PERSONAL_MARKERS)

    async def _build_personal_payload(self, requester_user_id: int) -> str:
        result = await self.session.execute(select(User).where(User.id == requester_user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return "Не удалось загрузить профиль пользователя для персональной сводки."

        profile = await self.profile_ai.build_profile_payload(
            self.session,
            target_user=user,
            viewer_user=user,
        )
        lines = [f"<b>👤 Сводка для {user.first_name}</b>"]
        if profile.get("ai_summary"):
            lines.append(profile["ai_summary"])

        assigned_cases = profile.get("assigned_cases") or []
        if assigned_cases:
            lines.append("\n<b>Открытые ответственности:</b>")
            for index, flow_case in enumerate(assigned_cases[:5], start=1):
                topic = flow_case.get("primary_topic_title") or "без топика"
                lines.append(f"{index}. <b>{flow_case['title']}</b> — {topic}")
        else:
            lines.append("\nОткрытых назначенных ситуаций сейчас нет.")

        recommendations = profile.get("ai_recommendations") or []
        if recommendations:
            lines.append("\n<b>Рекомендации:</b>")
            for item in recommendations[:4]:
                lines.append(f"• {item}")

        topic_groups = profile.get("topic_groups") or []
        if topic_groups:
            lines.append("\n<b>Основные темы:</b>")
            for topic in topic_groups[:4]:
                attn = topic.get("requires_attention_count", 0)
                attn_str = f" ⚠ {attn}" if attn else ""
                lines.append(f"• {topic['topic_title']}: <b>{topic['signal_count']}</b> сообщ.{attn_str}")
        return "\n".join(lines)

    @staticmethod
    def _match_group(normalized_query: str, groups: list) -> object | None:
        if not normalized_query:
            return None
        best = None
        best_score = 0
        for group in groups:
            title = " ".join((group.title or "").lower().replace("ё", "е").split())
            if not title:
                continue
            score = 0
            if title in normalized_query:
                score += 10
            title_words = {part for part in title.split() if len(part) >= 3}
            query_words = {part for part in normalized_query.split() if len(part) >= 3}
            score += len(title_words & query_words) * 3
            if score > best_score:
                best = group
                best_score = score
        return best

    @staticmethod
    def _pick_matching_sections(topic_matches: list, sections: list[dict]) -> list[dict]:
        if not topic_matches:
            return []
        section_map = {section["topic_id"]: section for section in sections}
        result: list[dict] = []
        for topic in topic_matches:
            if topic.id in section_map:
                result.append(section_map[topic.id])
        return result

    @staticmethod
    def _build_next_steps_payload(action_board: list[dict], group_match) -> str:
        scope = f"по группе «{group_match.title}»" if group_match is not None else "по всем группам"
        if not action_board:
            return f"Сейчас {scope} нет тем, которые AI поднял как приоритетные. Можно наблюдать поток в штатном режиме."

        lines = [f"<b>Что сделать сейчас {scope}:</b>"]
        for index, item in enumerate(action_board[:5], start=1):
            details = []
            if item.get("critical_case_count"):
                details.append(f"🔴 крит. ситуаций: <b>{item['critical_case_count']}</b>")
            if item.get("attention_count"):
                details.append(f"⚠ внимание: <b>{item['attention_count']}</b>")
            if item.get("follow_up_needed"):
                details.append("↩ нужен follow-up")
            if item.get("open_case_count"):
                details.append(f"📂 ситуации: <b>{item['open_case_count']}</b>")
            action = AssistantService._action_label(item.get('recommended_action'))
            summary = item.get('summary') or 'Тема требует разбора.'
            lines.append(f"\n{index}. <b>{item['topic_title']}</b> — {action}")
            lines.append(f"   {summary}")
            if details:
                lines.append("   " + " · ".join(details))
        return "\n".join(lines)

    @staticmethod
    def _build_topic_list_payload(group_match, sections: list[dict]) -> str:
        if not sections:
            if group_match is not None:
                return f"В группе «{group_match.title}» пока нет топиков с собранным контекстом."
            return "Пока не вижу топиков с собранным контекстом."

        scope = f"в группе «{group_match.title}»" if group_match is not None else "по всем группам"
        lines = [f"<b>Топики {scope}:</b>"]
        for index, section in enumerate(sections[:8], start=1):
            attn = section['stats'].get('attention_count', 0)
            cases = section['stats'].get('open_case_count', 0)
            flags = []
            if attn:
                flags.append(f"⚠ {attn}")
            if cases:
                flags.append(f"📂 {cases}")
            flag_str = "  " + " · ".join(flags) if flags else ""
            lines.append(f"{index}. <b>{section['topic_title']}</b>{flag_str}")
        return "\n".join(lines)

    @staticmethod
    def _build_topic_summary_payload(topic_sections: list[dict], group_match) -> str:
        if not topic_sections:
            scope = f"в группе «{group_match.title}»" if group_match is not None else ""
            return f"Не нашел подходящий топик {scope}, чтобы собрать сводку."

        primary = topic_sections[0]
        group_hint = f" · {primary['group_title']}" if primary.get("group_title") else ""
        lines = [f"<b>📌 {primary['topic_title']}{group_hint}</b>"]

        ai_summary = (primary.get("automation") or {}).get("summary") or primary.get("profile_summary")
        if ai_summary:
            lines.append(ai_summary)

        stats = primary.get("stats", {})
        stat_parts = []
        if stats.get("signal_count"):
            stat_parts.append(f"сигналов: <b>{stats['signal_count']}</b>")
        if stats.get("attention_count"):
            stat_parts.append(f"⚠ внимание: <b>{stats['attention_count']}</b>")
        if stats.get("open_case_count"):
            stat_parts.append(f"📂 ситуации: <b>{stats['open_case_count']}</b>")
        if stat_parts:
            lines.append(" · ".join(stat_parts))

        if primary.get("cases"):
            lines.append("\n<b>Ситуации:</b>")
            for case in primary["cases"][:3]:
                lines.append(f"• {case['title']}")

        if primary.get("signals"):
            lines.append("\n<b>Последние сообщения:</b>")
            for signal in primary["signals"][:4]:
                text = (signal.summary or getattr(signal, "body", "") or "")[:90].strip()
                store = getattr(signal, "store", None)
                prefix = f"{store}: " if store else ""
                lines.append(f"• {prefix}{text}")

        if len(topic_sections) > 1:
            related = ", ".join(f"«{section['topic_title']}»" for section in topic_sections[1:3])
            lines.append(f"\nСм. также: {related}")
        return "\n".join(lines)

    @staticmethod
    def _build_group_summary_payload(group_title: str, digest: dict | None, sections: list[dict], action_board: list[dict]) -> str:
        if digest is None:
            if not sections:
                return f"По группе «{group_title}» пока мало данных для сводки."
            top_topics = ", ".join(f"«{section['topic_title']}»" for section in sections[:4])
            return f"По группе «{group_title}» уже видны темы: {top_topics}, но полной сводки пока нет."

        lines = [f"<b>📊 Сводка по группе «{group_title}»</b>"]

        focus = digest.get("recommended_focus")
        if focus:
            lines.append(focus)

        stat_parts = []
        if digest.get("signal_count"):
            stat_parts.append(f"сигналов: <b>{digest['signal_count']}</b>")
        if digest.get("attention_count"):
            stat_parts.append(f"⚠ внимание: <b>{digest['attention_count']}</b>")
        if digest.get("open_case_count"):
            stat_parts.append(f"📂 ситуации: <b>{digest['open_case_count']}</b>")
        if digest.get("critical_case_count"):
            stat_parts.append(f"🔴 крит.: <b>{digest['critical_case_count']}</b>")
        if stat_parts:
            lines.append(" · ".join(stat_parts))

        if digest.get("top_topics"):
            lines.append("\n<b>Главные темы:</b>")
            for topic in digest["top_topics"][:5]:
                action = AssistantService._action_label(topic.get("recommended_action"))
                lines.append(f"• <b>{topic['topic_title']}</b> — {action}")

        if action_board:
            lines.append("\n<b>Требуют действия:</b>")
            for item in action_board[:3]:
                lines.append(f"• {item['topic_title']}")
        return "\n".join(lines)

    @staticmethod
    def _action_label(action: str | None) -> str:
        if not action:
            return "наблюдать"
        return ACTION_LABELS.get(action, action)

    @staticmethod
    def _build_global_summary_payload(group_digests: list[dict], action_board: list[dict], sections: list[dict]) -> str:
        if not group_digests and not action_board and not sections:
            return "Пока мало данных, чтобы собрать общую сводку по потоку."

        lines = ["<b>🗂 Общая сводка по потоку</b>"]

        if action_board:
            lines.append("\n<b>Сейчас в приоритете:</b>")
            for item in action_board[:4]:
                group_hint = f" · {item['group_title']}" if item.get("group_title") else ""
                flags = []
                if item.get("critical_case_count"):
                    flags.append(f"🔴 {item['critical_case_count']}")
                if item.get("attention_count"):
                    flags.append(f"⚠ {item['attention_count']}")
                flag_str = "  " + " ".join(flags) if flags else ""
                lines.append(f"• <b>{item['topic_title']}</b>{group_hint}{flag_str}")

        if group_digests:
            lines.append("\n<b>По группам:</b>")
            for item in group_digests[:3]:
                parts = []
                if item.get("attention_count"):
                    parts.append(f"внимание: {item['attention_count']}")
                if item.get("critical_case_count"):
                    parts.append(f"крит.: {item['critical_case_count']}")
                detail = ", ".join(parts) if parts else "штатный режим"
                lines.append(f"• <b>{item['group_title']}</b> — {detail}")

        if sections and not action_board:
            lines.append("\n<b>Активные темы:</b>")
            for section in sections[:5]:
                lines.append(f"• {section['topic_title']}")
        return "\n".join(lines)

    async def _generate_answer(self, query: str, payload: str, *, mode: str) -> str | None:
        if not self.llm.enabled:
            return None

        task = {
            "personal_summary": "Сделай персональную рабочую сводку и короткий план действий для сотрудника.",
            "next_steps": "Преобразуй это в практичный ответ менеджеру с коротким планом действий.",
            "topic_list": "Преобразуй список топиков в короткий и удобный для чтения ответ.",
            "topic_summary": "Преобразуй факты по топику в короткую рабочую сводку для оператора.",
            "group_summary": "Преобразуй факты по группе в короткую управленческую сводку.",
            "global_summary": "Преобразуй факты по потоку в короткую управленческую сводку.",
        }.get(mode, "Преобразуй факты в короткий практичный ответ.")

        prompt = (
            f"{task}\n\n"
            f"Запрос пользователя:\n{query}\n\n"
            f"Доказательства:\n{payload}\n\n"
            "Ответь по-русски в 4-8 строках. "
            "Используй HTML-форматирование: <b>жирный</b> для ключевых слов и чисел, "
            "• перед каждым пунктом списка. "
            "Не добавляй факты за пределами доказательств."
        )
        generated = await self.llm.generate_text(
            system=ASSISTANT_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.2,
            timeout=max(24, settings.OLLAMA_BACKGROUND_TIMEOUT - 4),
            max_tokens=220,
        )
        if generated:
            return generated

        await self.llm.warmup()
        retry_prompt = (
            f"Запрос:\n{query}\n\n"
            f"Короткие факты:\n{payload[:1400]}\n\n"
            "Ответь по-русски в 3-5 коротких строках. "
            "Используй только эти факты и не додумывай лишнее."
        )
        return await self.llm.generate_text(
            system="Ты краткий и точный AI-помощник BeerShop. Отвечай только по данным.",
            prompt=retry_prompt,
            temperature=0.1,
            timeout=settings.OLLAMA_BACKGROUND_TIMEOUT,
            max_tokens=140,
        )
