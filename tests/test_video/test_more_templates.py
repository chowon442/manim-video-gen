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


def test_graph_plot_patch_ops_add_curve_and_point_compiles():
    seg = Segment(
        id=0,
        narration="곡선과 직선을 함께 그리고 점을 표시합니다",
        tts_text="곡선과 직선을 함께 그리고 점을 표시합니다",
        visual_description="desc",
        visual_type="graph_plot",
        visual_params={
            "func_python": "lambda x: x**2",
            "x_range": [-3, 3, 1],
            "y_range": [-2, 9, 1],
            "patch_ops": [
                {
                    "op": "add_curve",
                    "func_python": "lambda x: -2*x + 1",
                    "color": "GREEN",
                    "label": "y=-2x+1",
                },
                {
                    "op": "add_point",
                    "x": 0.5,
                    "y": 0.25,
                    "color": "YELLOW",
                    "label": "보조점",
                },
            ],
        },
        prev_scene_state=None,
    )
    code = TemplateRegistry().render_code_for_segment(
        segment=seg,
        duration=5.0,
    )
    assert "graph_extra_0 = axes.plot(" in code
    assert "Dot(axes.c2p(0.5, 0.25)" in code
    compile(code, "<graph_patch_ops>", "exec")


def test_number_line_plot_cjk_label_uses_sanitized_text_label():
    code = NumberLinePlotTemplate.render_code(
        params={
            "x_range": [-3, 3, 1],
            "length": 7,
            "points": [
                {"value": 2, "label": r"(-3,\,12)\text{ 극대}", "color": "GREEN"},
            ],
        },
        duration=5.0,
        prev_scene_state=None,
    )
    assert "Text('(-3, 12) 극대'" in code
    assert "MathTex('(-3,\\,12)\\text{ 극대}'" not in code
    compile(code, "<number_line_cjk>", "exec")


def test_number_line_patch_ops_add_point_and_region_compiles():
    code = NumberLinePlotTemplate.render_code(
        params={
            "x_range": [-3, 3, 1],
            "length": 7,
            "patch_ops": [
                {
                    "op": "add_region",
                    "start": -2,
                    "end": 1,
                    "color": "TEAL",
                    "opacity": 0.2,
                },
                {
                    "op": "add_point",
                    "value": 1,
                    "label": "해",
                    "color": "GREEN",
                },
            ],
        },
        duration=6.0,
        prev_scene_state=None,
    )
    assert "Line(nl.n2p(-2.0), nl.n2p(1.0)" in code
    assert "Dot(nl.n2p(1.0), color=GREEN" in code
    compile(code, "<number_line_patch_ops>", "exec")


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


def test_annotated_equation_template_guards_missing_target_tex():
    code = AnnotatedEquationTemplate.render_code(
        params={
            "latex": r"\\det({{H}}) = (2)(4) - (1)^2 = {{7}} > 0",
            "annotations": [
                {
                    "target_tex": "H",
                    "text": "양의 정부호 (Positive Definite)",
                    "direction": "UP",
                },
                {
                    "target_tex": "7",
                    "text": "엄격한 볼록 함수",
                    "direction": "DOWN",
                },
            ],
        },
        duration=8.0,
        prev_scene_state=None,
    )
    assert "part_0 = eq.get_part_by_tex('H')" in code
    assert "if part_0 is not None:" in code
    assert "part_1 = eq.get_part_by_tex('7')" in code
    assert "if part_1 is not None:" in code
    compile(code, "<ann_guard>", "exec")


def test_annotated_equation_patch_ops_add_annotation_compiles():
    code = AnnotatedEquationTemplate.render_code(
        params={
            "latex": r"a x^2 + b x + c = 0",
            "annotations": [],
            "patch_ops": [
                {
                    "op": "add_annotation",
                    "target_tex": "b",
                    "text": "일차항",
                    "direction": "UP",
                    "color": "GREEN",
                }
            ],
        },
        duration=6.0,
        prev_scene_state=None,
    )
    assert "get_part_by_tex('b')" in code
    compile(code, "<ann_patch_ops>", "exec")


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
