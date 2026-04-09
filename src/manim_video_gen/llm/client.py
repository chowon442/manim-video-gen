"""OpenRouter chat client (OpenAI-compatible HTTP API via httpx)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from manim_video_gen.config import Settings

logger = logging.getLogger(__name__)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

T = TypeVar("T", bound=BaseModel)


def extract_json_from_text(text: str) -> Any:
    """Extract first JSON object or array from model output."""
    text = text.strip()
    # Strip markdown fences
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start_obj = text.find("{")
    start_arr = text.find("[")
    if start_obj == -1 and start_arr == -1:
        raise ValueError("No JSON object or array found in model output")

    if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        start = start_arr
        end = text.rfind("]")
        if end == -1:
            raise ValueError("Unterminated JSON array in model output")
        return json.loads(text[start : end + 1])

    start = start_obj
    end = text.rfind("}")
    if end == -1:
        raise ValueError("Unterminated JSON object in model output")
    return json.loads(text[start : end + 1])


class OpenRouterClient:
    """Minimal async client for OpenRouter chat completions.

    Use as an async context manager to reuse a single HTTP session across
    multiple LLM calls within one pipeline run:

        async with OpenRouterClient(settings) as client:
            result = await client.complete_text(...)
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "OpenRouterClient":
        timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
        self._client = httpx.AsyncClient(timeout=timeout)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def complete_text(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        self._settings.require_openrouter()
        headers = {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if self._client is not None:
            response = await self._client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("OpenRouter error: %s", response.text[:800])
                raise exc
            data = response.json()
        else:
            timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as tmp_client:
                response = await tmp_client.post(OPENROUTER_CHAT_URL, headers=headers, json=payload)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    logger.error("OpenRouter error: %s", response.text[:800])
                    raise exc
                data = response.json()

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response: {data!r}") from exc

    async def complete_json_model(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        temperature: float = 0.2,
    ) -> T:
        raw = await self.complete_text(
            model=model, messages=messages, temperature=temperature
        )
        parsed = extract_json_from_text(raw)
        return response_model.model_validate(parsed)
