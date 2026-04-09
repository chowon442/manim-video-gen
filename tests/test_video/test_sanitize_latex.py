"""sanitize_latex_for_compilation — 한글·비ASCII LaTeX 정리."""

from manim_video_gen.video.code_validator import sanitize_latex_for_compilation


def test_text_or_korean_becomes_quad() -> None:
    s = r"x = \frac{a}{2} \quad \text{또는} \quad x = b"
    out = sanitize_latex_for_compilation(s)
    assert "또는" not in out
    assert "\\text{" not in out or "또는" not in out
    assert r"\quad" in out


def test_bare_hangul_stripped() -> None:
    out = sanitize_latex_for_compilation(r"x = 1 또는 x = 2")
    assert "또는" not in out
    assert "x = 1" in out and "x = 2" in out


def test_ascii_preserved() -> None:
    s = r"x = \frac{-3 + 3\sqrt{3}\, i}{2}"
    assert sanitize_latex_for_compilation(s) == s
