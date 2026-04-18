"""Inworld TTS non-streaming API: base64 MP3 -> WAV via ffmpeg."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Literal

import httpx

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.models.script import TTSResult
from manim_video_gen.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_INWORLD_VOICE_URL = "https://api.inworld.ai/tts/v1/voice"


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
            "ffmpeg is required to convert Inworld TTS MP3 to WAV.",
            stage="tts",
            detail=str(exc),
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise TTSError(
            "ffmpeg failed while converting Inworld audio",
            stage="tts",
            detail=(exc.stderr or "")[:500],
        ) from exc


def _build_payload(
    settings: Settings,
    text: str,
    *,
    speaker_role: Literal["teacher", "student"] = "teacher",
) -> dict[str, Any]:
    voice_id = (settings.inworld_tts_voice_id or "Hyunwoo").strip() or "Hyunwoo"
    if speaker_role == "student" and (settings.inworld_student_tts_voice_id or "").strip():
        voice_id = (settings.inworld_student_tts_voice_id or "").strip()

    payload: dict[str, Any] = {
        "text": text,
        "voiceId": voice_id,
        "modelId": (settings.inworld_tts_model_id or "inworld-tts-1.5-max").strip()
        or "inworld-tts-1.5-max",
        "audioConfig": {
            "speakingRate": float(settings.inworld_tts_speaking_rate),
        },
        "temperature": float(settings.inworld_tts_temperature),
    }
    if settings.inworld_tts_timestamp_type == "WORD":
        payload["timestampType"] = "WORD"
    return payload


class InworldTTS(TTSProvider):
    """Inworld TTS 1.5 (non-streaming) -> WAV file + duration."""

    def __init__(self, settings: Settings) -> None:
        api_key = (settings.inworld_tts_api_key or "").strip()
        if not api_key:
            raise TTSError(
                "Inworld TTS requires INWORLD_TTS_API_KEY",
                stage="tts",
            )
        self._settings = settings
        self._auth_header = f"Basic {api_key}"

    async def synthesize(
        self,
        text: str,
        *,
        output_path: Path,
        speaker_role: Literal["teacher", "student"] = "teacher",
    ) -> TTSResult:
        if not text.strip():
            raise TTSError("TTS text is empty", stage="tts")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _build_payload(self._settings, text, speaker_role=speaker_role)
        headers = {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "User-Agent": "manim-video-gen",
        }
        timeout = httpx.Timeout(self._settings.tts_timeout_seconds)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    _INWORLD_VOICE_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise TTSError(
                f"Inworld TTS request failed: {exc}",
                stage="tts",
                detail=str(exc)[:800],
            ) from exc

        if response.status_code >= 400:
            raise TTSError(
                f"Inworld TTS HTTP {response.status_code}",
                stage="tts",
                detail=(response.text or "")[:800],
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise TTSError(
                "Inworld TTS returned invalid JSON",
                stage="tts",
                detail=str(exc)[:800],
            ) from exc

        b64 = data.get("audioContent")
        if not isinstance(b64, str) or not b64.strip():
            raise TTSError(
                "Inworld TTS response missing audioContent",
                stage="tts",
                detail=str(data)[:500],
            )

        try:
            mp3_bytes = base64.b64decode(b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise TTSError(
                "Inworld TTS audioContent is not valid base64",
                stage="tts",
                detail=str(exc)[:800],
            ) from exc

        if not mp3_bytes:
            raise TTSError("Inworld TTS returned empty audio", stage="tts")

        mp3_path = output_path.with_suffix(".mp3")
        mp3_path.write_bytes(mp3_bytes)
        try:
            duration = _ffprobe_duration_seconds(mp3_path)
            _ffmpeg_convert_to_wav(mp3_path, output_path)
        finally:
            mp3_path.unlink(missing_ok=True)

        return TTSResult(
            audio_path=output_path,
            duration_seconds=duration,
            word_timestamps=[],
        )
