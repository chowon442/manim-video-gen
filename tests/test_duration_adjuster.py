from manim_video_gen.video.duration_adjuster import (
    adjust_duration,
    estimate_construct_duration_seconds,
)


def test_estimate_duration_sums_play_and_wait() -> None:
    code = """
from manim import *

class Segment(Scene):
    def construct(self):
        self.play(Write(MathTex("1")), run_time=1.5)
        self.wait(0.25)
"""
    assert abs(estimate_construct_duration_seconds(code) - 1.75) < 1e-6


def test_adjust_duration_appends_wait() -> None:
    code = """
from manim import *

class Segment(Scene):
    def construct(self):
        self.play(Write(MathTex("1")), run_time=1.0)
"""
    adjusted = adjust_duration(code, target_duration=3.0)
    assert "self.wait(" in adjusted
    assert estimate_construct_duration_seconds(adjusted) >= 2.99
