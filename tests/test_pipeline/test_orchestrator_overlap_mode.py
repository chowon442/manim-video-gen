from pathlib import Path

import pytest

from manim_video_gen.config import get_settings
from manim_video_gen.models.script import Segment, TTSResult, VideoScript
from manim_video_gen.pipeline.orchestrator import generate_video


class _DummyClient:
    def __init__(self, *args, **kwargs):
        self.calls = 0

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

        return VideoScript(
            title="v",
            segments=[
                Segment(
                    id=0,
                    narration="수식을 씁니다",
                    tts_text="수식을 씁니다",
                    visual_description="desc",
                    visual_type="equation_write",
                    visual_params={"latex": "x^2+1=0"},
                    prev_scene_state=None,
                ),
                Segment(
                    id=1,
                    narration="다음 수식으로 바꿉니다",
                    tts_text="다음 수식으로 바꿉니다",
                    visual_description="desc",
                    visual_type="equation_transform",
                    visual_params={"from_latex": "x^2+1=0", "to_latex": "x^2=-1"},
                    prev_scene_state=[
                        {
                            "latex": "x^2+1=0",
                            "position_expr": "UP",
                        }
                    ],
                ),
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

    def concat_segments(self, segment_paths, output_path):
        output_path.write_bytes(b"mp4")
        return output_path


@pytest.mark.asyncio
async def test_overlap_safe_mode_disables_chain_and_prev_state(monkeypatch):
    def _fake_render_manim_scene(**kwargs):
        scene_path = kwargs["scene_path"]
        code = kwargs["code"]
        if scene_path.stem.startswith("scene_"):
            assert "_p0 = MathTex(" not in code
            assert "self.add(_p0)" not in code
        # chain mode should be bypassed entirely
        assert not scene_path.stem.startswith("chain_")
        path = scene_path.with_suffix(".mp4")
        path.write_bytes(b"mp4")
        return path

    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.OpenRouterClient", _DummyClient
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.get_tts_provider", lambda _s: _DummyTTS()
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.render_manim_scene",
        _fake_render_manim_scene,
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.VideoComposer", _DummyComposer
    )

    settings = get_settings().model_copy(
        update={
            "burn_subtitles": False,
            "diagnostic_dump": False,
            "keep_workspace": True,
            "openrouter_api_key": "dummy",
            "disable_equation_chain": True,
            "disable_prev_scene_state": True,
            "scene_bridge_enabled": False,
        }
    )

    final_path, workspace = await generate_video("dummy problem", settings=settings)
    try:
        assert final_path.is_file()
    finally:
        workspace.cleanup()
