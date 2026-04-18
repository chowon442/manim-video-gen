"""Azure Cognitive Services Text-to-Speech (REST) -> WAV via ffmpeg."""

from __future__ import annotations

import html
import logging
import subprocess
from pathlib import Path
from typing import Literal
import httpx

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.models.script import TTSResult
from manim_video_gen.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_AZURE_TTS_URL_TEMPLATE = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


def _ffprobe_duration_seconds(path: Path) -> float:
    import json

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
            "ffmpeg is required to convert Azure TTS audio to WAV.",
            stage="tts",
            detail=str(exc),
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise TTSError(
            "ffmpeg failed while converting Azure audio",
            stage="tts",
            detail=(exc.stderr or "")[:500],
        ) from exc


class AzureSpeechTTS(TTSProvider):
    """Azure Speech REST API (no extra SDK; uses httpx)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        key = (settings.azure_speech_key or "").strip()
        region = (settings.azure_speech_region or "").strip()
        if not key or not region:
            raise TTSError(
                "Azure TTS requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION",
                stage="tts",
            )
        self._key = key
        self._region = region
        self._voice = (settings.azure_tts_voice or "ko-KR-SunHiNeural").strip()

    def _ssml(self, text: str) -> str:
        safe = html.escape(text, quote=True)
        return (
            "<speak version='1.0' xml:lang='ko-KR'>"
            f"<voice xml:lang='ko-KR' name='{html.escape(self._voice, quote=True)}'>"
            f"{safe}</voice></speak>"
        )

    async def synthesize(
        self,
        text: str,
        *,
        output_path: Path,
        speaker_role: Literal["teacher", "student"] = "teacher",
    ) -> TTSResult:
        _ = speaker_role
        if not text.strip():
            raise TTSError("TTS text is empty", stage="tts")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        url = _AZURE_TTS_URL_TEMPLATE.format(region=self._region)
        headers: dict[str, str] = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "manim-video-gen",
        }
        timeout = httpx.Timeout(self._settings.tts_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                content=self._ssml(text),
            )
        if response.status_code >= 400:
            raise TTSError(
                f"Azure Speech HTTP {response.status_code}",
                stage="tts",
                detail=(response.text or "")[:800],
            )

        mp3_path = output_path.with_suffix(".mp3")
        mp3_path.write_bytes(response.content)
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
