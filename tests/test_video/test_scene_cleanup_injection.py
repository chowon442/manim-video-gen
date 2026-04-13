from manim_video_gen.video.duration_adjuster import ensure_scene_cleanup


def test_injects_cleanup_when_missing():
    code = """
from manim import *

class Segment(Scene):
    def construct(self):
        eq = MathTex("x=1")
        self.play(Write(eq), run_time=1.0)
        self.wait(2.0)
"""
    out = ensure_scene_cleanup(code)
    assert "self.play(*[FadeOut(m) for m in list(self.mobjects)]" in out
    assert "self.clear()" in out


def test_does_not_duplicate_cleanup_when_present():
    code = """
from manim import *

class Segment(Scene):
    def construct(self):
        eq = MathTex("x=1")
        self.play(Write(eq), run_time=1.0)
        self.wait(2.0)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.35)
"""
    out = ensure_scene_cleanup(code)
    assert out.count("FadeOut(") == 1


def test_injects_clear_even_when_fadeout_exists():
    code = """
from manim import *

class Segment(Scene):
    def construct(self):
        eq = MathTex("x=1")
        self.play(Write(eq), run_time=1.0)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.35)
"""
    out = ensure_scene_cleanup(code)
    assert out.count("FadeOut(") == 1
    assert "self.clear()" in out


def test_cleanup_can_be_disabled():
    code = """
from manim import *

class Segment(Scene):
    def construct(self):
        eq = MathTex("x=1")
        self.play(Write(eq), run_time=1.0)
"""
    out = ensure_scene_cleanup(code, enabled=False)
    assert out == code
