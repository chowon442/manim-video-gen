"""ElevenLabs TTS: prefer with-timestamps when available, else standard speech API."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import httpx

from manim_video_gen.config import Settings
from manim_video_gen.models.script import TTSResult
from manim_video_gen.tts.base import TTSProvider

logger = logging.getLogger(__name__)

ELEVEN_BASE = "https://api.elevenlabs.io/v1"

# Fallback when premium /with-timestamps is unavailable (e.g. 402 Payment Required)
_TIMESTAMP_FALLBACK_STATUSES = frozenset({402, 403, 404})


def _parse_elevenlabs_detail(body: str) -> tuple[str | None, str | None]:
    """JSON 오류 본문에서 (code, message) 추출."""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None, None
    detail = data.get("detail")
    if isinstance(detail, dict):
        return detail.get("code"), detail.get("message")
    if isinstance(detail, str):
        return None, detail
    return None, None


def _is_library_voice_free_tier_block(status_code: int, body: str) -> bool:
    """무료 플랜에서 API로 라이브러리 보이스 사용 불가 시(표준 TTS도 동일하게 실패)."""
    if status_code != 402:
        return False
    code, msg = _parse_elevenlabs_detail(body)
    if code == "paid_plan_required":
        return True
    if msg and "library voices" in msg.lower():
        return True
    return False


def _runtime_error_for_elevenlabs(response: httpx.Response) -> RuntimeError:
    sc = response.status_code
    body = response.text or ""
    err_code, api_msg = _parse_elevenlabs_detail(body[:4000])
    if sc == 401:
        return RuntimeError(
            "ElevenLabs 401: ELEVENLABS_API_KEY가 잘못되었거나 만료되었습니다."
        )
    if sc == 402:
        if err_code == "paid_plan_required" or (
            api_msg and "library voices" in api_msg.lower()
        ):
            return RuntimeError(
                "ElevenLabs 402 (paid_plan_required): 무료 계정은 API로 '라이브러리 보이스' "
                "(기본·프리셋 음성)를 쓸 수 없습니다. 남은 문자 크레딧과 별개의 플랜 제한입니다. "
                "해결: 대시보드 Voice Lab에서 만든 본인 보이스의 Voice ID를 ELEVENLABS_VOICE_ID에 넣거나, "
                "유료 구독으로 업그레이드하세요. "
                f"[API: {api_msg or err_code}]"
            )
        return RuntimeError(
            "ElevenLabs 402: 결제·크레딧 또는 플랜 제한입니다. "
            f"https://elevenlabs.io 에서 확인하세요. 상세: {api_msg or body[:400]}"
        )
    return RuntimeError(f"ElevenLabs HTTP {sc}: {api_msg or body[:500]}")


def _default_voice_id() -> str:
    # "Aria" — ElevenLabs multilingual_v2 기반 한국어 지원 음성.
    # 더 자연스러운 한국어를 원하면 ELEVENLABS_VOICE_ID 환경변수로
    # ElevenLabs Voice Library에서 조회한 한국어 전용 음성 ID를 설정하세요.
    return "9BWtsMINqrJLrRacOk9x"


class ElevenLabsTTS(TTSProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._api_key = settings.elevenlabs_api_key
        self._voice_id = settings.elevenlabs_voice_id or _default_voice_id()

    def _payload(self, text: str) -> dict[str, Any]:
        return {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

    async def synthesize(self, text: str, *, output_path: Path) -> TTSResult:
        if not text.strip():
            raise ValueError("TTS text is empty")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        timeout = httpx.Timeout(self._settings.tts_timeout_seconds)
        payload = self._payload(text)

        word_timestamps: list[dict[str, Any]] = []
        mp3_bytes: bytes | None = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            if self._settings.elevenlabs_try_timestamps:
                mp3_bytes, word_timestamps = await self._try_timestamps_then_standard(
                    client, payload
                )
            else:
                mp3_bytes = await self._synthesize_standard(client, payload)

        if mp3_bytes is None or not mp3_bytes:
            raise RuntimeError("ElevenLabs returned empty audio")

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
            word_timestamps=word_timestamps,
        )

    async def _try_timestamps_then_standard(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> tuple[bytes, list[dict[str, Any]]]:
        url_ts = f"{ELEVEN_BASE}/text-to-speech/{self._voice_id}/with-timestamps"
        headers_json = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = await client.post(url_ts, headers=headers_json, json=payload)
            if response.status_code == 401:
                raise _runtime_error_for_elevenlabs(response) from None
            if response.status_code in _TIMESTAMP_FALLBACK_STATUSES:
                if _is_library_voice_free_tier_block(
                    response.status_code, response.text or ""
                ):
                    raise _runtime_error_for_elevenlabs(response) from None
                logger.info(
                    "ElevenLabs with-timestamps returned %s; using standard TTS (no word timestamps).",
                    response.status_code,
                )
                raw = await self._synthesize_standard(client, payload)
                return raw, []

            response.raise_for_status()
            data = response.json()
            audio_b64 = data.get("audio_base64")
            if not audio_b64:
                raise RuntimeError("ElevenLabs response missing audio_base64")
            mp3 = base64.b64decode(audio_b64)
            words = _alignment_to_words(data.get("alignment") or {})
            return mp3, words
        except httpx.HTTPStatusError as exc:
            r = exc.response
            if r is not None and r.status_code in _TIMESTAMP_FALLBACK_STATUSES:
                if _is_library_voice_free_tier_block(r.status_code, r.text or ""):
                    raise _runtime_error_for_elevenlabs(r) from exc
                logger.info(
                    "ElevenLabs with-timestamps HTTP error %s; using standard TTS.",
                    r.status_code,
                )
                raw = await self._synthesize_standard(client, payload)
                return raw, []
            raise

    async def _synthesize_standard(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> bytes:
        url = f"{ELEVEN_BASE}/text-to-speech/{self._voice_id}"
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        response = await client.post(url, headers=headers, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            body = (response.text or "")[:800]
            logger.error("ElevenLabs standard TTS HTTP %s: %s", response.status_code, body)
            if response.status_code in (401, 402):
                raise _runtime_error_for_elevenlabs(response) from None
            raise
        return response.content


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
        raise RuntimeError(
            "ffmpeg is required to convert ElevenLabs audio to WAV."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg failed: {exc.stderr[:500]}") from exc


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
    except (FileNotFoundError, subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("ffprobe failed, using fallback duration: %s", exc)
        return 1.0


def _alignment_to_words(alignment: dict[str, Any]) -> list[dict[str, Any]]:
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    if not chars or not starts or not ends:
        return []
    if not (len(chars) == len(starts) == len(ends)):
        return []

    words: list[dict[str, Any]] = []
    current = ""
    w_start: float | None = None
    w_end: float | None = None

    for ch, s, e in zip(chars, starts, ends, strict=False):
        if ch.isspace():
            if current.strip() and w_start is not None and w_end is not None:
                words.append(
                    {"word": current.strip(), "start": w_start, "end": w_end}
                )
            current = ""
            w_start = None
            w_end = None
            continue
        if w_start is None:
            w_start = float(s)
        w_end = float(e)
        current += ch

    if current.strip() and w_start is not None and w_end is not None:
        words.append({"word": current.strip(), "start": w_start, "end": w_end})

    return words
