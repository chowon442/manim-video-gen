"""extract_json_from_text 엣지 케이스 테스트."""

import pytest
import httpx

from manim_video_gen.config import Settings
from manim_video_gen.llm.client import OpenRouterClient
from manim_video_gen.llm.client import extract_json_from_text


def test_plain_json_object():
    assert extract_json_from_text('{"key": "value"}') == {"key": "value"}


def test_plain_json_array():
    assert extract_json_from_text("[1, 2, 3]") == [1, 2, 3]


def test_markdown_fence_json():
    text = '```json\n{"a": 1}\n```'
    assert extract_json_from_text(text) == {"a": 1}


def test_markdown_fence_no_lang():
    text = '```\n{"b": 2}\n```'
    assert extract_json_from_text(text) == {"b": 2}


def test_trailing_text_after_json():
    text = '{"x": 10} 이것은 설명 텍스트입니다.'
    result = extract_json_from_text(text)
    assert result == {"x": 10}


def test_leading_text_before_json():
    text = '다음은 JSON입니다:\n{"result": true}'
    result = extract_json_from_text(text)
    assert result == {"result": True}


def test_nested_json_object():
    text = '{"outer": {"inner": [1, 2, 3]}}'
    result = extract_json_from_text(text)
    assert result == {"outer": {"inner": [1, 2, 3]}}


def test_array_before_object():
    text = '[{"id": 1}, {"id": 2}]'
    result = extract_json_from_text(text)
    assert result == [{"id": 1}, {"id": 2}]


def test_no_json_raises():
    with pytest.raises(ValueError, match="No JSON"):
        extract_json_from_text("이건 JSON이 아닙니다.")


def test_empty_string_raises():
    with pytest.raises(ValueError):
        extract_json_from_text("")


def test_whitespace_only_raises():
    with pytest.raises(ValueError):
        extract_json_from_text("   \n  ")


def test_numeric_values():
    text = '{"pi": 3.14, "neg": -1, "zero": 0}'
    result = extract_json_from_text(text)
    assert result["pi"] == pytest.approx(3.14)
    assert result["neg"] == -1
    assert result["zero"] == 0


def test_unicode_content():
    text = '{"narration": "이차방정식 풀이", "id": 1}'
    result = extract_json_from_text(text)
    assert result["narration"] == "이차방정식 풀이"


def test_markdown_fence_with_surrounding_text():
    text = '모델 응답:\n```json\n{"status": "ok"}\n```\n끝.'
    result = extract_json_from_text(text)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_openrouter_retries_body_error_524_once_then_succeeds(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setenv("MANIM_VIDEO_GEN_OPENROUTER_RETRIES", "1")
    monkeypatch.setenv("MANIM_VIDEO_GEN_OPENROUTER_RETRY_BASE_SECONDS", "0")
    monkeypatch.setenv("MANIM_VIDEO_GEN_OPENROUTER_RETRY_MAX_SECONDS", "0")
    settings = Settings()

    class _Resp:
        def __init__(self, payload: dict):
            self.status_code = 200
            self._payload = payload
            self.text = str(payload)

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class _FakeClient:
        def __init__(self):
            self.calls = 0

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                return _Resp(
                    {"error": {"message": "Provider returned error", "code": 524}}
                )
            return _Resp({"choices": [{"message": {"content": "ok"}}]})

    c = OpenRouterClient(settings)
    fake = _FakeClient()
    c._client = fake
    out = await c.complete_text(
        model="anthropic/claude-sonnet-4.6",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == "ok"
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_openrouter_retries_transport_error_once_then_succeeds(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "dummy")
    monkeypatch.setenv("MANIM_VIDEO_GEN_OPENROUTER_RETRIES", "1")
    monkeypatch.setenv("MANIM_VIDEO_GEN_OPENROUTER_RETRY_BASE_SECONDS", "0")
    monkeypatch.setenv("MANIM_VIDEO_GEN_OPENROUTER_RETRY_MAX_SECONDS", "0")
    settings = Settings()

    class _Resp:
        status_code = 200
        text = "ok"

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class _FakeClient:
        def __init__(self):
            self.calls = 0

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise httpx.ReadTimeout(
                    "timeout", request=httpx.Request("POST", "https://x")
                )
            return _Resp()

    c = OpenRouterClient(settings)
    fake = _FakeClient()
    c._client = fake
    out = await c.complete_text(
        model="anthropic/claude-sonnet-4.6",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert out == "ok"
    assert fake.calls == 2
