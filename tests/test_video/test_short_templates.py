"""ShortTemplateRegistry has/get interface tests."""

import ast

import pytest

from manim_video_gen.models.script import Segment
from manim_video_gen.video.templates.short.short_registry import ShortTemplateRegistry


def _make_segment(**kwargs) -> Segment:
    defaults = {
        "id": 0,
        "narration": "테스트 나레이션",
        "tts_text": "테스트 나레이션",
        "visual_description": "시각적 설명",
        "visual_type": "short_hook",
        "visual_params": {},
        "prev_scene_state": None,
    }
    defaults.update(kwargs)
    return Segment(**defaults)


class TestShortTemplateRegistryHas:
    def test_has_short_concept_equation(self):
        registry = ShortTemplateRegistry()
        assert registry.has("short_concept_equation") is True

    def test_has_nonexistent(self):
        registry = ShortTemplateRegistry()
        assert registry.has("nonexistent") is False

    def test_has_empty_string(self):
        registry = ShortTemplateRegistry()
        assert registry.has("") is False


class TestBeatTemplates:
    @pytest.mark.parametrize(
        "visual_type",
        ["short_hook", "short_before", "short_after", "short_payoff_card", "short_cta"],
    )
    def test_beat_template_registered(self, visual_type):
        registry = ShortTemplateRegistry()
        assert registry.has(visual_type) is True

    def test_short_hook_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type="short_hook", visual_params={"headline": "흥미로운 시작"})
        code = registry.render_code_for_segment(seg, duration=2.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "흥미로운 시작" in code


class TestConceptTemplates:
    @pytest.mark.parametrize(
        "visual_type",
        [
            "short_concept_equation",
            "short_concept_graph",
            "short_concept_number_line",
            "short_concept_annotated",
            "short_concept_compare",
            "short_concept_pattern",
        ],
    )
    def test_concept_template_registered(self, visual_type):
        registry = ShortTemplateRegistry()
        assert registry.has(visual_type) is True

    def test_short_concept_equation_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_equation",
            visual_params={"latex": r"E = mc^2"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "E = mc^2" in code
        assert "MathTex" in code

    def test_short_concept_graph_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_graph",
            visual_params={"func": "lambda x: x**2"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "Axes" in code
        assert "lambda x: x**2" in code

    def test_short_concept_number_line_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_number_line",
            visual_params={"value": 3, "label": "π"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "NumberLine" in code
        assert "π" in code

    def test_short_concept_annotated_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_annotated",
            visual_params={"latex": r"a^2 + b^2 = c^2", "annotation": "피타고라스"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "a^2 + b^2 = c^2" in code
        assert "피타고라스" in code

    def test_short_concept_compare_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_compare",
            visual_params={"left": "수학", "right": "과학"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "수학" in code
        assert "과학" in code

    def test_short_concept_pattern_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_pattern",
            visual_params={"items": ["A", "B", "C"]},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "A" in code
        assert "B" in code

    @pytest.mark.parametrize(
        "visual_type",
        [
            "short_concept_equation",
            "short_concept_graph",
            "short_concept_number_line",
            "short_concept_annotated",
            "short_concept_compare",
            "short_concept_pattern",
        ],
    )
    def test_concept_template_syntax_valid(self, visual_type):
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        ast.parse(code)
