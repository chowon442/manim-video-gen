"""Extract concise Manim / Python errors for LLM retry prompts."""

from __future__ import annotations

import re


def refine_manim_render_error(stderr_or_stdout: str, *, max_lines: int = 40) -> str:
    """
    Keep the tail of the log but prefer lines that look like tracebacks / LaTeX / Manim errors.
    """
    text = (stderr_or_stdout or "").strip()
    if not text:
        return "(empty manim output)"

    lines = text.splitlines()
    # Prefer last traceback block
    tb_start = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith("Traceback (most recent call last):"):
            tb_start = i
            break
    if tb_start is not None:
        chunk = lines[tb_start:]
        return "\n".join(chunk[-max_lines:])

    # LaTeX / common Manim errors
    keywords = re.compile(
        r"(LaTeX Error|! |Undefined control sequence|MathTex|Tex|manim\.|Exception:|Error:)",
        re.IGNORECASE,
    )
    important = [ln for ln in lines if keywords.search(ln)]
    if important:
        return "\n".join(important[-max_lines:])

    return "\n".join(lines[-max_lines:])
