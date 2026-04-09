"""subtitle ASS generation tests."""

from pathlib import Path

import pytest

from manim_video_gen.video.subtitle import (
    _ass_escape,
    _wrap_narration_lines,
    generate_ass_subtitle,
    generate_chain_ass_subtitle,
)


def test_generate_ass_contains_dialogue_and_timing(tmp_path: Path):
    out = tmp_path / "sub.ass"
    generate_ass_subtitle("안녕하세요 테스트", 3.5, out)
    text = out.read_text(encoding="utf-8")
    assert "Dialogue:" in text
    assert "PlayResX: 1920" in text
    assert "0:00:03.50" in text


def test_ass_escape_strips_backslashes():
    assert _ass_escape("x \\text test") == "x text test"
    assert "\\" not in _ass_escape("hello\\world")


def test_ass_escape_braces():
    assert _ass_escape("test {bold}") == "test \\{bold\\}"


def test_wrap_inserts_ass_line_breaks():
    long = "이것은 매우 긴 자막 문장입니다 이것은 매우 긴 자막 문장입니다 자막이 길면 줄바꿈이 필요합니다"
    wrapped = _wrap_narration_lines(long, max_chars=20)
    assert "\\N" in wrapped


def test_no_double_escaped_line_breaks(tmp_path: Path):
    """Ensure \\N (ASS line break) is not double-escaped to \\\\N."""
    out = tmp_path / "sub.ass"
    long_text = "이것은 매우 긴 자막 문장입니다 이것은 매우 긴 자막 문장입니다 줄바꿈 확인용 테스트"
    generate_ass_subtitle(long_text, 5.0, out)
    text = out.read_text(encoding="utf-8")
    assert "\\\\N" not in text


def test_subtitle_text_preserves_math_notation(tmp_path: Path):
    """narration with light math notation should appear readable in subtitles."""
    out = tmp_path / "sub.ass"
    narration = "x² + 6x + 9 = 0의 해를 구해봅시다."
    generate_ass_subtitle(narration, 4.0, out)
    text = out.read_text(encoding="utf-8")
    assert "x²" in text
    assert "6x" in text
    assert "\\" not in text or "\\N" in text or "\\{" in text


def test_generate_chain_ass_three_dialogues(tmp_path: Path):
    out = tmp_path / "chain.ass"
    generate_chain_ass_subtitle(
        ["첫 줄", "둘째", "셋째"],
        [3.5, 2.0, 1.5],
        out,
    )
    text = out.read_text(encoding="utf-8")
    assert text.count("Dialogue:") == 3
    assert "0:00:03.50" in text
    assert "0:00:05.50" in text


def test_generate_chain_ass_length_mismatch():
    with pytest.raises(ValueError, match="length mismatch"):
        generate_chain_ass_subtitle(["a"], [1.0, 2.0], Path("/tmp/x.ass"))
