"""Utilities to keep Korean spacing readable inside TeX strings.

Policy:
- Prefer Text() for Korean labels/sentences.
- If Korean must appear in a TeX string, wrap Korean runs with ``\\text{...}``
  so whitespace is preserved in text mode.
"""

from __future__ import annotations

import re


_HANGUL_RUN_RE = re.compile(r"[가-힣]+(?:\s+[가-힣]+)+")
_TEXT_CMD_RE = re.compile(r"\\text\{[^}]*\}")
_TEXT_CMD_CAPTURE_RE = re.compile(r"\\text\s*\{([^{}]*)\}")
_SPACING_CMD_RE = re.compile(r"\\[,;:]")
_GENERIC_LATEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")


def wrap_korean_text_runs(latex: str) -> str:
    """Wrap Korean word-runs containing spaces with ``\\text{...}``.

    Existing ``\\text{...}`` blocks are preserved.
    """
    s = str(latex)
    protected: list[str] = []

    def _protect(m: re.Match[str]) -> str:
        protected.append(m.group(0))
        return f"@@TEXT{len(protected) - 1}@@"

    s = _TEXT_CMD_RE.sub(_protect, s)

    def _repl(m: re.Match[str]) -> str:
        return rf"\text{{{m.group(0)}}}"

    s = _HANGUL_RUN_RE.sub(_repl, s)

    for idx, blk in enumerate(protected):
        s = s.replace(f"@@TEXT{idx}@@", blk)
    return s


def sanitize_latex_for_text_label(text: str) -> str:
    """Convert light LaTeX fragments into plain text for Text(...)."""
    s = str(text)
    s = _SPACING_CMD_RE.sub(" ", s)
    s = _TEXT_CMD_CAPTURE_RE.sub(r"\1", s)
    s = _GENERIC_LATEX_CMD_RE.sub("", s)
    s = s.replace("\\", "")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s
