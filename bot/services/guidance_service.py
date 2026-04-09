import logging

from bot.config import settings
from bot.database.repositories.knowledge_repo import KnowledgeRepository
from bot.services.llm_service import LLMService

logger = logging.getLogger(__name__)

ASSISTANT_SYSTEM_PROMPT = (
    "You are the BeerShop operations assistant. "
    "Answer naturally, clearly, and helpfully. "
    "Use the knowledge context when it exists, but do not quote raw fragments. "
    "If context is weak, still give the best practical answer and clearly state uncertainty. "
    "Always answer in Russian."
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

    async def _generate_with_ai(self, question: str, articles: list, *, mode: str) -> str | None:
        context = "\n\n".join(
            f"[{article.title}]\nSummary: {article.summary or 'none'}\nBody:\n{article.body[:1800]}"
            for article in articles
        )

        if mode == "guide":
            task = (
                "Prepare a short step-by-step instruction. "
                "Structure the answer as: what to do, steps, what to watch out for. "
                "If there is not enough context, still give the best practical guidance."
            )
        else:
            task = (
                "Answer the employee question like a strong workplace assistant. "
                "Be direct, practical, and easy to understand. "
                "If the exact policy is unknown, say that honestly and give the best next step."
            )

        prompt = (
            f"{task}\n\n"
            f"User question:\n{question}\n\n"
            f"Knowledge context:\n{context if context else 'No matching knowledge articles were found.'}\n\n"
            "Respond in Russian. Keep it compact and useful. "
            "Do not mention 'context' or 'sources' in the wording."
        )

        generated = await self.llm.generate_text(
            system=ASSISTANT_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=0.35 if mode == "answer" else 0.45,
            timeout=max(20, settings.OLLAMA_BACKGROUND_TIMEOUT - 2),
            max_tokens=120 if mode == "answer" else 160,
        )
        if generated:
            return generated

        retry_prompt = (
            "Answer in Russian in 2-4 short sentences.\n"
            f"Question: {question}\n"
            "If the exact instruction is unknown, say that directly and suggest the next action."
        )
        return await self.llm.generate_text(
            system="You are a concise operations assistant. Always answer in Russian.",
            prompt=retry_prompt,
            temperature=0.2,
            timeout=settings.OLLAMA_BACKGROUND_TIMEOUT,
            max_tokens=90,
        )

    @staticmethod
    def _serialize_source(article) -> dict:
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
        }
