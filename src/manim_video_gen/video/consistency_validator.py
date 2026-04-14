"""Narration-visual consistency validation for script segments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from manim_video_gen.models.script import Segment


_GRAPH_TOKENS = ("그래프", "좌표평면", "곡선", "포물선")
_POINT_TOKENS = ("점", "빨간 점", "붉은 점", "극대", "극소", "교점")
_NUMBER_LINE_TOKENS = ("수직선", "구간", "해", "근")
_RESULT_TOKENS = ("최종", "정답", "해는", "결과")
_DEICTIC_TOKENS = ("이 식", "여기서", "위 식", "위 결과")
_EQ_CONTEXT_TOKENS = ("함수", "정의", "두고", "놓고", "가정", "성질")
_HIGHLIGHT_EXPLAIN_TOKENS = ("핵심", "강조", "조건", "원리", "결정", "판단")
_SPOKEN_PARENTHESIS_TOKENS = (
    "괄호 열기",
    "괄호닫기",
    "괄호 닫기",
    "여는 괄호",
    "닫는 괄호",
)
_EQUATION_VISUAL_TYPES = frozenset(
    {
        "equation_write",
        "equation_transform",
        "equation_steps",
        "equation_derivation",
        "highlight_result",
        "annotated_equation",
    }
)
_PHONETIC_MATH_TOKENS = (
    "엑스",
    "와이",
    "제곱",
    "세제곱",
    "더하기",
    "빼기",
    "곱하기",
    "나누기",
    "마이너스",
    "은 영",
    "는 영",
)
_SYMBOLIC_MATH_RE = re.compile(r"[=+\-×÷^()√]|[xXyYzZ][²³^]?|[0-9]+[xXyYzZ]")


@dataclass(slots=True)
class ValidationIssue:
    severity: Literal["error", "warn"]
    code: str
    message: str
    segment_id: int


@dataclass(slots=True)
class ValidationReport:
    issues: list[ValidationIssue]

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(tok in text for tok in tokens)


def _patch_ops(seg: Segment) -> list[dict[str, object]]:
    raw = (seg.visual_params or {}).get("patch_ops")
    if not isinstance(raw, list):
        return []
    return [op for op in raw if isinstance(op, dict)]


def _contains_equation_only_graph_claim(narration: str) -> bool:
    """Graph claim that truly requires non-equation visuals.

    We intentionally avoid flagging contextual sentences like
    "이 함수를 두고 이 곡선의 성질을 본다" in equation segments.
    """
    n = narration
    if _contains_any(n, _POINT_TOKENS):
        return True
    has_graph = _contains_any(n, _GRAPH_TOKENS)
    if not has_graph:
        return False
    if _contains_any(n, _EQ_CONTEXT_TOKENS):
        return False
    return True


def _looks_overly_phonetic_math(narration: str) -> bool:
    n = narration.strip()
    if not n:
        return False
    if _SYMBOLIC_MATH_RE.search(n):
        return False
    hits = sum(1 for tok in _PHONETIC_MATH_TOKENS if tok in n)
    return hits >= 3


def _segment_issues(seg: Segment) -> list[ValidationIssue]:
    narration = (seg.narration or "").strip()
    tts_text = (seg.tts_text or "").strip()
    vt = seg.visual_type
    vp = seg.visual_params or {}
    issues: list[ValidationIssue] = []

    if _contains_any(tts_text, _SPOKEN_PARENTHESIS_TOKENS):
        issues.append(
            ValidationIssue(
                severity="error",
                code="E_TTS_SPOKEN_PARENTHESIS",
                message="tts_text contains spoken parenthesis markers (e.g. 괄호 열기/닫기); use natural spoken math phrasing",
                segment_id=seg.id,
            )
        )

    if vt == "equation_write" and _contains_equation_only_graph_claim(narration):
        issues.append(
            ValidationIssue(
                severity="error",
                code="E_EQ_WRITE_GRAPH_CLAIM",
                message="equation_write narration mentions graph/points but visual_type is equation-only",
                segment_id=seg.id,
            )
        )

    if vt == "graph_plot" and _contains_any(narration, _POINT_TOKENS):
        points = vp.get("points")
        extrema = vp.get("extrema_points")
        has_patch_points = any(
            str(op.get("op", "")).strip() == "add_point" for op in _patch_ops(seg)
        )
        if not points and not extrema and not has_patch_points:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="E_GRAPH_POINTS_MISSING",
                    message="graph narration mentions extrema/points but graph_plot has no points/extrema_points",
                    segment_id=seg.id,
                )
            )

    if vt == "number_line_plot" and not _contains_any(narration, _NUMBER_LINE_TOKENS):
        issues.append(
            ValidationIssue(
                severity="error",
                code="E_NUMBER_LINE_NARRATION_MISMATCH",
                message="number_line_plot narration does not mention roots/interval/number-line context",
                segment_id=seg.id,
            )
        )

    if vt == "equation_transform" and (
        not str(vp.get("from_latex", "")).strip()
        or not str(vp.get("to_latex", "")).strip()
    ):
        issues.append(
            ValidationIssue(
                severity="error",
                code="E_EQ_TRANSFORM_PARAMS_MISSING",
                message="equation_transform requires both from_latex and to_latex",
                segment_id=seg.id,
            )
        )

    if vt == "highlight_result" and not (
        _contains_any(narration, _RESULT_TOKENS)
        or _contains_any(narration, _HIGHLIGHT_EXPLAIN_TOKENS)
    ):
        issues.append(
            ValidationIssue(
                severity="warn",
                code="E_HIGHLIGHT_RESULT_CONTEXT_MISSING",
                message="highlight_result narration should present or emphasize final result",
                segment_id=seg.id,
            )
        )

    if vt in _EQUATION_VISUAL_TYPES and _looks_overly_phonetic_math(narration):
        issues.append(
            ValidationIssue(
                severity="warn",
                code="W_NARRATION_OVERLY_PHONETIC",
                message="equation narration appears overly phonetic; keep subtitle narration in readable symbolic math form",
                segment_id=seg.id,
            )
        )

    if _contains_any(narration, _DEICTIC_TOKENS) and not seg.prev_scene_state:
        issues.append(
            ValidationIssue(
                severity="warn",
                code="W_DEICTIC_WITHOUT_PREV_STATE",
                message="narration uses deictic reference but prev_scene_state is empty",
                segment_id=seg.id,
            )
        )

    return issues


def validate_script_consistency(segments: list[Segment]) -> ValidationReport:
    issues: list[ValidationIssue] = []
    for seg in segments:
        issues.extend(_segment_issues(seg))
    return ValidationReport(issues=issues)
