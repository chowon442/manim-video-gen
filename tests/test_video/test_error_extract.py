"""error_extract tests."""

from manim_video_gen.video.error_extract import refine_manim_render_error


def test_refine_prefers_traceback_tail():
    blob = "noise\n" * 5
    blob += "Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: bad\n"
    out = refine_manim_render_error(blob)
    assert "Traceback" in out
    assert "ValueError" in out


def test_refine_fallback_tail():
    lines = [f"line {i}" for i in range(50)]
    out = refine_manim_render_error("\n".join(lines))
    assert "line 49" in out
