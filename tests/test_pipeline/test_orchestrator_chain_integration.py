"""Lightweight integration: grouper + chain subtitle + chain renderer."""

from pathlib import Path
import pytest

from manim_video_gen.models.script import SceneObjectState, Segment, TTSResult
from manim_video_gen.models.script import VideoScript
from manim_video_gen.pipeline.chain_grouper import group_into_chains
from manim_video_gen.pipeline.orchestrator import generate_video
from manim_video_gen.video.chain_renderer import ChainRenderer
from manim_video_gen.video.subtitle import generate_chain_ass_subtitle
from manim_video_gen.config import get_settings


class _DummyClient:
    def __init__(self, *args, **kwargs):
        self._calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def complete_json_model(self, **kwargs):
        self._calls += 1
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
                    narration="핵심 원리를 강조합니다.",
                    tts_text="핵심 원리를 강조합니다.",
                    visual_description="desc",
                    visual_type="highlight_result",
                    visual_params={"latex": "y=c,\\;8<c<12"},
                    prev_scene_state=None,
                )
            ],
        )


class _DummyTTS:
    async def synthesize(self, text, output_path):
        output_path.write_bytes(b"wav")
        return TTSResult(audio_path=output_path, duration_seconds=1.0)


def _make_dummy_ffprobe_duration(seconds: float):
    def _ffprobe_duration(_path):
        return float(seconds)

    return _ffprobe_duration


def test_grouper_renderer_subtitle_roundtrip(tmp_path: Path):
    prev = [SceneObjectState(latex=r"x", position_expr="ORIGIN")]
    s0 = Segment(
        id=0,
        narration="나레이션 1",
        visual_description="d",
        visual_type="equation_write",
        visual_params={"latex": r"a=b"},
    )
    s1 = Segment(
        id=1,
        narration="나레이션 2",
        visual_description="d",
        visual_type="equation_transform",
        visual_params={"from_latex": r"a=b", "to_latex": r"c=d"},
        prev_scene_state=prev,
    )
    t0 = TTSResult(audio_path=Path("/tmp/a.wav"), duration_seconds=2.0)
    t1 = TTSResult(audio_path=Path("/tmp/b.wav"), duration_seconds=3.0)
    chains = group_into_chains([s0, s1], [t0, t1])
    assert len(chains) == 1
    assert chains[0].is_equation_chain is True
    code = ChainRenderer().render_chain(chains[0])
    compile(code, "<x>", "exec")
    ass = tmp_path / "c.ass"
    generate_chain_ass_subtitle(
        [s0.narration, s1.narration],
        chains[0].durations,
        ass,
        wrap_mode="char",
        font_size=39,
        margin_l=30,
        margin_r=31,
        margin_v=32,
    )
    text = ass.read_text(encoding="utf-8")
    assert "나레이션 1" in text
    assert "나레이션 2" in text
    assert "Style: Default,Noto Sans KR,39" in text
    assert ",2,30,31,32,1" in text


@pytest.mark.asyncio
async def test_consistency_error_mode_ignores_warn_only_issue(monkeypatch):
    def _fake_render_manim_scene_sync(**kwargs):
        path = kwargs["scene_path"].with_suffix(".mp4")
        path.write_bytes(b"mp4")
        return path

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

    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.OpenRouterClient", _DummyClient
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.get_tts_provider", lambda _s: _DummyTTS()
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.render_manim_scene",
        _fake_render_manim_scene_sync,
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.VideoComposer", _DummyComposer
    )
    monkeypatch.setattr(
        "manim_video_gen.pipeline.orchestrator.ffprobe_duration_seconds",
        _make_dummy_ffprobe_duration(1.0),
    )

    settings = get_settings().model_copy(
        update={
            "consistency_mode": "error",
            "script_quality_enabled": False,
            "burn_subtitles": False,
            "diagnostic_dump": False,
            "keep_workspace": True,
            "openrouter_api_key": "dummy",
        }
    )

    final_path, workspace = await generate_video("dummy problem", settings=settings)
    try:
        assert final_path.is_file()
    finally:
        workspace.cleanup()
