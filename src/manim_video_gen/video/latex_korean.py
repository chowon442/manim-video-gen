"""Utilities to keep Korean spacing readable inside TeX strings.

Policy:
- Prefer Text() for Korean labels/sentences.
- If Korean must appear in a TeX string, wrap Korean runs with ``\\text{...}``
  so whitespace is preserved in text mode.
"""

from __future__ import annotations

import re


_HANGUL_RUN_RE = re.compile(r"[가-힣0-9]+(?:\s+[가-힣0-9]+)+")
_TEXT_CMD_RE = re.compile(r"\\text\{[^}]*\}")
_TEXT_CMD_CAPTURE_RE = re.compile(r"\\text\s*\{([^{}]*)\}")
_HSPACE_CMD_RE = re.compile(r"\\hspace\s*\{[^{}]*\}")
_SPACING_CMD_RE = re.compile(r"\\[,;:]")
_GENERIC_LATEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")

_MATH_GLYPH_FALLBACKS: dict[str, str] = {
    "ᵀ": r"^{\mathsf T}",
}

_TEXT_GLYPH_FALLBACKS: dict[str, str] = {
    "ᵀ": "^T",
}


def apply_math_glyph_fallback(latex: str) -> str:
    """Replace known unsupported glyphs with MathTex-safe fragments."""
    out = str(latex)
    for src, repl in _MATH_GLYPH_FALLBACKS.items():
        out = out.replace(src, repl)
    return out


def apply_text_glyph_fallback(text: str) -> str:
    """Replace known unsupported glyphs with Text-safe alternatives."""
    out = str(text)
    for src, repl in _TEXT_GLYPH_FALLBACKS.items():
        out = out.replace(src, repl)
    return out


def derivation_annotation_needs_mathtex(s: str) -> bool:
    """True if a derivation step annotation should use MathTex instead of Text.

    Backslash implies LaTeX commands (e.g. ``\\alpha``, ``\\frac``). ``$`` is
    treated as inline math delimiters.
    """
    t = str(s).strip()
    if not t:
        return False
    return "\\" in t or "$" in t


def prepare_derivation_annotation(s: str) -> tuple[str, bool]:
    """Return ``(display_string, use_mathtex)`` for equation_derivation labels.

    MathTex path: ``wrap_korean_text_runs`` so Hangul and spaces work in TeX.
    Text path: ``apply_text_glyph_fallback`` only (no LaTeX).
    """
    t = str(s).strip()
    if not t:
        return "", False
    if derivation_annotation_needs_mathtex(t):
        return wrap_korean_text_runs(t), True
    return apply_text_glyph_fallback(t), False


def _visible_cjk_space_payload(run: str) -> str:
    normalized = re.sub(r"\s+", " ", str(run)).strip()
    return normalized.replace(" ", r"\hspace{0.33em}")


def wrap_korean_text_runs(latex: str) -> str:
    """Wrap Korean word-runs containing spaces with ``\\text{...}``.

    Existing ``\\text{...}`` blocks are preserved.
    """
    s = apply_math_glyph_fallback(latex)
    protected: list[str] = []

    def _protect(m: re.Match[str]) -> str:
        protected.append(m.group(0))
        return f"@@TEXT{len(protected) - 1}@@"

    s = _TEXT_CMD_RE.sub(_protect, s)

    def _repl(m: re.Match[str]) -> str:
        return rf"\text{{{_visible_cjk_space_payload(m.group(0))}}}"

    s = _HANGUL_RUN_RE.sub(_repl, s)

    for idx, blk in enumerate(protected):
        s = s.replace(f"@@TEXT{idx}@@", blk)
    return s


def sanitize_latex_for_text_label(text: str) -> str:
    """Convert light LaTeX fragments into plain text for Text(...)."""
    s = apply_text_glyph_fallback(text)
    s = _SPACING_CMD_RE.sub(" ", s)
    s = _HSPACE_CMD_RE.sub(" ", s)
    s = _TEXT_CMD_CAPTURE_RE.sub(r"\1", s)
    s = _GENERIC_LATEX_CMD_RE.sub("", s)
    s = s.replace("\\", "")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s
