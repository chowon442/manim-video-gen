"""Math notation normalization helpers for narration/TTS safety nets.

The LLM should ideally emit high-quality narration/tts_text already, but these
helpers catch common symbol and LaTeX leaks to improve TTS robustness.
"""

from __future__ import annotations

import re

# Order matters: longer / more specific first.
_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    # Unicode superscripts
    (re.compile(r"x²"), "엑스 제곱"),
    (re.compile(r"y²"), "와이 제곱"),
    (re.compile(r"x³"), "엑스 세제곱"),
    (re.compile(r"²"), " 제곱"),
    (re.compile(r"³"), " 세제곱"),
    # Caret superscripts
    (re.compile(r"x\^2", re.IGNORECASE), "엑스 제곱"),
    (re.compile(r"y\^2", re.IGNORECASE), "와이 제곱"),
    (re.compile(r"x\^3", re.IGNORECASE), "엑스 세제곱"),
    (re.compile(r"\^2"), " 제곱"),
    (re.compile(r"\^3"), " 세제곱"),
    # LaTeX fractions and roots
    (re.compile(r"\\frac\{([^}]+)\}\{([^}]+)\}"), r"\2분의 \1"),
    (re.compile(r"\\sqrt\{([^}]+)\}"), r"루트 \1"),
    (re.compile(r"\\sqrt\[(\d+)\]\{([^}]+)\}"), r"\2의 \1제곱근"),
    # Unicode math symbols
    (re.compile(r"√"), "루트"),
    (re.compile(r"π"), "파이"),
    (re.compile(r"∞"), "무한대"),
    (re.compile(r"±"), "플러스 마이너스"),
    (re.compile(r"≥"), "이상"),
    (re.compile(r"≤"), "이하"),
    (re.compile(r"≠"), "같지 않고"),
    # Operators in narration context
    (re.compile(r"(?<=\d)\s*\+\s*(?=\d)"), " 더하기 "),
    (re.compile(r"(?<=\d)\s*-\s*(?=\d)"), " 빼기 "),
    (re.compile(r"(?<=\d)\s*[×✕]\s*(?=\d)"), " 곱하기 "),
    (re.compile(r"(?<=\d)\s*÷\s*(?=\d)"), " 나누기 "),
    # LaTeX Greek & symbols
    (re.compile(r"\\pi"), "파이"),
    (re.compile(r"\\alpha"), "알파"),
    (re.compile(r"\\beta"), "베타"),
    (re.compile(r"\\theta"), "세타"),
    (re.compile(r"\\infty"), "무한대"),
    (re.compile(r"\\Rightarrow"), "이면"),
    (re.compile(r"\\rightarrow"), "로 가면"),
    (re.compile(r"\\times"), "곱하기"),
    (re.compile(r"\\cdot"), "곱하기"),
    (re.compile(r"\\pm"), "플러스 마이너스"),
    (re.compile(r"\\leq"), "이하"),
    (re.compile(r"\\geq"), "이상"),
    (re.compile(r"\\neq"), "같지 않고"),
    (re.compile(r"\\int"), "적분"),
    (re.compile(r"\\sum"), "시그마 합"),
    (re.compile(r"\\lim"), "극한"),
    (re.compile(r"\\det"), "행렬식"),
    (re.compile(r"\\vec\{([^}]+)\}"), r"벡터 \1"),
]

_SPOKEN_PAREN_OPEN_RE = re.compile(r"(?:괄호\s*열기|여는\s*괄호|열린\s*괄호)")
_SPOKEN_PAREN_CLOSE_RE = re.compile(r"(?:괄호\s*닫기|괄호닫기|닫는\s*괄호)")

_TTS_VAR_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![A-Za-z가-힣])x(?![A-Za-z가-힣])", re.IGNORECASE), "엑스"),
    (re.compile(r"(?<![A-Za-z가-힣])y(?![A-Za-z가-힣])", re.IGNORECASE), "와이"),
    (re.compile(r"(?<![A-Za-z가-힣])z(?![A-Za-z가-힣])", re.IGNORECASE), "제트"),
    (re.compile(r"(?<![A-Za-z가-힣])a(?![A-Za-z가-힣])", re.IGNORECASE), "에이"),
    (re.compile(r"(?<![A-Za-z가-힣])b(?![A-Za-z가-힣])", re.IGNORECASE), "비"),
    (re.compile(r"(?<![A-Za-z가-힣])m(?![A-Za-z가-힣])", re.IGNORECASE), "엠"),
    (re.compile(r"(?<![A-Za-z가-힣])n(?![A-Za-z가-힣])", re.IGNORECASE), "엔"),
]

_TTS_SYMBOL_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\+"), " 더하기 "),
    (re.compile(r"[×✕]"), " 곱하기 "),
    (re.compile(r"÷"), " 나누기 "),
    (re.compile(r"="), " 은 "),
]


def _strip_parenthesis_markers(text: str) -> str:
    out = _SPOKEN_PAREN_OPEN_RE.sub(" ", text)
    out = _SPOKEN_PAREN_CLOSE_RE.sub(" ", out)
    out = out.replace("(", " ").replace(")", " ")
    out = re.sub(r"\s+의\s+제곱", "의 제곱", out)
    return re.sub(r"\s+", " ", out).strip()


def polish_narration_math(text: str) -> str:
    """Replace common LaTeX/math fragments with Korean spoken forms for TTS.

    Safe no-op if nothing matches. Does not attempt full LaTeX parsing.
    """
    if not text:
        return text
    has_targets = (
        "\\" in text
        or "^" in text
        or "²" in text
        or "³" in text
        or "√" in text
        or "π" in text
        or "±" in text
        or "≥" in text
        or "≤" in text
        or "≠" in text
        or "∞" in text
    )
    if not has_targets:
        return text
    out = text
    for pattern, repl in _REPLACEMENTS:
        out = pattern.sub(repl, out)
    out = re.sub(r"\\[a-zA-Z]+", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def polish_tts_text(text: str) -> str:
    """Polish tts_text into more natural spoken Korean.

    Focuses on:
    - removing spoken parenthesis markers ("괄호 열기/닫기")
    - converting residual symbolic math into pronounceable Korean tokens
    - keeping a readable spoken form for TTS engines
    """
    if not text:
        return text

    out = polish_narration_math(text)
    out = _strip_parenthesis_markers(out)

    for pattern, repl in _TTS_SYMBOL_REPLACEMENTS:
        out = pattern.sub(repl, out)

    # Binary minus first, then unary minus.
    out = re.sub(r"(?<=[0-9A-Za-z가-힣])\s*-\s*(?=[0-9A-Za-z가-힣])", " 빼기 ", out)
    out = re.sub(r"(^|\s)-(?=\d)", r"\1마이너스 ", out)

    for pattern, repl in _TTS_VAR_REPLACEMENTS:
        out = pattern.sub(repl, out)

    out = re.sub(r"\s+의\s+제곱", "의 제곱", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out
