"""Settings default-value regression tests."""

from manim_video_gen.config import Settings


def test_transition_defaults_prefer_simple_non_bridge_flow(monkeypatch):
    monkeypatch.setenv("MANIM_VIDEO_GEN_CROSSFADE_DURATION", "0.20")
    monkeypatch.setenv("MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED", "false")
    s = Settings()
    assert s.crossfade_duration == 0.2
    assert s.scene_bridge_enabled is False
