"""extract_json_from_text 엣지 케이스 테스트."""

import pytest

from manim_video_gen.llm.client import extract_json_from_text


def test_plain_json_object():
    assert extract_json_from_text('{"key": "value"}') == {"key": "value"}


def test_plain_json_array():
    assert extract_json_from_text('[1, 2, 3]') == [1, 2, 3]


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
    text = "모델 응답:\n```json\n{\"status\": \"ok\"}\n```\n끝."
    result = extract_json_from_text(text)
    assert result == {"status": "ok"}
