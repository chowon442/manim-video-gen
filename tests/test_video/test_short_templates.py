"""ShortTemplateRegistry has/get interface tests."""

import pytest

from manim_video_gen.video.templates.short.short_registry import ShortTemplateRegistry


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
