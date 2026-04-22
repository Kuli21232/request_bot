import logging

from bot.config import settings
from bot.database.repositories.flow_repo import FlowRepository
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.database.repositories.topic_repo import TopicRepository
from bot.services.llm_service import LLMService

logger = logging.getLogger(__name__)

ASSISTANT_SYSTEM_PROMPT = (
    "You are the BeerShop operations assistant. "
    "Answer naturally, clearly, and helpfully. "
    "Use only the provided knowledge, groups, topics, signals, and cases. "
    "If the exact rule is unknown, say that directly and do not invent procedures or documents. "
    "Always answer in Russian."
)


class GuidanceService:
    def __init__(self, repo: KnowledgeRepository):
        self.repo = repo
        self.llm = LLMService()
        self.topic_repo = TopicRepository(repo.session)
        self.flow_repo = FlowRepository(repo.session)

    async def answer(self, question: str, *, audience: str = "all", mode: str = "answer") -> dict:
        articles = await self.repo.list_articles(published_only=True, search=question)
        scoped = [article for article in articles if article.audience in ("all", audience, "agent")]
        top_articles = scoped[:4]
        topic_matches = await self.topic_repo.search_relevant_topics(question, limit=5)
        topic_evidence = await self._build_topic_evidence(topic_matches)

        topic_first_answer = self._build_topic_first_answer(question, topic_evidence)
        if topic_first_answer is not None:
            return {
                "answer": topic_first_answer,
                "sources": [],
                "generated": False,
            }

        has_context = bool(top_articles) or any(
            item["recent_signals"] for item in topic_evidence
        )
        if self.llm.enabled and has_context:
            generated = await self._generate_with_ai(question, top_articles, topic_evidence, mode=mode)
            if generated:
                return {
                    "answer": generated,
                    "sources": [self._serialize_source(article) for article in top_articles],
                    "generated": True,
                }

        if topic_evidence:
            return {
                "answer": self._build_evidence_fallback(topic_evidence),
                "sources": [],
                "generated": False,
            }

        if not top_articles:
            return {
                "answer": (
                    "Я пока не нашел точной инструкции по этому вопросу. "
                    "Могу подсказать общий порядок действий, если вы уточните тему, "
                    "или можно добавить нужную инструкцию в базу знаний."
                ),
                "sources": [],
                "generated": False,
            }

        bullets = "\n".join(
            f"• {article.title}: {(article.summary or article.body)[:220]}"
            for article in top_articles
        )
        intro = "Нашел подходящие инструкции:" if mode == "guide" else "Нашел подходящие материалы:"
        return {
            "answer": f"{intro}\n{bullets}",
            "sources": [self._serialize_source(article) for article in top_articles],
            "generated": False,
        }

    async def _build_topic_evidence(self, topic_matches: list) -> list[dict]:
        evidence: list[dict] = []
        for topic in topic_matches[:4]:
            signals = await self.flow_repo.list_topic_signal_briefs(topic_id=topic.id, limit=4)
            cases = await self.flow_repo.list_topic_cases(topic_id=topic.id, limit=3)
            evidence.append(
                {
                    "topic_id": topic.id,
                    "topic_title": topic.title,
                    "group_title": topic.group.title if topic.group else "Неизвестная группа",
                    "topic_kind": topic.topic_kind,
                    "profile_summary": (topic.profile.profile_summary if topic.profile else None) or "",
                    "recent_signals": [
                        {
                            "summary": signal.summary or "",
                            "body_excerpt": self._shorten(signal.body, limit=120),
                            "kind": signal.kind,
                            "store": signal.store,
                            "importance": signal.importance,
                            "actionability": signal.actionability,
                        }
                        for signal in signals
                    ],
                    "recent_cases": [
                        {
                            "title": case.title,
                            "status": case.status,
                            "priority": case.priority,
                            "signal_count": case.signal_count,
                        }
                        for case in cases
                    ],
                }
            )
        return evidence

    async def _generate_with_ai(self, question: str, articles: list, topic_evidence: list[dict], *, mode: str) -> str | None:
        context = "\n\n".join(
            f"[{article.title}]\nSummary: {article.summary or 'none'}\nBody:\n{article.body[:1800]}"
            for article in articles
        )
        topic_context = "\n\n".join(self._format_topic_evidence_block(item) for item in topic_evidence)

        if mode == "guide":
            task = (
                "Prepare a short step-by-step instruction. "
                "If the provided data is not enough for an exact instruction, say that directly and suggest the next safe step."
            )
        else:
            task = (
                "Answer the employee question like a strong workplace assistant. "
                "Base the answer only on the provided groups, topics, signals, cases, and knowledge articles."
            )

        prompt = (
            f"{task}\n\n"
            f"User question:\n{question}\n\n"
            f"Topic and group evidence:\n{topic_context if topic_context else 'No clearly matching topics were found.'}\n\n"
            f"Knowledge context:\n{context if context else 'No matching knowledge articles were found.'}\n\n"
            "Respond in Russian. Keep it compact and practical. "
            "Do not invent documents, departments, instructions, or procedures that are not present in the evidence."
        )

        generated = await self.llm.generate_text(
            system=ASSISTANT_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.25 if mode == "answer" else 0.35,
            timeout=max(20, settings.OLLAMA_BACKGROUND_TIMEOUT - 2),
            max_tokens=160 if mode == "answer" else 220,
        )
        if generated:
            return generated

        await self.llm.warmup()

        retry_prompt = (
            f"Question: {question}\n\n"
            f"Topic evidence:\n{topic_context if topic_context else 'No topic evidence.'}\n\n"
            "Answer in Russian in 2-4 short sentences. "
            "If the exact rule is unknown, say that directly and recommend the safest next step."
        )
        return await self.llm.generate_text(
            system="You are a concise operations assistant. Always answer in Russian.",
            prompt=retry_prompt,
            temperature=0.1,
            timeout=settings.OLLAMA_BACKGROUND_TIMEOUT,
            max_tokens=120,
        )

    def _build_topic_first_answer(self, question: str, topic_evidence: list[dict]) -> str | None:
        normalized_question = question.lower().replace("ё", "е")

        system_answer = self._build_system_answer(normalized_question)
        if system_answer is not None:
            return system_answer

        if not topic_evidence:
            return None

        primary = topic_evidence[0]
        visible_topics = [item["topic_title"] for item in topic_evidence[:3]]
        topics_text = ", ".join(f"«{title}»" for title in visible_topics)
        group_text = primary["group_title"]
        signal_examples = self._format_signal_examples(primary["recent_signals"])

        if any(phrase in normalized_question for phrase in ("куда отправ", "куда писать", "в какой топик", "где писать", "куда мне")):
            if len(visible_topics) == 1:
                return (
                    f"В группе «{group_text}» вижу отдельный топик «{primary['topic_title']}». "
                    f"По последним сообщениям там обсуждают: {signal_examples}. "
                    f"Значит такие сообщения лучше отправлять именно туда. "
                    "Если нужен точный формат отчета или шаблон, его надо отдельно зафиксировать в инструкции."
                )
            return (
                f"В группе «{group_text}» по этой теме вижу несколько подходящих топиков: {topics_text}. "
                f"Если нужен базовый маршрут, начните с «{primary['topic_title']}». "
                f"По свежим сообщениям там обсуждают: {signal_examples}. "
                "Для точного регламента лучше закрепить инструкцию в базе знаний."
            )

        if any(phrase in normalized_question for phrase in ("что нужно", "что мне нужно", "какие документы", "что отправлять", "что сдавать")):
            return (
                f"По группе «{group_text}» вижу связанные топики {topics_text}. "
                f"По последним сообщениям там обсуждают: {signal_examples}. "
                f"Это помогает понять, куда писать по теме, но не подтверждает точный список документов или действий. "
                f"Если вопрос именно по работе с темой, начните с «{primary['topic_title']}». "
                "Если нужен формальный регламент, его надо добавить в базу знаний."
            )

        if any(phrase in normalized_question for phrase in ("что по", "что происходит", "какая ситуация", "что сейчас")):
            case_text = self._format_case_examples(primary["recent_cases"])
            return (
                f"По теме «{primary['topic_title']}» в группе «{group_text}» сейчас вижу такие сигналы: {signal_examples}. "
                f"Связанные ситуации: {case_text}. "
                "Если хотите, могу дальше отвечать по этой теме только в рамках найденных топиков и кейсов."
            )

        if any(phrase in normalized_question for phrase in ("какие топики", "какой топик", "есть ли топик", "по каким топикам")):
            return f"По этой теме у вас сейчас вижу такие топики: {topics_text}."

        return None

    @staticmethod
    def _build_system_answer(normalized_question: str) -> str | None:
        if any(
            phrase in normalized_question
            for phrase in (
                "как ты фильтруешь",
                "каким образом ты фильтруешь",
                "как ты сортируешь",
                "как работаешь с топиками",
                "как анализируешь топики",
                "как анализируешь группы",
            )
        ):
            return (
                "Я смотрю на название топика и группы, текст сообщения, вложения, повторяемость темы и историю похожих сигналов. "
                "Сначала определяю, что это за тип сообщения, потом связываю его с подходящим топиком и кейсом. "
                "Если точного правила или подтвержденной инструкции нет, я лучше скажу об этом прямо, чем придумаю ответ."
            )
        return None

    def _build_evidence_fallback(self, topic_evidence: list[dict]) -> str:
        primary = topic_evidence[0]
        return (
            f"По теме ближе всего подходит топик «{primary['topic_title']}» в группе «{primary['group_title']}». "
            f"По последним сообщениям там обсуждают: {self._format_signal_examples(primary['recent_signals'])}. "
            "Если нужен точный регламент действий, его пока нет в базе знаний, поэтому лучше закрепить его отдельно."
        )

    def _format_topic_evidence_block(self, item: dict) -> str:
        signal_text = "; ".join(
            f"{signal['kind']} | {signal['store'] or 'без точки'} | {signal['summary'] or signal['body_excerpt']}"
            for signal in item["recent_signals"][:4]
        ) or "no recent signals"
        case_text = "; ".join(
            f"{case['title']} ({case['status']}, {case['priority']}, signals={case['signal_count']})"
            for case in item["recent_cases"][:3]
        ) or "no recent cases"
        return (
            f"Topic: {item['topic_title']}\n"
            f"Group: {item['group_title']}\n"
            f"Kind: {item['topic_kind']}\n"
            f"Profile: {item['profile_summary'] or 'none'}\n"
            f"Recent signals: {signal_text}\n"
            f"Recent cases: {case_text}"
        )

    @staticmethod
    def _format_signal_examples(signals: list[dict]) -> str:
        if not signals:
            return "свежих сигналов пока мало"
        parts = []
        for signal in signals[:3]:
            text = signal["summary"] or signal["body_excerpt"] or signal["kind"]
            if signal["store"]:
                text = f"{signal['store']}: {text}"
            parts.append(text)
        return "; ".join(parts)

    @staticmethod
    def _format_case_examples(cases: list[dict]) -> str:
        if not cases:
            return "открытых кейсов по этой теме пока не видно"
        return "; ".join(f"{case['title']} ({case['status']}, {case['priority']})" for case in cases[:3])

    @staticmethod
    def _shorten(text: str | None, *, limit: int = 120) -> str:
        if not text:
            return ""
        value = " ".join(text.split())
        if len(value) <= limit:
            return value
        return f"{value[: limit - 1]}…"

    @staticmethod
    def _serialize_source(article) -> dict:
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
        }
