from manim_video_gen.video.latex_korean import (
    apply_text_glyph_fallback,
    derivation_annotation_needs_mathtex,
    prepare_derivation_annotation,
    sanitize_latex_for_text_label,
    wrap_korean_text_runs,
)


def test_wrap_korean_phrase_with_spaces():
    src = r"x + 최대 값"
    out = wrap_korean_text_runs(src)
    assert out == r"x + \text{최대\hspace{0.33em}값}"


def test_wrap_korean_phrase_with_digit_keeps_space_visible():
    src = r"x + 가 실근 3개"
    out = wrap_korean_text_runs(src)
    assert out == r"x + \text{가\hspace{0.33em}실근\hspace{0.33em}3개}"


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


def test_math_fallback_for_unsupported_superscript_t():
    src = r"b = (-1,-3)ᵀ"
    out = wrap_korean_text_runs(src)
    assert out == r"b = (-1,-3)^{\mathsf T}"


def test_derivation_annotation_needs_mathtex_for_backslash_or_dollar():
    assert derivation_annotation_needs_mathtex(r"\alpha") is True
    assert derivation_annotation_needs_mathtex("$x$") is True
    assert derivation_annotation_needs_mathtex("인수분해") is False


def test_prepare_derivation_annotation_mathtex_vs_text():
    mt, use = prepare_derivation_annotation(r"\alpha \text{ 도출}")
    assert use is True
    assert "\\text{" in mt
    plain, use2 = prepare_derivation_annotation("인수분해")
    assert use2 is False
    assert plain == "인수분해"


def test_text_fallback_for_unsupported_superscript_t():
    src = "b = (-1,-3)ᵀ"
    out = apply_text_glyph_fallback(src)
    assert out == "b = (-1,-3)^T"
