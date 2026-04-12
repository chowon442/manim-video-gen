"""OpenRouter chat client (OpenAI-compatible HTTP API via httpx)."""

from __future__ import annotations

import json
import logging
import re
import asyncio
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import LLMError

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

        max_retries = max(0, int(self._settings.openrouter_retries))

        def _is_provider_body_error(data: dict[str, Any]) -> tuple[bool, int, str]:
            err = data.get("error")
            if not isinstance(err, dict):
                return False, 0, ""
            code = int(err.get("code", 0) or 0)
            msg = str(err.get("message", ""))
            retriable = code in {429, 502, 503, 504, 524}
            return retriable, code, msg

        async def _request_once(client: httpx.AsyncClient) -> dict[str, Any]:
            response = await client.post(
                OPENROUTER_CHAT_URL, headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()

        async def _request_with_retry(client: httpx.AsyncClient) -> dict[str, Any]:
            for attempt in range(max_retries + 1):
                try:
                    data = await _request_once(client)
                    retriable_body, code, msg = _is_provider_body_error(data)
                    if retriable_body:
                        if attempt >= max_retries:
                            raise LLMError(
                                f"OpenRouter provider error {code}",
                                stage="llm",
                                detail=msg[:800],
                            )
                        wait = min(
                            float(self._settings.openrouter_retry_max_seconds),
                            float(self._settings.openrouter_retry_base_seconds)
                            * (2**attempt),
                        )
                        logger.warning(
                            "OpenRouter provider error %s, retry %d/%d after %.2fs: %s",
                            code,
                            attempt + 1,
                            max_retries,
                            wait,
                            msg,
                        )
                        if wait > 0:
                            await asyncio.sleep(wait)
                        continue
                    return data
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code if exc.response is not None else 0
                    retriable = status == 429 or (500 <= status < 600)
                    if not retriable or attempt >= max_retries:
                        txt = (
                            exc.response.text[:800]
                            if exc.response is not None
                            else str(exc)
                        )
                        logger.error("OpenRouter error: %s", txt)
                        raise LLMError(
                            f"OpenRouter HTTP {status}",
                            stage="llm",
                            detail=txt,
                        ) from exc
                    wait = min(
                        float(self._settings.openrouter_retry_max_seconds),
                        float(self._settings.openrouter_retry_base_seconds)
                        * (2**attempt),
                    )
                    logger.warning(
                        "OpenRouter transient HTTP %s, retry %d/%d after %.2fs",
                        status,
                        attempt + 1,
                        max_retries,
                        wait,
                    )
                    if wait > 0:
                        await asyncio.sleep(wait)
                except httpx.HTTPError as exc:
                    if attempt >= max_retries:
                        logger.error(
                            "OpenRouter transport error after retries: %s", exc
                        )
                        raise LLMError(
                            "OpenRouter transport error",
                            stage="llm",
                            detail=str(exc)[:800],
                        ) from exc
                    wait = min(
                        float(self._settings.openrouter_retry_max_seconds),
                        float(self._settings.openrouter_retry_base_seconds)
                        * (2**attempt),
                    )
                    logger.warning(
                        "OpenRouter transport error, retry %d/%d after %.2fs: %s",
                        attempt + 1,
                        max_retries,
                        wait,
                        exc,
                    )
                    if wait > 0:
                        await asyncio.sleep(wait)

            raise LLMError("OpenRouter retry loop exhausted", stage="llm")

        if self._client is not None:
            data = await _request_with_retry(self._client)
        else:
            timeout = httpx.Timeout(self._settings.llm_timeout_seconds)
            async with httpx.AsyncClient(timeout=timeout) as tmp_client:
                data = await _request_with_retry(tmp_client)

        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(
                f"Unexpected OpenRouter response: {data!r}",
                stage="llm",
            ) from exc

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
        try:
            return response_model.model_validate(parsed)
        except ValidationError as exc:
            raise LLMError(
                "LLM JSON did not match schema",
                stage="llm",
                detail=str(exc),
            ) from exc
