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
        lines = [f"Персональная сводка для {user.first_name}:"]
        if profile.get("ai_summary"):
            lines.append(profile["ai_summary"])

        assigned_cases = profile.get("assigned_cases") or []
        if assigned_cases:
            lines.append("Открытые ответственности:")
            for index, flow_case in enumerate(assigned_cases[:5], start=1):
                lines.append(
                    f"{index}. {flow_case['title']} — приоритет {flow_case['priority']}, "
                    f"топик {flow_case.get('primary_topic_title') or 'без топика'}."
                )
        else:
            lines.append("Открытых назначенных ситуаций сейчас нет.")

        recommendations = profile.get("ai_recommendations") or []
        if recommendations:
            lines.append("Рекомендации:")
            for item in recommendations[:4]:
                lines.append(f"• {item}")

        topic_groups = profile.get("topic_groups") or []
        if topic_groups:
            lines.append("Основные темы пользователя:")
            for topic in topic_groups[:4]:
                lines.append(
                    f"• {topic['topic_title']}: сообщений {topic['signal_count']}, "
                    f"внимание {topic['requires_attention_count']}."
                )
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

        lines = [f"Что сделать сейчас {scope}:"]
        for index, item in enumerate(action_board[:5], start=1):
            details = []
            if item.get("critical_case_count"):
                details.append(f"критичных ситуаций: {item['critical_case_count']}")
            if item.get("attention_count"):
                details.append(f"сообщений с вниманием: {item['attention_count']}")
            if item.get("follow_up_needed"):
                details.append("нужен follow-up")
            if item.get("open_case_count"):
                details.append(f"открытых ситуаций: {item['open_case_count']}")
            lines.append(
                f"{index}. {item['topic_title']} ({item.get('group_title') or 'группа'}) — "
                f"{AssistantService._action_label(item.get('recommended_action'))}. "
                f"{item.get('summary') or 'Тема требует разбора.'}"
            )
            if details:
                lines.append("   " + ", ".join(details))
        return "\n".join(lines)

    @staticmethod
    def _build_topic_list_payload(group_match, sections: list[dict]) -> str:
        if not sections:
            if group_match is not None:
                return f"В группе «{group_match.title}» пока нет топиков с собранным контекстом."
            return "Пока не вижу топиков с собранным контекстом."

        scope = f"в группе «{group_match.title}»" if group_match is not None else "по всем группам"
        lines = [f"Топики {scope}:"]
        for index, section in enumerate(sections[:8], start=1):
            lines.append(
                f"{index}. {section['topic_title']} — приоритет {section['priority']}, "
                f"внимание {section['stats'].get('attention_count', 0)}, "
                f"ситуации {section['stats'].get('open_case_count', 0)}."
            )
        return "\n".join(lines)

    @staticmethod
    def _build_topic_summary_payload(topic_sections: list[dict], group_match) -> str:
        if not topic_sections:
            scope = f"в группе «{group_match.title}»" if group_match is not None else ""
            return f"Не нашел подходящий топик {scope}, чтобы собрать сводку."

        primary = topic_sections[0]
        lines = [
            f"Сводка по теме «{primary['topic_title']}»"
            + (f" в группе «{primary['group_title']}»:" if primary.get("group_title") else ":"),
            primary.get("automation", {}).get("summary")
            or primary.get("profile_summary")
            or "По теме уже собран рабочий контекст.",
        ]
        lines.append(
            f"Сигналов: {primary['stats'].get('signal_count', 0)}, "
            f"требуют внимания: {primary['stats'].get('attention_count', 0)}, "
            f"активных ситуаций: {primary['stats'].get('open_case_count', 0)}."
        )
        if primary.get("cases"):
            case_titles = ", ".join(case["title"] for case in primary["cases"][:3])
            lines.append(f"Связанные ситуации: {case_titles}.")
        if primary.get("signals"):
            signal_summaries = "; ".join(
                (signal.summary or signal.body[:80]).strip()
                for signal in primary["signals"][:3]
            )
            if signal_summaries:
                lines.append(f"Последние сигналы: {signal_summaries}.")
        if len(topic_sections) > 1:
            related = ", ".join(section["topic_title"] for section in topic_sections[1:3])
            lines.append(f"Рядом по смыслу еще темы: {related}.")
        return "\n".join(lines)

    @staticmethod
    def _build_group_summary_payload(group_title: str, digest: dict | None, sections: list[dict], action_board: list[dict]) -> str:
        if digest is None:
            if not sections:
                return f"По группе «{group_title}» пока мало данных для сводки."
            top_topics = ", ".join(section["topic_title"] for section in sections[:4])
            return f"По группе «{group_title}» уже видны темы: {top_topics}, но полной сводки пока нет."

        lines = [
            f"Сводка по группе «{group_title}»:",
            digest.get("recommended_focus") or "Группа под контролем.",
            f"Сигналов: {digest.get('signal_count', 0)}, "
            f"требуют внимания: {digest.get('attention_count', 0)}, "
            f"активных ситуаций: {digest.get('open_case_count', 0)}, "
            f"критичных: {digest.get('critical_case_count', 0)}.",
        ]
        if digest.get("top_topics"):
            lines.append(
                "Главные темы: "
                + "; ".join(
                    f"{topic['topic_title']} ({AssistantService._action_label(topic.get('recommended_action'))})"
                    for topic in digest["top_topics"][:4]
                )
                + "."
            )
        if action_board:
            lines.append(
                "Что сделать сейчас: "
                + "; ".join(item["topic_title"] for item in action_board[:3])
                + "."
            )
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

        lines = ["Общая сводка по потоку:"]
        if action_board:
            lines.append(
                "Сейчас в приоритете: "
                + "; ".join(
                    f"{item['topic_title']} ({item.get('group_title') or 'группа'})"
                    for item in action_board[:4]
                )
                + "."
            )
        if group_digests:
            lines.append(
                "По группам: "
                + "; ".join(
                    f"{item['group_title']} — внимание {item.get('attention_count', 0)}, критичных {item.get('critical_case_count', 0)}"
                    for item in group_digests[:3]
                )
                + "."
            )
        if sections:
            lines.append(
                "Главные темы: " + "; ".join(section["topic_title"] for section in sections[:5]) + "."
            )
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
            "Ответь по-русски в 4-8 коротких строках. "
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
