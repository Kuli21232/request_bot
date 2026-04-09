import asyncio
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
        self.fallback_model = settings.OLLAMA_FALLBACK_MODEL

    async def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.4,
        timeout: int = 18,
        max_tokens: int = 180,
    ) -> str | None:
        if not self.enabled:
            return None

        payload = await self._generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            timeout=timeout,
            max_tokens=max_tokens,
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
        timeout: int = 18,
        max_tokens: int = 240,
    ) -> dict | None:
        if not self.enabled:
            return None

        payload = await self._generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            timeout=timeout,
            response_format="json",
            max_tokens=max_tokens,
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
        max_tokens: int = 180,
    ) -> str | None:
        try:
            primary = await asyncio.wait_for(
                self._request_model(
                    model=self.model,
                    prompt=prompt,
                    system=system,
                    temperature=temperature,
                    timeout=timeout,
                    response_format=response_format,
                    max_tokens=max_tokens,
                ),
                timeout=timeout + 2,
            )
        except asyncio.TimeoutError:
            logger.warning("LLM primary request timed out for model %s", self.model)
            primary = None
        if primary:
            return primary

        if self.fallback_model and self.fallback_model != self.model:
            logger.warning("Retrying LLM request with fallback model %s", self.fallback_model)
            try:
                return await asyncio.wait_for(
                    self._request_model(
                        model=self.fallback_model,
                        prompt=prompt,
                        system=system,
                        temperature=temperature,
                        timeout=timeout,
                        response_format=response_format,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout + 2,
                )
            except asyncio.TimeoutError:
                logger.warning("LLM fallback request timed out for model %s", self.fallback_model)
                return None
        return None

    async def _request_model(
        self,
        *,
        model: str,
        prompt: str,
        system: str | None,
        temperature: float,
        timeout: int,
        response_format: str | None,
        max_tokens: int,
    ) -> str | None:
        try:
            body = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "15m",
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
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
                        logger.warning("LLM returned status %s for model %s", resp.status, model)
                        return None
                    data = await resp.json()
                    if data.get("error"):
                        logger.warning("LLM error for model %s: %s", model, data["error"])
                        return None
                    return data.get("response", "")
        except Exception as exc:
            logger.warning("LLM unavailable for model %s: %s", model, exc)
            return None

    async def warmup(self) -> None:
        if not self.enabled:
            return
        try:
            await self.generate_text(
                prompt="Ответь одним словом: готов",
                system="Ты помощник.",
                temperature=0.1,
                timeout=12,
                max_tokens=8,
            )
        except Exception as exc:
            logger.warning("LLM warmup failed: %s", exc)
