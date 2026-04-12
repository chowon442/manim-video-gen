from manim_video_gen.video.latex_korean import (
    sanitize_latex_for_text_label,
    wrap_korean_text_runs,
)


def test_wrap_korean_phrase_with_spaces():
    src = r"x + 최대 값"
    out = wrap_korean_text_runs(src)
    assert out == r"x + \text{최대 값}"


def test_existing_text_block_is_preserved():
    src = r"x + \text{이미 처리됨}"
    out = wrap_korean_text_runs(src)
    assert out == src


def test_single_korean_word_not_wrapped():
    src = r"x + 최대"
    out = wrap_korean_text_runs(src)
    assert out == src


def test_sanitize_latex_for_text_label_removes_text_cmd_and_spacing():
    src = r"(-3,\,12)\text{ 극대}"
    out = sanitize_latex_for_text_label(src)
    assert out == "(-3, 12) 극대"
