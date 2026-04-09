"""Generate ASS subtitle files for FFmpeg burn-in."""

from __future__ import annotations

from pathlib import Path


def _ass_escape(text: str) -> str:
    """Escape characters special in ASS Dialogue lines.

    Handles braces and newlines. Backslashes in narration are stripped
    rather than escaped because they are almost always LaTeX remnants
    that should not appear on-screen.
    """
    t = text.replace("\\", "")
    t = t.replace("{", "\\{").replace("}", "\\}")
    t = t.replace("\n", " ")
    return t


def _format_ass_time(seconds: float) -> str:
    """H:MM:SS.cs for ASS (centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    whole = int(s)
    cs = int(round((s - whole) * 100))
    if cs >= 100:
        whole += 1
        cs = 0
    return f"{h}:{m:02d}:{whole:02d}.{cs:02d}"


def _wrap_narration_lines(narration: str, max_chars: int = 42) -> str:
    """Insert ASS line breaks for long narration."""
    s = narration.strip()
    if len(s) <= max_chars:
        return s
    parts: list[str] = []
    while s:
        chunk = s[:max_chars]
        break_idx = chunk.rfind(" ")
        if break_idx > max_chars // 2:
            chunk = s[:break_idx]
            s = s[break_idx:].lstrip()
        else:
            s = s[max_chars:]
        parts.append(chunk)
    return "\\N".join(parts)


_ASS_HEADER = """[Script Info]
Title: manim-video-gen
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans KR,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def generate_ass_subtitle(
    narration: str,
    duration_seconds: float,
    output_path: Path,
    *,
    style_name: str = "Default",
) -> Path:
    """
    Write an ASS file with one Dialogue covering [0, duration_seconds].

    Bottom-center alignment is set in the Default style (Alignment=2).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start = _format_ass_time(0.0)
    end = _format_ass_time(float(duration_seconds))
    escaped = _ass_escape(narration)
    text = _wrap_narration_lines(escaped)

    dialogue = (
        f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"
    )

    output_path.write_text(_ASS_HEADER + dialogue, encoding="utf-8")
    return output_path
