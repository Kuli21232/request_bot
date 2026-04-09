import json
import logging

import aiohttp

from bot.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self) -> None:
        self.enabled = settings.OLLAMA_ENABLED
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL

    async def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.4,
        timeout: int = 60,
    ) -> str | None:
        if not self.enabled:
            return None

        payload = await self._generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            timeout=timeout,
        )
        if payload is None:
            return None
        return payload.strip() or None

    async def generate_json(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        timeout: int = 60,
    ) -> dict | None:
        if not self.enabled:
            return None

        payload = await self._generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            timeout=timeout,
            response_format="json",
        )
        if payload is None:
            return None

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON: %s", exc)
            return None

    async def _generate(
        self,
        *,
        prompt: str,
        system: str | None,
        temperature: float,
        timeout: int,
        response_format: str | None = None,
    ) -> str | None:
        try:
            body = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                },
            }
            if system:
                body["system"] = system
            if response_format == "json":
                body["format"] = "json"

            async with aiohttp.ClientSession() as client:
                async with client.post(
                    f"{self.base_url}/api/generate",
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("LLM returned status %s", resp.status)
                        return None
                    data = await resp.json()
                    return data.get("response", "")
        except Exception as exc:
            logger.warning("LLM unavailable: %s", exc)
            return None
