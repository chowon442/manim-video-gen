"""Tests for Replicate qwen3-tts provider."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from manim_video_gen.config import Settings
from manim_video_gen.exceptions import TTSError
from manim_video_gen.tts.factory import get_tts_provider
from manim_video_gen.tts.replicate_tts import (
    ReplicateTTS,
    _build_input,
    _output_to_url,
)


def test_get_tts_provider_replicate_returns_replicate_tts(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "replicate")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "test-token")
    settings = Settings()
    provider = get_tts_provider(settings)
    assert isinstance(provider, ReplicateTTS)


def test_replicate_tts_init_missing_token_raises(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_TTS_PROVIDER", "replicate")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "")
    settings = Settings()
    with pytest.raises(TTSError, match="REPLICATE_API_TOKEN"):
        ReplicateTTS(settings)


def test_require_replicate_raises_value_error(monkeypatch) -> None:
    monkeypatch.setenv("REPLICATE_API_TOKEN", "")
    s = Settings()
    with pytest.raises(ValueError, match="REPLICATE_API_TOKEN"):
        s.require_replicate()


def test_require_replicate_ok(monkeypatch) -> None:
    monkeypatch.setenv("REPLICATE_API_TOKEN", "x")
    s = Settings()
    s.require_replicate()


def test_build_input_custom_voice(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "custom_voice")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_SPEAKER", "Dylan")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_LANGUAGE", "Spanish")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_STYLE", "speak slowly")
    s = Settings()
    inp = _build_input(s, "Hola")
    assert inp["mode"] == "custom_voice"
    assert inp["text"] == "Hola"
    assert inp["speaker"] == "Dylan"
    assert inp["language"] == "Spanish"
    assert inp["style_instruction"] == "speak slowly"


def test_build_input_custom_voice_student_overrides(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "custom_voice")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_SPEAKER", "Teacher")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_LANGUAGE", "Korean")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_STYLE", "teacher style")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_SPEAKER", "Student")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_LANGUAGE", "auto")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_STYLE", "question style")
    s = Settings()
    inp = _build_input(s, "질문입니다", speaker_role="student")
    assert inp["mode"] == "custom_voice"
    assert inp["speaker"] == "Student"
    assert inp["language"] == "auto"
    assert inp["style_instruction"] == "question style"


def test_build_input_voice_clone(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "voice_clone")
    monkeypatch.setenv(
        "MANIM_VIDEO_GEN_REPLICATE_TTS_REF_AUDIO",
        "https://example.com/ref.wav",
    )
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_REF_TEXT", "hello world")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_SPEAKER", "Aiden")
    s = Settings()
    inp = _build_input(s, "Clone me")
    assert inp["mode"] == "voice_clone"
    assert inp["reference_audio"] == "https://example.com/ref.wav"
    assert inp["reference_text"] == "hello world"
    assert inp["speaker"] == "Aiden"


def test_build_input_voice_clone_student_speaker_override(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "voice_clone")
    monkeypatch.setenv(
        "MANIM_VIDEO_GEN_REPLICATE_TTS_REF_AUDIO",
        "https://example.com/ref.wav",
    )
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_SPEAKER", "Teacher")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_SPEAKER", "Student")
    s = Settings()
    inp = _build_input(s, "Clone student", speaker_role="student")
    assert inp["speaker"] == "Student"


def test_build_input_voice_clone_missing_audio_raises(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "voice_clone")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_REF_AUDIO", "")
    s = Settings()
    with pytest.raises(TTSError, match="REF_AUDIO"):
        _build_input(s, "x")


def test_build_input_voice_design(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "voice_design")
    monkeypatch.setenv(
        "MANIM_VIDEO_GEN_REPLICATE_TTS_VOICE_DESC",
        "A warm female voice",
    )
    s = Settings()
    inp = _build_input(s, "Hi")
    assert inp["mode"] == "voice_design"
    assert inp["voice_description"] == "A warm female voice"


def test_build_input_voice_design_missing_desc_raises(monkeypatch) -> None:
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "voice_design")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_VOICE_DESC", "")
    s = Settings()
    with pytest.raises(TTSError, match="VOICE_DESC"):
        _build_input(s, "x")


def test_output_to_url_string() -> None:
    assert (
        _output_to_url("https://cdn.example/out.wav") == "https://cdn.example/out.wav"
    )


def test_output_to_url_object_with_url() -> None:
    obj = MagicMock()
    obj.url = "https://cdn.example/f.wav"
    assert _output_to_url(obj) == "https://cdn.example/f.wav"


def test_output_to_url_invalid_raises() -> None:
    with pytest.raises(TTSError, match="unexpected output"):
        _output_to_url(42)


def test_output_to_url_list_single_string() -> None:
    assert (
        _output_to_url(["https://cdn.example/out.wav"]) == "https://cdn.example/out.wav"
    )


def test_output_to_url_list_single_object_with_url() -> None:
    obj = MagicMock()
    obj.url = "https://cdn.example/f.wav"
    assert _output_to_url([obj]) == "https://cdn.example/f.wav"


@pytest.mark.asyncio
async def test_synthesize_downloads_and_writes_wav(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPLICATE_API_TOKEN", "secret")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_MODE", "custom_voice")
    monkeypatch.setenv("MANIM_VIDEO_GEN_REPLICATE_TTS_SPEAKER", "Aiden")
    monkeypatch.setattr(
        "manim_video_gen.tts.replicate_tts._ffprobe_duration_seconds",
        lambda path: 2.5,
    )

    async def fake_to_thread(fn, *args, **kwargs):
        return "https://example.com/audio.wav"

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    class FakeAsyncClient:
        def __init__(self, *a, **k) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url: str):
            assert url == "https://example.com/audio.wav"
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.content = b"fake-wav-bytes"
            return resp

    monkeypatch.setattr(
        "manim_video_gen.tts.replicate_tts.httpx.AsyncClient",
        FakeAsyncClient,
    )

    settings = Settings()
    tts = ReplicateTTS(settings)
    out = tmp_path / "seg.wav"
    result = await tts.synthesize("Hello test", output_path=out)

    assert out.read_bytes() == b"fake-wav-bytes"
    assert result.audio_path == out
    assert result.duration_seconds == 2.5
    assert result.word_timestamps == []


@pytest.mark.asyncio
async def test_synthesize_empty_text_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REPLICATE_API_TOKEN", "secret")
    settings = Settings()
    tts = ReplicateTTS(settings)
    with pytest.raises(TTSError, match="empty"):
        await tts.synthesize("   ", output_path=tmp_path / "a.wav")
