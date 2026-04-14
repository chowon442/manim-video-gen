"""subtitle ASS generation tests."""

from pathlib import Path

import pytest

from manim_video_gen.video.subtitle import (
    _ass_escape,
    _normalize_subtitle_narration,
    _strip_math_delimiters,
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
    assert "Style: Default,Noto Sans KR,42" in text


def test_ass_escape_strips_backslashes():
    assert _ass_escape("x \\text test") == "x test"
    assert "\\" not in _ass_escape("hello\\world")


def test_ass_escape_braces():
    assert _ass_escape("test {bold}") == "test \\{bold\\}"


def test_normalize_subtitle_narration_converts_subscript_braces():
    src = "f_{x₁x₁} = 2, f_{x₂x₂} = 4"
    out = _normalize_subtitle_narration(src)
    assert "f_(x₁x₁)" in out
    assert "f_(x₂x₂)" in out
    assert "\\{" not in out


def test_normalize_subtitle_narration_strips_text_cmd():
    src = r"(-3,\,12)\text{ 극대}"
    out = _normalize_subtitle_narration(src)
    assert out == "(-3, 12) 극대"


def test_strip_math_delimiters_removes_dollar_wrappers():
    assert _strip_math_delimiters(r"$g(x)$") == "g(x)"
    assert _strip_math_delimiters(r"$$g(x)$$") == "g(x)"


def test_normalize_subtitle_narration_greek_to_unicode():
    assert "α" in _normalize_subtitle_narration(r"$f(\alpha)=f(1)$")
    assert "$" not in _normalize_subtitle_narration(r"$f(\alpha)=f(1)$")


def test_normalize_subtitle_narration_frac_and_sqrt():
    out = _normalize_subtitle_narration(r"$\frac{1}{2}$와 $\sqrt{3}$")
    assert out == "(1)/(2)와 √(3)"


def test_normalize_subtitle_narration_sub_sup_unicode():
    """$f(x_1)={x_1}^3+6y^3$ -> plain Unicode (no $, sub/sup as Unicode)."""
    out = _normalize_subtitle_narration("$f(x_1)={x_1}^3+6y^3$")
    assert out == "f(x₁)=x₁³+6y³"


def test_wrap_inserts_ass_line_breaks():
    long = "이것은 매우 긴 자막 문장입니다 이것은 매우 긴 자막 문장입니다 자막이 길면 줄바꿈이 필요합니다"
    wrapped = _wrap_narration_lines(long, max_chars=20)
    assert "\\N" in wrapped


def test_generate_ass_auto_wrap_mode_does_not_force_manual_breaks(tmp_path: Path):
    out = tmp_path / "auto.ass"
    long_text = (
        "이것은 자동 줄바꿈을 확인하기 위한 매우 긴 자막 문장입니다 "
        "글자 수 기준 강제 개행 없이 ASS 렌더러가 가로폭 기준으로 알아서 줄을 나눠야 합니다"
    )
    generate_ass_subtitle(
        long_text,
        5.0,
        out,
        wrap_mode="auto",
    )
    text = out.read_text(encoding="utf-8")
    assert "\\N" not in text


def test_generate_ass_char_wrap_mode_keeps_manual_breaks(tmp_path: Path):
    out = tmp_path / "char.ass"
    long_text = (
        "이것은 문자수 개행을 확인하기 위한 매우 긴 자막 문장입니다 "
        "글자 수 기준으로 끊어야 할 때는 ASS 강제 개행이 들어가야 합니다"
    )
    generate_ass_subtitle(
        long_text,
        5.0,
        out,
        wrap_mode="char",
        max_chars=20,
    )
    text = out.read_text(encoding="utf-8")
    assert "\\N" in text


def test_no_double_escaped_line_breaks(tmp_path: Path):
    """Ensure \\N (ASS line break) is not double-escaped to \\\\N."""
    out = tmp_path / "sub.ass"
    long_text = "이것은 매우 긴 자막 문장입니다 이것은 매우 긴 자막 문장입니다 줄바꿈 확인용 테스트"
    generate_ass_subtitle(long_text, 5.0, out, wrap_mode="char")
    text = out.read_text(encoding="utf-8")
    assert "\\\\N" not in text


def test_subtitle_text_preserves_math_notation(tmp_path: Path):
    """narration with light math notation should appear readable in subtitles."""
    out = tmp_path / "sub.ass"
    narration = "x² + 6x + 9 = 0의 해를 구해봅시다."
    generate_ass_subtitle(narration, 4.0, out, wrap_mode="char")
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


def test_subtitle_style_options_applied(tmp_path: Path):
    out = tmp_path / "styled.ass"
    generate_ass_subtitle(
        "테스트 문장",
        2.0,
        out,
        font_size=38,
        margin_l=40,
        margin_r=44,
        margin_v=28,
        max_chars=10,
    )
    text = out.read_text(encoding="utf-8")
    assert "Style: Default,Noto Sans KR,38" in text
    assert ",2,40,44,28,1" in text


def test_generate_chain_ass_length_mismatch():
    with pytest.raises(ValueError, match="length mismatch"):
        generate_chain_ass_subtitle(["a"], [1.0, 2.0], Path("/tmp/x.ass"))
