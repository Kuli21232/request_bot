"""AI-классификация через локальный Ollama (бесплатно)."""
import json
import logging
import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = """Проанализируй текст заявки и верни JSON со следующими полями:
- subject: краткая тема (до 10 слов)
- category: категория (IT, HR, Финансы, Документы, Оборудование, Другое)
- sentiment: тональность (neutral, frustrated, urgent, positive)
- priority_suggestion: предложение по приоритету (low, normal, high, critical)

Верни ТОЛЬКО JSON, без пояснений.

Заявка:
"""


class AIClassifier:
    def __init__(self):
        self.enabled = settings.OLLAMA_ENABLED
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def classify(self, text: str) -> dict | None:
        if not self.enabled or not text:
            return None

        prompt = CLASSIFY_PROMPT + text[:2000]

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
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Ollama вернул статус %s", resp.status)
                        return None
                    data = await resp.json()
                    raw = data.get("response", "")
                    return json.loads(raw)
        except (aiohttp.ClientError, json.JSONDecodeError, Exception) as e:
            logger.warning("AI-классификация недоступна: %s", e)
            return None
