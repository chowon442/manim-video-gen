import sys
import types
from importlib.util import find_spec

if find_spec("replicate") is None:
    _replicate_mod = types.ModuleType("replicate")
    _replicate_mod.Client = object  # type: ignore[attr-defined]
    _replicate_exc_mod = types.ModuleType("replicate.exceptions")

    class _ReplicateError(Exception):
        pass

    _replicate_exc_mod.ReplicateError = _ReplicateError  # type: ignore[attr-defined]
    sys.modules["replicate"] = _replicate_mod
    sys.modules["replicate.exceptions"] = _replicate_exc_mod

from manim_video_gen.models.script import Segment, VideoScript
from manim_video_gen.pipeline.orchestrator import (
    split_segment_for_transition_tail,
    split_script_transition_tails,
)


def _seg(**kwargs) -> Segment:
    base = {
        "id": 8,
        "narration": "세 근은 ... 이제 그래프로 확인해 봅시다.",
        "tts_text": "세 근은 ... 이제 그래프로 확인해 봅시다.",
        "visual_description": "곡선과 직선을 함께 그리고 교점을 표시",
        "visual_type": "graph_plot",
        "visual_params": {
            "func_python": "lambda x: x**3 + 1",
            "x_range": [-3, 3, 1],
            "y_range": [-5, 5, 1],
            "line_python": "lambda x: -2*x + 6",
            "points": [{"x": 0, "y": 1, "color": "GREEN", "label": "(0,1)"}],
        },
        "prev_scene_state": None,
    }
    base.update(kwargs)
    return Segment(**base)


def test_split_transition_tail_for_graph_plot():
    s = _seg(
        narration="세 근은 x=-1,-2,-3 입니다. 따라서 세 점에서 만납니다. 이제 그래프로 확인해 봅시다.",
        tts_text="세 근은 엑스는 마이너스 일, 이, 삼 입니다. 따라서 세 점에서 만납니다. 이제 그래프로 확인해 봅시다.",
    )
    out = split_segment_for_transition_tail(s)
    assert len(out) == 2
    lead, tail = out
    assert lead.visual_type == "highlight_result"
    assert "이제 그래프로" not in lead.narration
    assert tail.visual_type == "graph_plot"
    assert tail.narration.startswith("이제 그래프로")


def test_no_split_without_transition_phrase():
    s = _seg(narration="세 교점을 그래프로 확인합니다.")
    out = split_segment_for_transition_tail(s)
    assert len(out) == 1
    assert out[0].visual_type == "graph_plot"


def test_split_script_transition_tails_repolishes_tts_text():
    src = Segment(
        id=0,
        narration="근은 하나입니다. 이제 그래프로 확인해 봅시다.",
        tts_text="근은 하나입니다. 이제 그래프로 확인해 봅시다.",
        visual_description="그래프 장면",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**2",
            "x_range": [-3, 3, 1],
            "y_range": [-1, 9, 1],
        },
        prev_scene_state=None,
    )
    script = VideoScript(title="t", segments=[src])
    out = split_script_transition_tails(script)
    assert len(out.segments) == 2
    for seg in out.segments:
        assert seg.tts_text.strip()


def test_split_tail_replaces_spoken_parenthesis_in_tts_text():
    src = Segment(
        id=0,
        narration="식을 정리하면 (x+3)^2 = 0입니다. 이제 그래프로 확인해 봅시다.",
        tts_text="식을 정리하면 괄호 열기 엑스 더하기 삼 괄호 닫기 의 제곱은 영입니다. 이제 그래프로 확인해 봅시다.",
        visual_description="그래프 장면",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**2",
            "x_range": [-3, 3, 1],
            "y_range": [-1, 9, 1],
        },
        prev_scene_state=None,
    )
    out = split_script_transition_tails(VideoScript(title="t", segments=[src]))
    assert len(out.segments) == 2
    assert "괄호" not in out.segments[0].tts_text
