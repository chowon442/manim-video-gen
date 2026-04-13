"""math_notation polish tests."""

from manim_video_gen.utils.math_notation import polish_narration_math, polish_tts_text


def test_polish_x_squared():
    assert "제곱" in polish_narration_math("식 x^2 는")


def test_polish_pi():
    assert "파이" in polish_narration_math(r"원주율 \pi")


def test_plain_text_unchanged():
    assert polish_narration_math("안녕하세요") == "안녕하세요"


def test_polish_tts_text_avoids_spoken_parenthesis_markers():
    src = "괄호 열기 엑스 더하기 삼 괄호 닫기 의 제곱은 영입니다."
    out = polish_tts_text(src)
    assert "괄호" not in out
    assert "엑스 더하기 삼" in out


def test_polish_tts_text_converts_parenthesized_symbolic_math():
    src = "(x+3)^2 = 0"
    out = polish_tts_text(src)
    assert "(" not in out
    assert ")" not in out
    assert "^" not in out
    assert "엑스" in out
    assert "제곱" in out
