"""math_notation polish tests."""

from manim_video_gen.utils.math_notation import polish_narration_math


def test_polish_x_squared():
    assert "제곱" in polish_narration_math("식 x^2 는")


def test_polish_pi():
    assert "파이" in polish_narration_math(r"원주율 \pi")


def test_plain_text_unchanged():
    assert polish_narration_math("안녕하세요") == "안녕하세요"
