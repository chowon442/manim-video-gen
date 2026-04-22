"""Tests for xAI Grok TTS provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.llm.prompts.scriptify import (
    SCRIPTIFY_GROK_TTS_TAG_APPENDIX,
    scriptify_system_prompt,
)
from manim_video_gen.tts.factory import get_tts_provider
from manim_video_gen.models.script import Segment, VideoScript
from manim_video_gen.pipeline.orchestrator import _ensure_tts_text
from manim_video_gen.tts.grok_tts import GrokTTS, _build_payload


def test_get_tts_provider_grok_returns_grok_tts(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "grok")
    monkeypatch.setenv("XAI_API_KEY", "xai-test-key")
    settings = Settings()
    provider = get_tts_provider(settings)
    assert type(provider).__name__ == "GrokTTS"


def test_get_tts_provider_xai_alias(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "xai")
    monkeypatch.setenv("MANIM_VIDEO_GEN_XAI_API_KEY", "xai-test-key")
    settings = Settings()
    provider = get_tts_provider(settings)
    assert type(provider).__name__ == "GrokTTS"


def test_grok_tts_init_missing_key_raises(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "grok")
    monkeypatch.setenv("XAI_API_KEY", "")
    monkeypatch.setenv("MANIM_VIDEO_GEN_XAI_API_KEY", "")
    settings = Settings()
    with pytest.raises(TTSError, match="XAI_API_KEY"):
        GrokTTS(settings)


def test_build_payload_defaults(monkeypatch) -> None:
    monkeypatch.setenv("XAI_API_KEY", "k")
    s = Settings()
    body = _build_payload(s, "hello")
    assert body["text"] == "hello"
    assert body["voice_id"] == "Ara"
    assert body["language"] == "ko"
    assert body["output_format"]["codec"] == "mp3"
    assert body["output_format"]["sample_rate"] == 44100


def test_scriptify_system_prompt_grok_includes_appendix(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "grok")
    s = Settings()
    out = scriptify_system_prompt(s)
    assert SCRIPTIFY_GROK_TTS_TAG_APPENDIX.strip() in out
    assert "[pause]" in out


def test_ensure_tts_text_grok_preserves_speech_tags(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "grok")
    monkeypatch.setenv("XAI_API_KEY", "k")
    settings = Settings()
    seg = Segment(
        id=0,
        narration="x² = 1",
        tts_text="엑스 제곱 [pause] 은 일",
        visual_description="v",
        visual_type="equation_write",
        visual_params={"latex": "x^2=1"},
        prev_scene_state=None,
    )
    script = VideoScript(title="t", segments=[seg])
    out = _ensure_tts_text(script, settings)
    assert out.segments[0].tts_text == "엑스 제곱 [pause] 은 일"


def test_scriptify_system_prompt_non_grok_omits_appendix(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "elevenlabs")
    s = Settings()
    out = scriptify_system_prompt(s)
    assert SCRIPTIFY_GROK_TTS_TAG_APPENDIX.strip() not in out


@pytest.mark.asyncio
async def test_synthesize_success_mocked_http(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XAI_API_KEY", "dummy")
    settings = Settings()

    monkeypatch.setattr(
        "manim_video_gen.tts.grok_tts._ffprobe_duration_seconds",
        lambda _p: 0.42,
    )

    def _fake_convert(src, dst) -> None:
        dst.write_bytes(b"fake-wav")

    monkeypatch.setattr(
        "manim_video_gen.tts.grok_tts._ffmpeg_convert_to_wav",
        _fake_convert,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""
    mock_response.content = b"fake-mp3-bytes"

    mock_instance = MagicMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)

    out = tmp_path / "seg.wav"
    with patch(
        "manim_video_gen.tts.grok_tts.httpx.AsyncClient",
        return_value=mock_instance,
    ):
        tts = GrokTTS(settings)
        result = await tts.synthesize("테스트 [pause] 끝", output_path=out)

    assert result.duration_seconds == 0.42
    assert result.audio_path == out
    assert out.read_bytes() == b"fake-wav"
    mock_instance.post.assert_called_once()
    call_kw = mock_instance.post.call_args[1]
    assert call_kw["json"]["text"] == "테스트 [pause] 끝"


@pytest.mark.asyncio
async def test_synthesize_http_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XAI_API_KEY", "dummy")
    settings = Settings()

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "unauthorized"

    mock_instance = MagicMock()
    mock_instance.post = AsyncMock(return_value=mock_response)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "manim_video_gen.tts.grok_tts.httpx.AsyncClient",
        return_value=mock_instance,
    ):
        tts = GrokTTS(settings)
        with pytest.raises(TTSError, match="HTTP 401"):
            await tts.synthesize("x", output_path=tmp_path / "a.wav")
