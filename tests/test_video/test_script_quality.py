from manim_video_gen.models.script import Segment
from manim_video_gen.video.script_quality import evaluate_script_quality


def _seg(**kwargs) -> Segment:
    defaults = {
        "id": 0,
        "narration": "주어진 식을 먼저 확인합니다.",
        "tts_text": "주어진 식을 먼저 확인합니다.",
        "visual_description": "desc",
        "visual_type": "equation_write",
        "visual_params": {"latex": "x=1"},
        "prev_scene_state": None,
    }
    defaults.update(kwargs)
    return Segment(**defaults)


def test_quality_report_collects_hard_failures_from_consistency():
    seg = _seg(
        id=1,
        narration="이 식의 그래프를 좌표평면에 그려 봅시다.",
        visual_type="equation_write",
        visual_params={"latex": "x^2+1=0"},
    )

    report = evaluate_script_quality([seg], profile="quality_first")

    assert any(i.code == "E_EQ_WRITE_GRAPH_CLAIM" for i in report.hard_failures)
    assert 1 in report.repair_targets
    assert report.total_score < 0.8


def test_quality_report_warns_when_visual_variety_is_low():
    segs = [
        _seg(id=0, narration="먼저 x^2+2x+1=0을 씁니다."),
        _seg(
            id=1,
            narration="이어서 인수분해하면 (x+1)^2=0 입니다.",
            visual_type="equation_transform",
            visual_params={"from_latex": "x^2+2x+1=0", "to_latex": "(x+1)^2=0"},
        ),
        _seg(
            id=2,
            narration="따라서 해는 x=-1 입니다.",
            visual_type="highlight_result",
            visual_params={"latex": "x=-1"},
        ),
    ]

    report = evaluate_script_quality(segs, profile="quality_first")

    assert any(i.code == "W_VISUAL_VARIETY_LOW" for i in report.soft_issues)
