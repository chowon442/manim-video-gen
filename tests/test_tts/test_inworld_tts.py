"""Tests for Inworld TTS provider."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.tts.factory import get_tts_provider
from manim_video_gen.tts.inworld_tts import InworldTTS, _build_payload


def test_get_tts_provider_inworld_returns_inworld_tts(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "inworld")
    monkeypatch.setenv("INWORLD_TTS_API_KEY", "test-key")
    settings = Settings()
    provider = get_tts_provider(settings)
    assert isinstance(provider, InworldTTS)


def test_inworld_tts_init_missing_key_raises(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "inworld")
    monkeypatch.setenv("INWORLD_TTS_API_KEY", "")
    settings = Settings()
    with pytest.raises(TTSError, match="INWORLD_TTS_API_KEY"):
        InworldTTS(settings)


def test_build_payload_omits_timestamp_when_none(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_INWORLD_TTS_TIMESTAMP_TYPE", "NONE")
    s = Settings()
    body = _build_payload(s, "hello")
    assert "timestampType" not in body
    assert body["voiceId"] == "Hyunwoo"
    assert body["modelId"] == "inworld-tts-1.5-max"


def test_build_payload_word_timestamp(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_INWORLD_TTS_TIMESTAMP_TYPE", "WORD")
    s = Settings()
    body = _build_payload(s, "hello")
    assert body.get("timestampType") == "WORD"


@pytest.mark.asyncio
async def test_synthesize_success_mocked_http(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INWORLD_TTS_API_KEY", "dummy")
    settings = Settings()

    monkeypatch.setattr(
        "manim_video_gen.tts.inworld_tts._ffprobe_duration_seconds",
        lambda _p: 0.42,
    )

    def _fake_convert(src, dst) -> None:
        dst.write_bytes(b"fake-wav")

    monkeypatch.setattr(
        "manim_video_gen.tts.inworld_tts._ffmpeg_convert_to_wav",
        _fake_convert,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""
    mock_response.json.return_value = {
        "audioContent": base64.b64encode(b"fake-mp3-bytes").decode("ascii"),
    }

    mock_instance = MagicMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)

    out = tmp_path / "seg.wav"
    with patch(
        "manim_video_gen.tts.inworld_tts.httpx.AsyncClient",
        return_value=mock_instance,
    ):
        tts = InworldTTS(settings)
        result = await tts.synthesize("테스트", output_path=out)

    assert result.duration_seconds == 0.42
    assert result.audio_path == out
    assert out.read_bytes() == b"fake-wav"
    mock_instance.post.assert_called_once()
    call_kw = mock_instance.post.call_args[1]
    assert call_kw["json"]["text"] == "테스트"


@pytest.mark.asyncio
async def test_synthesize_http_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INWORLD_TTS_API_KEY", "dummy")
    settings = Settings()

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "unauthorized"

    mock_instance = MagicMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "manim_video_gen.tts.inworld_tts.httpx.AsyncClient",
        return_value=mock_instance,
    ):
        tts = InworldTTS(settings)
        with pytest.raises(TTSError, match="HTTP 401"):
            await tts.synthesize("x", output_path=tmp_path / "a.wav")


@pytest.mark.asyncio
async def test_synthesize_missing_audio_content(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INWORLD_TTS_API_KEY", "dummy")
    settings = Settings()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    mock_instance = MagicMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "manim_video_gen.tts.inworld_tts.httpx.AsyncClient",
        return_value=mock_instance,
    ):
        tts = InworldTTS(settings)
        with pytest.raises(TTSError, match="missing audioContent"):
            await tts.synthesize("x", output_path=tmp_path / "a.wav")
