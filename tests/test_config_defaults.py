"""Settings default-value regression tests."""

from manim_video_gen.config import Settings, VideoFormatProfile


def test_transition_defaults_prefer_simple_non_bridge_flow(monkeypatch):
    monkeypatch.setenv("MANIM_VIDEO_GEN_CROSSFADE_DURATION", "0.20")
    monkeypatch.setenv("MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED", "false")
    monkeypatch.setenv("MANIM_VIDEO_GEN_INTER_SCENE_GAP_SECONDS", "0")
    s = Settings()
    assert s.crossfade_duration == 0.2
    assert s.scene_bridge_enabled is False
    assert s.inter_scene_gap_seconds == 0.0


def test_script_quality_guard_defaults(monkeypatch):
    monkeypatch.delenv("MANIM_VIDEO_GEN_SCRIPT_QUALITY_ENABLED", raising=False)
    monkeypatch.delenv("MANIM_VIDEO_GEN_SCRIPT_QUALITY_PROFILE", raising=False)
    monkeypatch.delenv("MANIM_VIDEO_GEN_SCRIPT_QUALITY_MIN_TOTAL", raising=False)
    s = Settings()
    assert s.script_quality_enabled is False
    assert s.script_quality_profile == "quality_first"
    assert s.script_quality_min_total == 0.82


def test_video_format_profile_enum_values():
    assert VideoFormatProfile.LANDSCAPE.value == "landscape"
    assert VideoFormatProfile.SHORT_9_16.value == "short_9_16"


def test_video_format_profile_landscape_resolution():
    profile = VideoFormatProfile.LANDSCAPE
    assert profile.width == 1920
    assert profile.height == 1080
    assert profile.safe_zone_top_pct == 0.0
    assert profile.safe_zone_bottom_pct == 0.0


def test_video_format_profile_short_9_16_resolution():
    profile = VideoFormatProfile.SHORT_9_16
    assert profile.width == 1080
    assert profile.height == 1920
    assert profile.safe_zone_top_pct == 0.12
    assert profile.safe_zone_bottom_pct == 0.20


def test_settings_default_format_profile_is_landscape():
    s = Settings()
    assert s.format_profile == VideoFormatProfile.LANDSCAPE


def test_settings_format_profile_from_env(monkeypatch):
    monkeypatch.setenv("MANIM_VIDEO_GEN_FORMAT_PROFILE", "short_9_16")
    s = Settings()
    assert s.format_profile == VideoFormatProfile.SHORT_9_16
