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


class TestDomainTemplates:
    @pytest.mark.parametrize(
        "visual_type",
        ["short_domain_icon", "short_stat_chart", "short_flow_arrow"],
    )
    def test_domain_template_registered(self, visual_type):
        registry = ShortTemplateRegistry()
        assert registry.has(visual_type) is True

    def test_short_stat_chart_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_stat_chart",
            visual_params={"values": [10, 20, 30], "labels": ["A", "B", "C"]},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code

    @pytest.mark.parametrize(
        "visual_type",
        ["short_domain_icon", "short_stat_chart", "short_flow_arrow"],
    )
    def test_domain_template_syntax_valid(self, visual_type):
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        ast.parse(code)


class TestAllTemplatesRegistered:
    """Verify all 14 templates are registered."""

    ALL_TYPES = [
        # Beat (5)
        "short_hook", "short_before", "short_after", "short_payoff_card", "short_cta",
        # Concept (6)
        "short_concept_equation", "short_concept_graph", "short_concept_number_line",
        "short_concept_annotated", "short_concept_compare", "short_concept_pattern",
        # Domain (3)
        "short_domain_icon", "short_stat_chart", "short_flow_arrow",
    ]

    def test_all_templates_registered(self):
        registry = ShortTemplateRegistry()
        for vt in self.ALL_TYPES:
            assert registry.has(vt) is True, f"Missing template: {vt}"

    def test_total_count(self):
        registry = ShortTemplateRegistry()
        registered = sum(1 for vt in self.ALL_TYPES if registry.has(vt))
        assert registered == 14

    def test_unknown_type_returns_false(self):
        registry = ShortTemplateRegistry()
        assert registry.has("unknown_type_xyz") is False

    @pytest.mark.parametrize("visual_type", ALL_TYPES)
    def test_template_generates_valid_python(self, visual_type):
        """All templates should generate syntactically valid Python."""
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "def construct(self):" in code
        ast.parse(code)


class TestSafeZoneCompliance:
    """Verify all templates respect 9:16 safe zone."""

    ALL_TYPES = [
        "short_hook", "short_before", "short_after", "short_payoff_card", "short_cta",
        "short_concept_equation", "short_concept_graph", "short_concept_number_line",
        "short_concept_annotated", "short_concept_compare", "short_concept_pattern",
        "short_domain_icon", "short_stat_chart", "short_flow_arrow",
    ]

    @pytest.mark.parametrize("visual_type", ALL_TYPES)
    def test_template_sets_9_16_frame(self, visual_type):
        """All templates should set 9:16 frame dimensions."""
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        # Should set frame dimensions for 9:16
        assert "19.2" in code or "10.8" in code

    @pytest.mark.parametrize("visual_type", ALL_TYPES)
    def test_template_uses_safe_zone_y_offset(self, visual_type):
        """All templates should use safe zone Y offset to avoid headline/subtitle areas."""
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        # Should use safe zone Y offset (not just ORIGIN)
        assert "move_to" in code


class TestLayoutHelpers:
    """Test _layout.py helper functions."""

    def test_safe_zone_y_offset_returns_float(self):
        from manim_video_gen.video.templates.short._layout import safe_zone_y_offset
        offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)
        assert isinstance(offset, float)

    def test_safe_zone_y_offset_content_center(self):
        from manim_video_gen.video.templates.short._layout import (
            CONTENT_ZONE_BOTTOM,
            CONTENT_ZONE_TOP,
            safe_zone_y_offset,
        )
        offset = safe_zone_y_offset(has_headline=True, has_subtitle=True)
        expected = (CONTENT_ZONE_TOP + CONTENT_ZONE_BOTTOM) / 2
        assert abs(offset - expected) < 0.001

    def test_scale_to_fit_frame_returns_code(self):
        from manim_video_gen.video.templates.short._layout import scale_to_fit_frame
        code = scale_to_fit_frame("eq")
        assert "scale_to_fit_width" in code
        assert "eq.width" in code
