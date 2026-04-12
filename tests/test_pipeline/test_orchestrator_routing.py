from manim_video_gen.models.script import Segment
from manim_video_gen.pipeline.orchestrator import _requires_custom_scene


def _seg(*, narration: str, visual_type: str, visual_params: dict) -> Segment:
    return Segment(
        id=0,
        narration=narration,
        tts_text=narration,
        visual_description="desc",
        visual_type=visual_type,
        visual_params=visual_params,
        prev_scene_state=None,
    )


def test_graph_plot_curve_and_line_claim_requires_custom_scene():
    seg = _seg(
        narration="직선 y=-2x+6을 곡선과 함께 그리겠습니다.",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**3 + 6*x**2 + 9*x + 12",
        },
    )
    assert _requires_custom_scene(seg) is True


def test_graph_plot_single_curve_stays_template():
    seg = _seg(
        narration="곡선 그래프를 그립니다.",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**2",
            "points": [{"x": 0, "y": 0, "color": "RED"}],
        },
    )
    assert _requires_custom_scene(seg) is False
