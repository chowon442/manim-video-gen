"""TemplateRegistry has() 및 render_code_for_segment() 파라미터 전달 테스트."""

import pytest

from manim_video_gen.models.script import SceneObjectState, Segment
from manim_video_gen.video.templates.registry import TemplateRegistry


def _make_segment(**kwargs) -> Segment:
    defaults = {
        "id": 0,
        "narration": "테스트 나레이션",
        "tts_text": "테스트 나레이션",
        "visual_description": "수식을 보여줌",
        "visual_type": "equation_write",
        "visual_params": {},
        "prev_scene_state": None,
    }
    defaults.update(kwargs)
    return Segment(**defaults)


class TestTemplateRegistryHas:
    def test_has_equation_write(self):
        registry = TemplateRegistry()
        assert registry.has("equation_write") is True

    def test_has_equation_transform(self):
        registry = TemplateRegistry()
        assert registry.has("equation_transform") is True

    def test_has_unknown_type(self):
        registry = TemplateRegistry()
        assert registry.has("unknown_type") is False

    def test_has_empty_string(self):
        registry = TemplateRegistry()
        assert registry.has("") is False


class TestRenderCodeForSegment:
    def test_equation_write_generates_valid_python(self):
        registry = TemplateRegistry()
        seg = _make_segment(
            visual_type="equation_write",
            visual_params={"latex": r"x^2 + 2x + 1"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert r"x^2 + 2x + 1" in code
        assert "self.play(" in code
        assert "self.wait(" in code

    def test_equation_write_respects_duration(self):
        registry = TemplateRegistry()
        seg = _make_segment(
            visual_type="equation_write",
            visual_params={"latex": r"y = mx + b"},
        )
        code = registry.render_code_for_segment(seg, duration=5.0)
        compile(code, "<test>", "exec")  # 문법 오류 없음 확인

    def test_equation_transform_without_prev_state(self):
        registry = TemplateRegistry()
        seg = _make_segment(
            visual_type="equation_transform",
            visual_params={"from_latex": r"x^2", "to_latex": r"x^2 + 1"},
        )
        code = registry.render_code_for_segment(seg, duration=4.0)
        assert "TransformMatchingTex" in code
        assert r"x^2" in code
        assert r"x^2 + 1" in code

    def test_equation_transform_with_prev_state(self):
        registry = TemplateRegistry()
        prev = [SceneObjectState(latex=r"x^2", position_expr="UP")]
        seg = _make_segment(
            visual_type="equation_transform",
            visual_params={"from_latex": r"x^2", "to_latex": r"x^2 + 1"},
            prev_scene_state=prev,
        )
        code = registry.render_code_for_segment(seg, duration=4.0)
        assert "self.add(" in code
        assert "TransformMatchingTex" in code

    def test_unknown_type_raises(self):
        registry = TemplateRegistry()
        seg = _make_segment(visual_type="unsupported_custom_viz_xyz")
        with pytest.raises(KeyError, match="Unsupported visual_type"):
            registry.render_code_for_segment(seg, duration=3.0)

    def test_has_graph_plot(self):
        registry = TemplateRegistry()
        assert registry.has("graph_plot") is True

    def test_has_equation_steps(self):
        registry = TemplateRegistry()
        assert registry.has("equation_steps") is True

    def test_params_passed_correctly(self):
        registry = TemplateRegistry()
        latex = r"\frac{1}{2}mv^2"
        seg = _make_segment(
            visual_type="equation_write",
            visual_params={"latex": latex, "font_size": 60},
        )
        code = registry.render_code_for_segment(seg, duration=2.0)
        # 생성 코드는 repr() 기반 일반 문자열이라 소스에는 \\frac 형태로 보임
        assert "MathTex(" in code and "frac{1}{2}mv^2" in code
        assert "60" in code
