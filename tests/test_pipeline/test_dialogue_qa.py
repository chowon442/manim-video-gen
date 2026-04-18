from __future__ import annotations

import sys
import types
from importlib.util import find_spec

import pytest

if find_spec("replicate") is None:
    _replicate_mod = types.ModuleType("replicate")
    _replicate_mod.Client = object  # type: ignore[attr-defined]
    _replicate_exc_mod = types.ModuleType("replicate.exceptions")

    class _ReplicateError(Exception):
        pass

    _replicate_exc_mod.ReplicateError = _ReplicateError  # type: ignore[attr-defined]
    sys.modules["replicate"] = _replicate_mod
    sys.modules["replicate.exceptions"] = _replicate_exc_mod

from manim_video_gen.config import get_settings
from manim_video_gen.models.script import Segment, VideoScript
from manim_video_gen.pipeline.orchestrator import (
    _apply_dialogue_prefix_rules,
    _dialogue_question_count_target,
    _dialogue_rewrite_slot_windows,
    _normalize_dialogue_script,
    _validate_dialogue_mode_settings,
)


def _base_script(n: int = 6) -> VideoScript:
    return VideoScript(
        title="t",
        segments=[
            Segment(
                id=i,
                narration=f"설명 {i}",
                tts_text=f"설명 {i}",
                visual_description="desc",
                visual_type="equation_write",
                visual_params={"latex": f"x+{i}=0"},
                prev_scene_state=None,
            )
            for i in range(n)
        ],
    )


def test_dialogue_question_count_target() -> None:
    assert _dialogue_question_count_target(4) == 1
    assert _dialogue_question_count_target(5) == 2


def test_dialogue_slot_windows_for_one_question() -> None:
    out = _dialogue_rewrite_slot_windows(segment_count=4, question_count=1)
    assert out == [(0.45, 0.55)]


def test_dialogue_slot_windows_for_two_questions() -> None:
    out = _dialogue_rewrite_slot_windows(segment_count=8, question_count=2)
    assert out == [(0.25, 0.35), (0.65, 0.75)]


def test_apply_dialogue_prefix_rules_question_only() -> None:
    script = _base_script(3)
    script.segments[0] = script.segments[0].model_copy(
        update={"narration": "질문입니다", "tts_text": "질문입니다", "speaker": "student", "turn": "question"}
    )
    script.segments[1] = script.segments[1].model_copy(
        update={"speaker": "teacher", "turn": "answer"}
    )
    out = _apply_dialogue_prefix_rules(script)
    assert out.segments[0].narration.startswith("[질문] ")
    assert not out.segments[0].tts_text.startswith("[질문]")
    assert not out.segments[1].narration.startswith("[질문]")


def test_normalize_dialogue_script_reindexes_and_prefixes() -> None:
    script = VideoScript(
        title="t",
        segments=[
            Segment(
                id=10,
                narration="질문",
                tts_text="질문",
                visual_description="desc",
                visual_type="equation_write",
                visual_params={"latex": "x=1"},
                prev_scene_state=None,
                speaker="student",
                turn="question",
            ),
            Segment(
                id=12,
                narration="답변",
                tts_text="답변",
                visual_description="desc",
                visual_type="equation_transform",
                visual_params={"from_latex": "x=1", "to_latex": "x=2"},
                prev_scene_state=None,
                speaker="teacher",
                turn="answer",
            ),
        ],
    )
    out = _normalize_dialogue_script(script)
    assert [s.id for s in out.segments] == [0, 1]
    assert out.segments[0].narration.startswith("[질문] ")


def test_validate_dialogue_settings_rejects_unsupported_provider() -> None:
    settings = get_settings().model_copy(
        update={
            "dialogue_qa_enabled": True,
            "tts_provider": "azure",
        }
    )
    with pytest.raises(ValueError, match="replicate|inworld"):
        _validate_dialogue_mode_settings(settings)


def test_validate_dialogue_settings_replicate_requires_student_voice() -> None:
    settings = get_settings().model_copy(
        update={
            "dialogue_qa_enabled": True,
            "tts_provider": "replicate",
            "replicate_student_tts_speaker": "",
        }
    )
    with pytest.raises(ValueError, match="REPLICATE_STUDENT_TTS_SPEAKER"):
        _validate_dialogue_mode_settings(settings)


def test_validate_dialogue_settings_inworld_requires_student_voice() -> None:
    settings = get_settings().model_copy(
        update={
            "dialogue_qa_enabled": True,
            "tts_provider": "inworld",
            "inworld_student_tts_voice_id": "",
        }
    )
    with pytest.raises(ValueError, match="INWORLD_STUDENT_TTS_VOICE"):
        _validate_dialogue_mode_settings(settings)
