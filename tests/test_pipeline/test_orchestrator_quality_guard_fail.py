from pathlib import Path

import pytest

from manim_video_gen.config import get_settings
from manim_video_gen.models.script import Segment, TTSResult, VideoScript
from manim_video_gen.pipeline.orchestrator import generate_video


class _DummyClientNoImprove:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def complete_json_model(self, **kwargs):
        model = kwargs["response_model"]
        if model.__name__ == "SolutionPlan":
            from manim_video_gen.models.solution import SolutionPlan, SolutionStep

            return SolutionPlan(
                title="t", steps=[SolutionStep(step_number=1, explanation="e")]
            )

        # Always equation-only script (low visual variety)
        return VideoScript(
            title="v",
            segments=[
                Segment(
                    id=0,
                    narration="x^2+2x+1=0을 씁니다.",
                    tts_text="엑스 제곱 더하기 이엑스 더하기 일은 영을 씁니다.",
                    visual_description="desc",
                    visual_type="equation_write",
                    visual_params={"latex": "x^2+2x+1=0"},
                    prev_scene_state=None,
                ),
                Segment(
                    id=1,
                    narration="인수분해하면 (x+1)^2=0 입니다.",
                    tts_text="인수분해하면 엑스 더하기 일의 제곱은 영입니다.",
                    visual_description="desc",
                    visual_type="equation_transform",
                    visual_params={"from_latex": "x^2+2x+1=0", "to_latex": "(x+1)^2=0"},
                    prev_scene_state=None,
                ),
                Segment(
                    id=2,
                    narration="해는 x=-1 입니다.",
                    tts_text="해는 엑스는 마이너스 일입니다.",
                    visual_description="desc",
                    visual_type="highlight_result",
                    visual_params={"latex": "x=-1"},
                    prev_scene_state=None,
                ),
            ],
        )


class _DummyTTS:
    async def synthesize(self, text, output_path: Path, speaker_role="teacher"):
        _ = speaker_role
        output_path.write_bytes(b"wav")
        return TTSResult(audio_path=output_path, duration_seconds=1.0)


class _DummyComposer:
    def __init__(self, *args, **kwargs):
        pass

    def merge_segment(self, **kwargs):
        kwargs["output_path"].write_bytes(b"mp4")
        return kwargs["output_path"]

    def compose_final_with_bridges(self, paths, output, **kwargs):
        output.write_bytes(b"mp4")
        return output

    def compose_final(self, paths, output):
        output.write_bytes(b"mp4")
        return output


def _make_dummy_ffprobe_duration(seconds: float):
    def _ffprobe_duration(_path):
        return float(seconds)

    return _ffprobe_duration


@pytest.mark.asyncio
async def test_quality_guard_fail_on_soft_after_max_raises(monkeypatch):
    def _fake_render_manim_scene(**kwargs):
        path = kwargs["scene_path"].with_suffix(".mp4")
        path.write_bytes(b"mp4")
        return path

    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.OpenRouterClient",
        lambda *_a, **_k: _DummyClientNoImprove(),
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.get_tts_provider",
        lambda _s: _DummyTTS(),
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.render_manim_scene",
        _fake_render_manim_scene,
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.VideoComposer",
        _DummyComposer,
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.ffprobe_duration_seconds",
        _make_dummy_ffprobe_duration(1.0),
    )

    settings = get_settings().model_copy(
        update={
            "script_quality_enabled": True,
            "script_quality_profile": "quality_first",
            "script_quality_min_total": 0.95,
            "script_quality_max_attempts": 1,
            "script_quality_max_segments_per_attempt": 1,
            "script_quality_fail_on_soft_after_max": True,
            "consistency_mode": "warn",
            "burn_subtitles": False,
            "diagnostic_dump": False,
            "keep_workspace": False,
            "openrouter_api_key": "dummy",
        }
    )

    with pytest.raises(ValueError, match="Script quality"):
        await generate_video("dummy", settings=settings)
