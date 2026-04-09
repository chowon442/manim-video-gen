"""Tests for NumberLinePlotTemplate and AnnotatedEquationTemplate."""

from manim_video_gen.models.solution import SolutionPlan, SolutionStep
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
