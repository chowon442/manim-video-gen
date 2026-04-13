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


def test_tts_text_with_spoken_parenthesis_markers_is_error():
    s = _seg(
        id=51,
        visual_type="equation_transform",
        visual_params={"from_latex": "x^2+6x+9=0", "to_latex": "(x+3)^2=0"},
        narration="식을 정리하면 (x+3)^2 = 0이 됩니다.",
        tts_text="식을 정리하면 괄호 열기 엑스 더하기 삼 괄호 닫기 의 제곱은 영이 됩니다.",
    )
    r = validate_script_consistency([s])
    assert any(
        i.code == "E_TTS_SPOKEN_PARENTHESIS" and i.severity == "error"
        for i in r.issues
    )


def test_equation_narration_overly_phonetic_emits_warn():
    s = _seg(
        id=52,
        visual_type="equation_write",
        visual_params={"latex": "x^3 + 6x^2 + 11x + 6 = 0"},
        narration="삼차 방정식 엑스 세제곱 더하기 육엑스 제곱 더하기 십일엑스 더하기 육은 영입니다.",
    )
    r = validate_script_consistency([s])
    assert any(
        i.code == "W_NARRATION_OVERLY_PHONETIC" and i.severity == "warn"
        for i in r.issues
    )
