"""Settings default-value regression tests."""

from manim_video_gen.config import Settings


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


def test_dialogue_qa_defaults(monkeypatch):
    monkeypatch.delenv("MANIM_VIDEO_GEN_DIALOGUE_QA_ENABLED", raising=False)
    monkeypatch.delenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_SPEAKER", raising=False)
    monkeypatch.delenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_LANGUAGE", raising=False)
    monkeypatch.delenv("MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_STYLE", raising=False)
    monkeypatch.delenv("MANIM_VIDEO_GEN_INWORLD_STUDENT_TTS_VOICE", raising=False)
    s = Settings()
    assert s.dialogue_qa_enabled is False
    assert s.replicate_student_tts_speaker == ""
    assert s.replicate_student_tts_language == ""
    assert s.replicate_student_tts_style_instruction == ""
    assert s.inworld_student_tts_voice_id == ""
