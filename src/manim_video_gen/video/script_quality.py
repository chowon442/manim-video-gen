"""Script-level quality scoring and repair targeting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from manim_video_gen.models.script import Segment
from manim_video_gen.video.consistency_validator import validate_script_consistency

QualityProfile = Literal["quality_first", "balanced", "stable"]

_EQUATION_TYPES = frozenset(
    {
        "equation_write",
        "equation_transform",
        "equation_steps",
        "equation_derivation",
        "highlight_result",
        "annotated_equation",
    }
)
_CONNECTOR_TOKENS = (
    "이어서",
    "다음으로",
    "그러면",
    "따라서",
    "즉",
    "이 식에서",
    "위 결과를",
)
_CLOSING_TOKENS = (
    "정리",
    "따라서",
    "결론",
    "해는",
    "최종",
)


@dataclass(slots=True)
class ScriptQualityIssue:
    severity: Literal["error", "warn"]
    code: str
    message: str
    segment_id: int


@dataclass(slots=True)
class ScriptQualityReport:
    profile: QualityProfile
    total_score: float
    dimensions: dict[str, float]
    hard_failures: list[ScriptQualityIssue]
    soft_issues: list[ScriptQualityIssue]
    repair_targets: list[int]

    @property
    def has_hard_failures(self) -> bool:
        return bool(self.hard_failures)


def _clip01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _flow_dimension(segments: list[Segment]) -> float:
    if not segments:
        return 0.0
    if len(segments) == 1:
        return 1.0

    tail = segments[1:]
    with_connector = sum(
        1
        for seg in tail
        if any(tok in (seg.narration or "") for tok in _CONNECTOR_TOKENS)
    )
    last = segments[-1].narration or ""
    has_closing = any(tok in last for tok in _CLOSING_TOKENS)
    connector_ratio = with_connector / float(len(tail))
    return _clip01(0.8 * connector_ratio + (0.2 if has_closing else 0.0))


def _pedagogy_dimension(segments: list[Segment]) -> float:
    if not segments:
        return 0.0
    lengths = [len((s.narration or "").strip()) for s in segments]
    non_empty = sum(1 for ln in lengths if ln >= 8)
    return _clip01(non_empty / float(len(segments)))


def _visual_variety_dimension(segments: list[Segment]) -> tuple[float, bool]:
    if not segments:
        return 0.0, False

    uniq_types = {s.visual_type for s in segments}
    non_eq_count = sum(1 for s in segments if s.visual_type not in _EQUATION_TYPES)
    total = len(segments)

    uniq_component = min(1.0, len(uniq_types) / max(2.0, total / 2.0))
    non_eq_component = non_eq_count / float(total)
    score = _clip01(0.55 * uniq_component + 0.45 * non_eq_component)

    low = total >= 3 and non_eq_count == 0
    return score, low


def _renderability_dimension(
    hard_count: int,
    warn_count: int,
) -> float:
    return _clip01(1.0 - 0.35 * float(hard_count) - 0.06 * float(warn_count))


def _weights(profile: QualityProfile) -> dict[str, float]:
    if profile == "quality_first":
        return {
            "flow": 0.35,
            "pedagogy": 0.30,
            "visual_variety": 0.20,
            "renderability": 0.15,
        }
    if profile == "stable":
        return {
            "flow": 0.20,
            "pedagogy": 0.20,
            "visual_variety": 0.15,
            "renderability": 0.45,
        }
    return {
        "flow": 0.25,
        "pedagogy": 0.25,
        "visual_variety": 0.20,
        "renderability": 0.30,
    }


def evaluate_script_quality(
    segments: list[Segment],
    *,
    profile: QualityProfile = "balanced",
) -> ScriptQualityReport:
    consistency = validate_script_consistency(segments)
    hard_failures = [
        ScriptQualityIssue(
            severity="error",
            code=i.code,
            message=i.message,
            segment_id=i.segment_id,
        )
        for i in consistency.issues
        if i.severity == "error"
    ]
    soft_issues = [
        ScriptQualityIssue(
            severity="warn",
            code=i.code,
            message=i.message,
            segment_id=i.segment_id,
        )
        for i in consistency.issues
        if i.severity != "error"
    ]

    flow = _flow_dimension(segments)
    pedagogy = _pedagogy_dimension(segments)
    visual_variety, visual_variety_low = _visual_variety_dimension(segments)
    renderability = _renderability_dimension(len(hard_failures), len(soft_issues))

    if visual_variety_low:
        soft_issues.append(
            ScriptQualityIssue(
                severity="warn",
                code="W_VISUAL_VARIETY_LOW",
                message=(
                    "script is equation-only across multiple segments; add at least one "
                    "non-equation visual segment when math content supports it"
                ),
                segment_id=segments[0].id if segments else -1,
            )
        )

    dims = {
        "flow": flow,
        "pedagogy": pedagogy,
        "visual_variety": visual_variety,
        "renderability": renderability,
    }

    w = _weights(profile)
    total = _clip01(sum(dims[k] * w[k] for k in dims))

    target_ids = {
        i.segment_id for i in hard_failures + soft_issues if i.segment_id >= 0
    }
    repair_targets = sorted(target_ids)

    return ScriptQualityReport(
        profile=profile,
        total_score=total,
        dimensions=dims,
        hard_failures=hard_failures,
        soft_issues=soft_issues,
        repair_targets=repair_targets,
    )
