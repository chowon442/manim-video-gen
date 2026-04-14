from pathlib import Path

import pytest

from manim_video_gen.config import get_settings
from manim_video_gen.models.script import Segment, TTSResult, VideoScript
from manim_video_gen.pipeline.orchestrator import generate_video


class _DummyClientAutoRepair:
    def __init__(self, *args, **kwargs):
        self.scriptify_calls = 0

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

        self.scriptify_calls += 1
        if self.scriptify_calls == 1:
            # Invalid for consistency(error): equation_write narration claims graph scene.
            return VideoScript(
                title="v",
                segments=[
                    Segment(
                        id=0,
                        narration="이 식의 그래프를 좌표평면에 그려 봅시다.",
                        tts_text="이 식의 그래프를 좌표평면에 그려 봅시다.",
                        visual_description="식 쓰기",
                        visual_type="equation_write",
                        visual_params={"latex": "x^2+1=0"},
                    )
                ],
            )

        # Repaired response.
        return VideoScript(
            title="v",
            segments=[
                Segment(
                    id=0,
                    narration="주어진 방정식 x^2+1=0을 씁니다.",
                    tts_text="주어진 방정식 엑스 제곱 더하기 일은 영을 씁니다.",
                    visual_description="식 쓰기",
                    visual_type="equation_write",
                    visual_params={"latex": "x^2+1=0"},
                )
            ],
        )


class _DummyTTS:
    async def synthesize(self, text, output_path: Path):
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

    def generate_silence_audio(self, *, duration, output_path):
        output_path.write_bytes(b"m4a")
        return output_path


def _make_dummy_ffprobe_duration(seconds: float):
    def _ffprobe_duration(_path):
        return float(seconds)

    return _ffprobe_duration


@pytest.mark.asyncio
async def test_error_mode_auto_repairs_script_then_continues(monkeypatch):
    def _fake_render_manim_scene(**kwargs):
        path = kwargs["scene_path"].with_suffix(".mp4")
        path.write_bytes(b"mp4")
        return path

    client = _DummyClientAutoRepair()
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.OpenRouterClient",
        lambda *_a, **_k: client,
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
            "consistency_mode": "error",
            "consistency_auto_repair": True,
            "consistency_auto_repair_max_attempts": 2,
            "script_quality_enabled": False,
            "burn_subtitles": False,
            "diagnostic_dump": False,
            "keep_workspace": True,
            "openrouter_api_key": "dummy",
        }
    )

    final_path, workspace = await generate_video("dummy", settings=settings)
    try:
        assert final_path.is_file()
        assert client.scriptify_calls == 2
    finally:
        workspace.cleanup()
