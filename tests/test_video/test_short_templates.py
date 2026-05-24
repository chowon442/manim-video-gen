"""ShortTemplateRegistry has/get interface tests."""

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
