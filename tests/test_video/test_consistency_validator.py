from manim_video_gen.models.script import Segment
from manim_video_gen.video.consistency_validator import validate_script_consistency


def _seg(**kwargs) -> Segment:
    defaults = {
        "id": 0,
        "narration": "기본 나레이션",
        "tts_text": "기본 나레이션",
        "visual_description": "desc",
        "visual_type": "equation_write",
        "visual_params": {"latex": "x=1"},
        "prev_scene_state": None,
    }
    defaults.update(kwargs)
    return Segment(**defaults)


def test_graph_plot_claims_extrema_without_points_is_error():
    s = _seg(
        id=1,
        visual_type="graph_plot",
        visual_params={"func_python": "lambda x: x**3"},
        narration="그래프에서 극대와 극소를 빨간 점으로 표시합니다.",
    )
    r = validate_script_consistency([s])
    assert r.has_errors is True
    assert any(i.code == "E_GRAPH_POINTS_MISSING" for i in r.issues)


def test_graph_plot_with_points_passes_point_rule():
    s = _seg(
        id=2,
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**3",
            "points": [{"x": -1, "y": 2, "color": "RED", "label": "극대"}],
        },
        narration="그래프에서 극대와 극소를 빨간 점으로 표시합니다.",
    )
    r = validate_script_consistency([s])
    assert not any(i.code == "E_GRAPH_POINTS_MISSING" for i in r.issues)


def test_equation_write_mentions_graph_is_error():
    s = _seg(
        id=3,
        visual_type="equation_write",
        visual_params={"latex": "x^2+1=0"},
        narration="이 식의 그래프를 좌표평면에 그려봅시다.",
    )
    r = validate_script_consistency([s])
    assert r.has_errors
    assert any(i.code == "E_EQ_WRITE_GRAPH_CLAIM" for i in r.issues)


def test_equation_write_contextual_curve_word_is_not_error():
    s = _seg(
        id=31,
        visual_type="equation_write",
        visual_params={"latex": "f(x)=x^3+1"},
        narration="주어진 함수를 f(x)=x^3+1로 두고 이 곡선의 성질을 봅시다.",
    )
    r = validate_script_consistency([s])
    assert not any(i.code == "E_EQ_WRITE_GRAPH_CLAIM" for i in r.issues)


def test_deictic_without_prev_state_is_warn():
    s = _seg(
        id=4,
        visual_type="equation_transform",
        visual_params={"from_latex": "x=1", "to_latex": "x-1=0"},
        narration="이 식에서 1을 이항합니다.",
        prev_scene_state=None,
    )
    r = validate_script_consistency([s])
    assert any(i.code == "W_DEICTIC_WITHOUT_PREV_STATE" for i in r.issues)


def test_highlight_result_explanatory_narration_is_warn_not_error():
    s = _seg(
        id=41,
        visual_type="highlight_result",
        visual_params={"latex": r"y=c,\;8<c<12"},
        narration="핵심 원리를 강조합니다. 이 조건이 교점 개수를 결정합니다.",
    )
    r = validate_script_consistency([s])
    assert not any(i.code == "E_HIGHLIGHT_RESULT_CONTEXT_MISSING" for i in r.issues)


def test_highlight_result_unrelated_narration_emits_warn_issue():
    s = _seg(
        id=42,
        visual_type="highlight_result",
        visual_params={"latex": r"y=c,\;8<c<12"},
        narration="이제 다음 장면으로 넘어갑니다.",
    )
    r = validate_script_consistency([s])
    assert any(
        i.code == "E_HIGHLIGHT_RESULT_CONTEXT_MISSING" and i.severity == "warn"
        for i in r.issues
    )
