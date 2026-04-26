"""xAI Grok Text-to-Speech: POST /v1/tts -> MP3 bytes -> WAV via ffmpeg."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.models.script import TTSResult
from manim_video_gen.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_XAI_TTS_URL = "https://api.x.ai/v1/tts"
_MAX_ATTEMPTS = 8
_BASE_WAIT_S = 2.0
_MAX_WAIT_S = 60.0


def _ffprobe_duration_seconds(path: Path) -> float:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        meta = json.loads(completed.stdout)
        return float(meta["format"]["duration"])
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        KeyError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        logger.warning("ffprobe failed, using fallback duration: %s", exc)
        return 1.0


def _ffmpeg_convert_to_wav(src: Path, dst: Path) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), str(dst)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise TTSError(
            "ffmpeg is required to convert xAI TTS MP3 to WAV.",
            stage="tts",
            detail=str(exc),
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise TTSError(
            "ffmpeg failed while converting xAI TTS audio",
            stage="tts",
            detail=(exc.stderr or "")[:500],
        ) from exc


def _build_payload(settings: Settings, text: str) -> dict[str, Any]:
    voice = (settings.xai_tts_voice_id or "Ara").strip() or "Ara"
    lang = (settings.xai_tts_language or "ko").strip() or "ko"
    return {
        "text": text,
        "voice_id": voice,
        "output_format": {
            "codec": "mp3",
            "sample_rate": 44100,
            "bit_rate": 128000,
        },
        "language": lang,
    }


class GrokTTS(TTSProvider):
    """xAI TTS API (Grok) -> WAV file + duration."""

    def __init__(self, settings: Settings) -> None:
        api_key = (settings.xai_api_key or "").strip()
        if not api_key:
            raise TTSError(
                "Grok TTS requires XAI_API_KEY (or MANIM_VIDEO_GEN_XAI_API_KEY)",
                stage="tts",
            )
        self._settings = settings
        self._auth_header = f"Bearer {api_key}"

    async def _post_audio(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "User-Agent": "manim-video-gen",
        }
        timeout = httpx.Timeout(self._settings.tts_timeout_seconds)
        last_response: httpx.Response | None = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(_MAX_ATTEMPTS):
                try:
                    response = await client.post(
                        _XAI_TTS_URL,
                        headers=headers,
                        json=payload,
                    )
                except httpx.HTTPError as exc:
                    raise TTSError(
                        f"xAI TTS request failed: {exc}",
                        stage="tts",
                        detail=str(exc)[:800],
                    ) from exc

                last_response = response
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt >= _MAX_ATTEMPTS - 1:
                        break
                    wait = min(
                        _MAX_WAIT_S,
                        _BASE_WAIT_S * (2**attempt),
                    )
                    logger.warning(
                        "xAI TTS HTTP %s, waiting %.1fs then retry %s/%s",
                        response.status_code,
                        wait,
                        attempt + 2,
                        _MAX_ATTEMPTS,
                    )
                    await asyncio.sleep(wait)
                    continue
                return response

        if last_response is not None:
            raise TTSError(
                f"xAI TTS HTTP {last_response.status_code}",
                stage="tts",
                detail=(last_response.text or "")[:800],
            )
        raise TTSError("xAI TTS request failed with no response", stage="tts")

    async def synthesize(self, text: str, *, output_path: Path) -> TTSResult:
        if not text.strip():
            raise TTSError("TTS text is empty", stage="tts")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _build_payload(self._settings, text)
        response = await self._post_audio(payload)

        if response.status_code >= 400:
            raise TTSError(
                f"xAI TTS HTTP {response.status_code}",
                stage="tts",
                detail=(response.text or "")[:800],
            )

        mp3_bytes = response.content
        if not mp3_bytes:
            raise TTSError("xAI TTS returned empty audio body", stage="tts")

        mp3_path = output_path.with_suffix(".mp3")
        mp3_path.write_bytes(mp3_bytes)
        try:
            _ffmpeg_convert_to_wav(mp3_path, output_path)
            # Length of the merged audio file (WAV), not MP3 — matches Manim mux.
            duration = _ffprobe_duration_seconds(output_path)
        finally:
            mp3_path.unlink(missing_ok=True)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=[],
        )
