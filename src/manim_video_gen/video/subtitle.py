"""Generate ASS subtitle files for FFmpeg burn-in."""

from __future__ import annotations

import re
from pathlib import Path


_SUBSCRIPT_BRACE_RE = re.compile(r"_\{([^{}]+)\}")
_SUPERSCRIPT_BRACE_RE = re.compile(r"\^\{([^{}]+)\}")
# Latin + Greek letters (for sub/sup script pairing)
_LETTER_CLASS = "a-zA-Z\u03b1-\u03c9\u0391-\u03a9"
_SUB_DIGIT_TRANS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUP_DIGIT_TRANS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_SUP_EXTRA_TRANS = str.maketrans("+-=()n", "⁺⁻⁼⁽⁾ⁿ")
_TEXT_CMD_RE = re.compile(r"\\text\s*\{([^{}]*)\}")
_MATHRM_CMD_RE = re.compile(r"\\mathrm\s*\{([^{}]*)\}")
_FRAC_RE = re.compile(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
_SQRT_RE = re.compile(r"\\sqrt\s*\{([^{}]*)\}")
_TEX_CMD_RE = re.compile(r"\\[a-zA-Z]+")

# ASS cannot render LaTeX; map common commands to Unicode so symbols stay visible.
# Longer names first (e.g. \varepsilon before \epsilon is unnecessary here — no prefix clash).
_LATEX_CMD_TO_UNICODE: tuple[tuple[str, str], ...] = (
    (r"\varepsilon", "ε"),
    (r"\vartheta", "ϑ"),
    (r"\varsigma", "ς"),
    (r"\varphi", "φ"),
    (r"\epsilon", "ε"),
    (r"\upsilon", "υ"),
    (r"\lambda", "λ"),
    (r"\sigma", "σ"),
    (r"\omega", "ω"),
    (r"\alpha", "α"),
    (r"\beta", "β"),
    (r"\gamma", "γ"),
    (r"\delta", "δ"),
    (r"\zeta", "ζ"),
    (r"\eta", "η"),
    (r"\theta", "θ"),
    (r"\iota", "ι"),
    (r"\kappa", "κ"),
    (r"\mu", "μ"),
    (r"\nu", "ν"),
    (r"\xi", "ξ"),
    (r"\pi", "π"),
    (r"\rho", "ρ"),
    (r"\tau", "τ"),
    (r"\phi", "φ"),
    (r"\chi", "χ"),
    (r"\psi", "ψ"),
    (r"\Gamma", "Γ"),
    (r"\Delta", "Δ"),
    (r"\Theta", "Θ"),
    (r"\Lambda", "Λ"),
    (r"\Xi", "Ξ"),
    (r"\Pi", "Π"),
    (r"\Sigma", "Σ"),
    (r"\Phi", "Φ"),
    (r"\Psi", "Ψ"),
    (r"\Omega", "Ω"),
    (r"\infty", "∞"),
    (r"\cdots", "⋯"),
    (r"\ldots", "…"),
    (r"\dots", "…"),
    (r"\cdot", "·"),
    (r"\times", "×"),
    (r"\div", "÷"),
    (r"\pm", "±"),
    (r"\mp", "∓"),
    (r"\leq", "≤"),
    (r"\geq", "≥"),
    (r"\neq", "≠"),
    (r"\approx", "≈"),
    (r"\equiv", "≡"),
    (r"\in", "∈"),
    (r"\notin", "∉"),
    (r"\subset", "⊂"),
    (r"\partial", "∂"),
    (r"\nabla", "∇"),
    (r"\sum", "∑"),
    (r"\prod", "∏"),
    (r"\int", "∫"),
    (r"\angle", "∠"),
    (r"\perp", "⊥"),
    (r"\parallel", "∥"),
    (r"\degree", "°"),
    (r"\circ", "°"),
    (r"\sin", "sin"),
    (r"\cos", "cos"),
    (r"\tan", "tan"),
    (r"\cot", "cot"),
    (r"\sec", "sec"),
    (r"\csc", "csc"),
    (r"\log", "log"),
    (r"\ln", "ln"),
    (r"\exp", "exp"),
    (r"\lim", "lim"),
    (r"\max", "max"),
    (r"\min", "min"),
    (r"\sup", "sup"),
    (r"\inf", "inf"),
    (r"\det", "det"),
    (r"\gcd", "gcd"),
    (r"\quad", " "),
    (r"\qquad", "  "),
    (r"\left", ""),
    (r"\right", ""),
)


def _strip_math_delimiters(t: str) -> str:
    """Remove $ / $$ wrappers (ASS has no inline math renderer)."""
    s = t.replace("$$", "")
    return s.replace("$", "")


def _latex_fragments_to_unicode(t: str) -> str:
    """Turn common LaTeX into plain Unicode for subtitle burn-in."""
    out = _FRAC_RE.sub(r"(\1)/(\2)", t)
    out = _SQRT_RE.sub(r"√(\1)", out)
    out = _MATHRM_CMD_RE.sub(r"\1", out)
    for cmd, u in _LATEX_CMD_TO_UNICODE:
        out = out.replace(cmd, u)
    return out


def _to_subscript_digits(digits: str) -> str:
    if not digits.isdigit():
        return digits
    return digits.translate(_SUB_DIGIT_TRANS)


def _to_superscript_chunk(chunk: str) -> str:
    """Map digits and a few symbols to Unicode superscript (e.g. ^{10} -> ¹⁰)."""
    out: list[str] = []
    for ch in chunk:
        if ch in "0123456789":
            out.append(ch.translate(_SUP_DIGIT_TRANS))
        elif ch in "+-=()n":
            out.append(ch.translate(_SUP_EXTRA_TRANS))
        else:
            out.append(ch)
    return "".join(out)


def _apply_unicode_math_scripts(t: str) -> str:
    """Convert LaTeX-like sub/sup to Unicode (₀₁₂, ⁰¹²) where possible."""
    out = t

    # {x_12} -> x₁₂ (unwrap brace + single-letter subscript)
    out = re.sub(
        rf"\{{([{_LETTER_CLASS}])_([0-9]+)\}}",
        lambda m: m.group(1) + _to_subscript_digits(m.group(2)),
        out,
    )

    # _{12} -> ₁₂ (numeric subscript only)
    out = re.sub(
        r"_\{([0-9]+)\}",
        lambda m: _to_subscript_digits(m.group(1)),
        out,
    )

    # x_12 -> x₁₂ (letter + bare numeric subscript)
    out = re.sub(
        rf"([{_LETTER_CLASS}])_([0-9]+)",
        lambda m: m.group(1) + _to_subscript_digits(m.group(2)),
        out,
    )

    # ^{10}, ^{n}, etc.
    out = re.sub(
        r"\^\{([^}]+)\}",
        lambda m: _to_superscript_chunk(m.group(1))
        if re.fullmatch(r"[0-9+=()n\-]+", m.group(1))
        else "^{" + m.group(1) + "}",
        out,
    )

    # x₁^3, y^2 (letter, optional Unicode subscript digits, then ASCII caret + digits)
    out = re.sub(
        rf"([{_LETTER_CLASS}])([₀₁₂₃₄₅₆₇₈₉]*)\^([0-9]+)",
        lambda m: m.group(1) + m.group(2) + _to_superscript_chunk(m.group(3)),
        out,
    )

    # Remaining _{...} / ^{...} — readable fallback
    out = _SUBSCRIPT_BRACE_RE.sub(r"_(\1)", out)
    out = _SUPERSCRIPT_BRACE_RE.sub(r"^(\1)", out)
    return out


def _normalize_subtitle_narration(text: str) -> str:
    """Normalize LaTeX-like remnants so subtitles stay readable."""
    t = str(text)
    t = _strip_math_delimiters(t)
    t = t.replace(r"\,", " ").replace(r"\;", " ").replace(r"\:", " ")
    t = _TEXT_CMD_RE.sub(r"\1", t)
    t = _latex_fragments_to_unicode(t)
    t = _apply_unicode_math_scripts(t)
    t = _TEX_CMD_RE.sub("", t)
    t = t.replace("\\", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _ass_escape(text: str) -> str:
    """Escape characters special in ASS Dialogue lines.

    Handles braces and newlines. Backslashes in narration are stripped
    rather than escaped because they are almost always LaTeX remnants
    that should not appear on-screen.
    """
    t = _normalize_subtitle_narration(text)
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


def _wrap_narration_lines(narration: str, max_chars: int = 56) -> str:
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


def _build_ass_header(
    *,
    font_size: int,
    margin_l: int,
    margin_r: int,
    margin_v: int,
) -> str:
    return f"""[Script Info]
Title: manim-video-gen
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans KR,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def generate_ass_subtitle(
    narration: str,
    duration_seconds: float,
    output_path: Path,
    *,
    style_name: str = "Default",
    max_chars: int = 56,
    wrap_mode: str = "auto",
    font_size: int = 42,
    margin_l: int = 56,
    margin_r: int = 56,
    margin_v: int = 44,
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
    text = (
        escaped
        if str(wrap_mode).lower() == "auto"
        else _wrap_narration_lines(escaped, max_chars=max_chars)
    )

    dialogue = f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n"

    output_path.write_text(
        _build_ass_header(
            font_size=font_size,
            margin_l=margin_l,
            margin_r=margin_r,
            margin_v=margin_v,
        )
        + dialogue,
        encoding="utf-8",
    )
    return output_path


def generate_chain_ass_subtitle(
    narrations: list[str],
    durations: list[float],
    output_path: Path,
    *,
    style_name: str = "Default",
    max_chars: int = 56,
    wrap_mode: str = "auto",
    font_size: int = 42,
    margin_l: int = 56,
    margin_r: int = 56,
    margin_v: int = 44,
) -> Path:
    """
    Write an ASS file with one Dialogue per segment, timed with cumulative offsets.

    narrations[i] displays during [sum(durations[:i]), sum(durations[:i+1])).
    """
    if len(narrations) != len(durations):
        raise ValueError("narrations and durations length mismatch")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    offset = 0.0
    lines: list[str] = []
    for narration, dur in zip(narrations, durations, strict=True):
        start = _format_ass_time(offset)
        end = _format_ass_time(offset + float(dur))
        escaped = _ass_escape(narration)
        text = (
            escaped
            if str(wrap_mode).lower() == "auto"
            else _wrap_narration_lines(escaped, max_chars=max_chars)
        )
        lines.append(f"Dialogue: 0,{start},{end},{style_name},,0,0,0,,{text}\n")
        offset += float(dur)

    output_path.write_text(
        _build_ass_header(
            font_size=font_size,
            margin_l=margin_l,
            margin_r=margin_r,
            margin_v=margin_v,
        )
        + "".join(lines),
        encoding="utf-8",
    )
    return output_path
