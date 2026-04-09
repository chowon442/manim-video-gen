"""Replicate qwen/qwen3-tts: WAV URL output, downloaded to disk."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx
import replicate

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.models.script import TTSResult
from manim_video_gen.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_MODEL_ID = "qwen/qwen3-tts"


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


def _output_to_url(output: Any) -> str:
    """Normalize Replicate run() return value to an HTTP(S) URL string."""
    if isinstance(output, str) and output.startswith(("http://", "https://")):
        return output
    url = getattr(output, "url", None)
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        return url
    raise TTSError(
        "Replicate qwen3-tts returned an unexpected output (expected URL or object with .url)",
        stage="tts",
        detail=repr(type(output)),
    )


def _build_input(settings: Settings, text: str) -> dict[str, Any]:
    mode = settings.replicate_tts_mode
    payload: dict[str, Any] = {
        "text": text,
        "mode": mode,
        "language": (settings.replicate_tts_language or "auto").strip() or "auto",
    }

    if mode == "custom_voice":
        payload["speaker"] = (settings.replicate_tts_speaker or "Aiden").strip() or "Aiden"
    elif mode == "voice_clone":
        ref_audio = (settings.replicate_tts_reference_audio or "").strip()
        if not ref_audio:
            raise TTSError(
                "voice_clone mode requires MANIM_VIDEO_GEN_REPLICATE_TTS_REF_AUDIO (URL)",
                stage="tts",
            )
        payload["reference_audio"] = ref_audio
        ref_text = (settings.replicate_tts_reference_text or "").strip()
        if ref_text:
            payload["reference_text"] = ref_text
        spk = (settings.replicate_tts_speaker or "").strip()
        if spk:
            payload["speaker"] = spk
    elif mode == "voice_design":
        desc = (settings.replicate_tts_voice_description or "").strip()
        if not desc:
            raise TTSError(
                "voice_design mode requires MANIM_VIDEO_GEN_REPLICATE_TTS_VOICE_DESC",
                stage="tts",
            )
        payload["voice_description"] = desc

    style = (settings.replicate_tts_style_instruction or "").strip()
    if style:
        payload["style_instruction"] = style

    return payload


class ReplicateTTS(TTSProvider):
    """qwen/qwen3-tts on Replicate -> WAV file + duration."""

    def __init__(self, settings: Settings) -> None:
        token = (settings.replicate_api_token or "").strip()
        if not token:
            raise TTSError(
                "Replicate TTS requires REPLICATE_API_TOKEN",
                stage="tts",
            )
        self._settings = settings
        self._client = replicate.Client(api_token=token)

    def _run_sync(self, input_payload: dict[str, Any]) -> Any:
        return self._client.run(_MODEL_ID, input=input_payload)

    async def synthesize(self, text: str, *, output_path: Path) -> TTSResult:
        if not text.strip():
            raise TTSError("TTS text is empty", stage="tts")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_payload = _build_input(self._settings, text)

        try:
            raw_output = await asyncio.to_thread(self._run_sync, input_payload)
        except Exception as exc:
            logger.exception("Replicate qwen3-tts run failed")
            raise TTSError(
                f"Replicate TTS failed: {exc}",
                stage="tts",
                detail=str(exc)[:800],
            ) from exc

        url = _output_to_url(raw_output)
        timeout = httpx.Timeout(self._settings.tts_timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                wav_bytes = response.content
        except httpx.HTTPError as exc:
            raise TTSError(
                f"Failed to download Replicate audio: {exc}",
                stage="tts",
                detail=str(exc)[:800],
            ) from exc

        if not wav_bytes:
            raise TTSError("Replicate returned empty audio", stage="tts")

        output_path.write_bytes(wav_bytes)
        duration = _ffprobe_duration_seconds(output_path)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=[],
        )
