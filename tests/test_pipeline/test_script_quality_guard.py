from __future__ import annotations

import pytest

from manim_video_gen.config import get_settings
from manim_video_gen.models.script import Segment, VideoScript
from manim_video_gen.models.solution import SolutionPlan, SolutionStep
from manim_video_gen.pipeline.orchestrator import _scriptify_with_quality_guard


def _plan() -> SolutionPlan:
    return SolutionPlan(
        title="이차방정식",
        steps=[
            SolutionStep(step_number=1, explanation="식을 확인합니다."),
            SolutionStep(step_number=2, explanation="인수분해합니다."),
        ],
    )


def _low_quality_script() -> VideoScript:
    return VideoScript(
        title="t",
        segments=[
            Segment(
                id=0,
                narration="x^2+2x+1=0을 씁니다.",
                tts_text="엑스 제곱 더하기 이엑스 더하기 일은 영을 씁니다.",
                visual_description="식 쓰기",
                visual_type="equation_write",
                visual_params={"latex": "x^2+2x+1=0"},
                prev_scene_state=None,
            ),
            Segment(
                id=1,
                narration="인수분해하면 (x+1)^2=0 입니다.",
                tts_text="인수분해하면 엑스 더하기 일의 제곱은 영입니다.",
                visual_description="변환",
                visual_type="equation_transform",
                visual_params={"from_latex": "x^2+2x+1=0", "to_latex": "(x+1)^2=0"},
                prev_scene_state=None,
            ),
            Segment(
                id=2,
                narration="해는 x=-1 입니다.",
                tts_text="해는 엑스는 마이너스 일입니다.",
                visual_description="결과 강조",
                visual_type="highlight_result",
                visual_params={"latex": "x=-1"},
                prev_scene_state=None,
            ),
        ],
    )


def _improved_script_change_two_segments() -> VideoScript:
    return VideoScript(
        title="t",
        segments=[
            Segment(
                id=0,
                narration="먼저 x^2+2x+1=0을 씁니다.",
                tts_text="먼저 엑스 제곱 더하기 이엑스 더하기 일은 영을 씁니다.",
                visual_description="식 쓰기",
                visual_type="equation_write",
                visual_params={"latex": "x^2+2x+1=0"},
                prev_scene_state=None,
            ),
            Segment(
                id=1,
                narration="인수분해하면 (x+1)^2=0 입니다.",
                tts_text="인수분해하면 엑스 더하기 일의 제곱은 영입니다.",
                visual_description="변환",
                visual_type="equation_transform",
                visual_params={"from_latex": "x^2+2x+1=0", "to_latex": "(x+1)^2=0"},
                prev_scene_state=None,
            ),
            Segment(
                id=2,
                narration="따라서 그래프에서 x=-1 지점을 빨간 점으로 확인합니다.",
                tts_text="따라서 그래프에서 엑스는 마이너스 일 지점을 빨간 점으로 확인합니다.",
                visual_description="그래프 확인",
                visual_type="graph_plot",
                visual_params={
                    "func_python": "lambda x: (x+1)**2",
                    "x_range": [-4, 2, 1],
                    "y_range": [-1, 9, 1],
                    "points": [{"x": -1, "y": 0, "color": "RED", "label": "x=-1"}],
                },
                prev_scene_state=None,
            ),
        ],
    )


class _DummyClient:
    def __init__(self, scripts: list[VideoScript]):
        self._scripts = list(scripts)
        self._idx = 0

    async def complete_json_model(self, **kwargs):
        model = kwargs["response_model"]
        if model is not VideoScript:
            raise AssertionError("This dummy only supports VideoScript responses")
        out = self._scripts[min(self._idx, len(self._scripts) - 1)]
        self._idx += 1
        return out


@pytest.mark.asyncio
async def test_quality_guard_repairs_script_when_threshold_not_met():
    client = _DummyClient(
        [_low_quality_script(), _improved_script_change_two_segments()]
    )
    settings = get_settings().model_copy(
        update={
            "script_quality_enabled": True,
            "script_quality_profile": "quality_first",
            "script_quality_min_total": 0.8,
            "script_quality_max_attempts": 1,
            "script_quality_max_segments_per_attempt": 2,
            "script_quality_fail_on_soft_after_max": False,
            "consistency_mode": "warn",
        }
    )

    script, _consistency, quality = await _scriptify_with_quality_guard(
        client=client,
        settings=settings,
        plan=_plan(),
    )

    assert quality is not None
    assert quality.total_score >= 0.8
    assert script.segments[2].visual_type == "graph_plot"


@pytest.mark.asyncio
async def test_quality_guard_rejects_candidate_changing_too_many_segments():
    client = _DummyClient(
        [_low_quality_script(), _improved_script_change_two_segments()]
    )
    settings = get_settings().model_copy(
        update={
            "script_quality_enabled": True,
            "script_quality_profile": "quality_first",
            "script_quality_min_total": 0.8,
            "script_quality_max_attempts": 1,
            "script_quality_max_segments_per_attempt": 1,
            "script_quality_fail_on_soft_after_max": False,
            "consistency_mode": "warn",
        }
    )

    script, _consistency, quality = await _scriptify_with_quality_guard(
        client=client,
        settings=settings,
        plan=_plan(),
    )

    assert quality is not None
    assert script.segments[2].visual_type == "highlight_result"
