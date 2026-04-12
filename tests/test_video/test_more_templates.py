"""Tests for NumberLinePlotTemplate and AnnotatedEquationTemplate."""

from manim_video_gen.models.solution import SolutionPlan, SolutionStep
from manim_video_gen.models.script import Segment
from manim_video_gen.video.templates.more import (
    AnnotatedEquationTemplate,
    NumberLinePlotTemplate,
)
from manim_video_gen.video.templates.registry import TemplateRegistry


def test_number_line_template_compiles():
    code = NumberLinePlotTemplate.render_code(
        params={
            "x_range": [-3, 3, 1],
            "length": 7,
            "points": [
                {"value": -1, "label": r"x=-1", "color": "RED"},
                {"value": 2, "label": "해", "color": "GREEN"},
            ],
            "regions": [{"start": -1, "end": 2, "color": "BLUE", "opacity": 0.3}],
        },
        duration=8.0,
        prev_scene_state=None,
    )
    assert "NumberLine" in code
    assert "Line(nl.n2p" in code
    compile(code, "<nl>", "exec")


def test_graph_plot_template_supports_points():
    seg = Segment(
        id=0,
        narration="그래프에서 점을 표시합니다",
        tts_text="그래프에서 점을 표시합니다",
        visual_description="desc",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**2",
            "x_range": [-3, 3, 1],
            "y_range": [-1, 9, 1],
            "points": [{"x": 1, "y": 1, "color": "RED", "label": "극소"}],
        },
        prev_scene_state=None,
    )
    code = TemplateRegistry().render_code_for_segment(
        segment=seg,
        duration=5.0,
    )
    assert "Dot(axes.c2p" in code
    compile(code, "<graph_points>", "exec")


def test_graph_plot_cjk_label_uses_sanitized_text_label():
    seg = Segment(
        id=0,
        narration="그래프에서 점을 표시합니다",
        tts_text="그래프에서 점을 표시합니다",
        visual_description="desc",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**2",
            "x_range": [-3, 3, 1],
            "y_range": [-1, 9, 1],
            "points": [
                {"x": -3, "y": 12, "color": "RED", "label": r"(-3,\\,12)\\text{ 극대}"}
            ],
        },
        prev_scene_state=None,
    )
    code = TemplateRegistry().render_code_for_segment(
        segment=seg,
        duration=5.0,
    )
    assert "Text('(-3, 12) 극대'" in code
    compile(code, "<graph_points_cjk>", "exec")


def test_equation_steps_template_compiles_after_fit_guard_injection():
    seg = Segment(
        id=11,
        narration="단계를 보여줍니다",
        tts_text="단계를 보여줍니다",
        visual_description="desc",
        visual_type="equation_steps",
        visual_params={
            "steps": [
                r"f(-3) = -27 + 54 - 27 + 12 = 12",
                r"f(-1) = -1 + 6 - 9 + 12 = 8",
            ],
            "arrange_direction": "DOWN",
        },
        prev_scene_state=None,
    )
    code = TemplateRegistry().render_code_for_segment(seg, duration=6.0)
    compile(code, "<eq_steps_fit>", "exec")


def test_annotated_equation_template_compiles():
    code = AnnotatedEquationTemplate.render_code(
        params={
            "latex": r"a x^2 + b x + c = 0",
            "annotations": [
                {
                    "target_tex": "a",
                    "text": "이차항 계수",
                    "direction": "UP",
                    "color": "YELLOW",
                },
                {
                    "target_tex": "b",
                    "text": "일차항",
                    "direction": "DOWN",
                    "color": "GREEN",
                },
            ],
        },
        duration=10.0,
        prev_scene_state=None,
    )
    assert "get_part_by_tex" in code
    assert "{{" in code or "a" in code
    compile(code, "<ann>", "exec")


def test_registry_has_new_templates():
    reg = TemplateRegistry()
    assert reg.has("number_line_plot")
    assert reg.has("annotated_equation")
    assert reg.has("visual_scene") is False


def test_solution_plan_visualization_hints_optional():
    p = SolutionPlan(
        title="t",
        steps=[
            SolutionStep(step_number=1, explanation="e"),
        ],
    )
    assert p.visualization_hints == []
    p2 = SolutionPlan(
        title="t",
        steps=[SolutionStep(step_number=1, explanation="e")],
        visualization_hints=["수직선에 해 표시"],
    )
    assert p2.visualization_hints == ["수직선에 해 표시"]
