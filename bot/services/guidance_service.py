import json
import logging

import aiohttp

from bot.config import settings
from bot.database.repositories.knowledge_repo import KnowledgeRepository

logger = logging.getLogger(__name__)


class GuidanceService:
    def __init__(self, repo: KnowledgeRepository):
        self.repo = repo
        self.enabled = settings.OLLAMA_ENABLED
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def answer(self, question: str, *, audience: str = "all") -> dict:
        articles = await self.repo.list_articles(published_only=True, search=question)
        scoped = [article for article in articles if article.audience in ("all", audience, "agent")]
        top_articles = scoped[:4]
        if not top_articles:
            return {
                "answer": "Пока не нашел готовой инструкции по этому вопросу. Лучше уточнить формулировку или добавить статью в базу знаний.",
                "sources": [],
            }

        if self.enabled:
            answer = await self._generate_with_ai(question, top_articles)
            if answer:
                return {
                    "answer": answer,
                    "sources": [self._serialize_source(article) for article in top_articles],
                }

        bullets = "\n".join(
            f"• {article.title}: {(article.summary or article.body)[:220]}"
            for article in top_articles
        )
        return {
            "answer": f"Нашел подходящие инструкции:\n{bullets}",
            "sources": [self._serialize_source(article) for article in top_articles],
        }

    async def _generate_with_ai(self, question: str, articles: list) -> str | None:
        context = "\n\n".join(
            f"[{article.title}]\n{article.summary or ''}\n{article.body[:1600]}"
            for article in articles
        )
        prompt = (
            "Ты помощник для сотрудников BeerShop. Ответь коротко и практично на вопрос пользователя, "
            "используя только контекст базы знаний. Если данных недостаточно, честно скажи об этом.\n\n"
            f"Контекст:\n{context}\n\n"
            f"Вопрос: {question}\n\n"
            "Верни JSON вида {\"answer\": \"...\"}"
        )
        try:
            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                    timeout=aiohttp.ClientTimeout(total=40),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    payload = json.loads(data.get("response", "{}"))
                    return payload.get("answer")
        except Exception as exc:
            logger.warning("Guidance AI unavailable: %s", exc)
            return None

    @staticmethod
    def _serialize_source(article) -> dict:
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
        }
