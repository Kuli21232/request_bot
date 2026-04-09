import logging

from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.services.llm_service import LLMService

logger = logging.getLogger(__name__)

ASSISTANT_SYSTEM_PROMPT = (
    "Ты живой операционный AI-ассистент BeerShop. "
    "Отвечай естественно, по-человечески и полезно. "
    "Не перечисляй сырые куски базы знаний, а сначала подумай и собери нормальный ответ. "
    "Если информации мало, честно скажи об этом и предложи следующий шаг. "
    "Пиши по-русски, короткими абзацами, без канцелярита."
)


class GuidanceService:
    def __init__(self, repo: KnowledgeRepository):
        self.repo = repo
        self.llm = LLMService()

    async def answer(self, question: str, *, audience: str = "all", mode: str = "answer") -> dict:
        articles = await self.repo.list_articles(published_only=True, search=question)
        scoped = [article for article in articles if article.audience in ("all", audience, "agent")]
        top_articles = scoped[:4]

        if self.llm.enabled:
            generated = await self._generate_with_ai(question, top_articles, mode=mode)
            if generated:
                return {
                    "answer": generated,
                    "sources": [self._serialize_source(article) for article in top_articles],
                    "generated": True,
                }

        if not top_articles:
            return {
                "answer": (
                    "Пока не нашел уверенного ответа в базе знаний и AI сейчас недоступен. "
                    "Лучше уточнить вопрос или добавить нужную инструкцию в базу знаний."
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

    async def _generate_with_ai(self, question: str, articles: list, *, mode: str) -> str | None:
        context = "\n\n".join(
            f"[{article.title}]\nКратко: {article.summary or 'без краткого описания'}\nСодержание:\n{article.body[:2200]}"
            for article in articles
        )

        if mode == "guide":
            task = (
                "Собери понятный инструктаж по запросу пользователя. "
                "Если в контексте есть релевантные материалы, преврати их в понятную пошаговую инструкцию. "
                "Если материалов мало, все равно дай лучший практический ответ и отдельно коротко скажи, чего не хватает. "
                "Структура ответа: 1) что делать, 2) шаги, 3) на что обратить внимание."
            )
        else:
            task = (
                "Ответь на вопрос пользователя как сильный рабочий ассистент. "
                "Не копируй статьи дословно, а синтезируй ответ своими словами. "
                "Если контекста мало, честно отметь это, но все равно дай лучший практический ориентир."
            )

        prompt = (
            f"{task}\n\n"
            f"Вопрос пользователя:\n{question}\n\n"
            f"Контекст базы знаний:\n{context if context else 'Контекст не найден.'}\n\n"
            "Сделай ответ живым, понятным и полезным для обычного сотрудника. "
            "Не пиши 'по данным контекста' или 'источники сообщают'. "
            "Если уместно, заверши коротким следующим шагом."
        )

        return await self.llm.generate_text(
            system=ASSISTANT_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.45 if mode == "guide" else 0.35,
            timeout=16,
            max_tokens=220 if mode == "guide" else 180,
        )

    @staticmethod
    def _serialize_source(article) -> dict:
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
        }
