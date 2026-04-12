from manim_video_gen.models.script import Segment
from manim_video_gen.pipeline.orchestrator import split_segment_for_transition_tail


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
