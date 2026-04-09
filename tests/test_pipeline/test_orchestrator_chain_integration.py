"""Lightweight integration: grouper + chain subtitle + chain renderer."""

from pathlib import Path

from manim_video_gen.models.script import SceneObjectState, Segment, TTSResult
from manim_video_gen.pipeline.chain_grouper import group_into_chains
from manim_video_gen.video.chain_renderer import ChainRenderer
from manim_video_gen.video.subtitle import generate_chain_ass_subtitle


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
    )
    assert "나레이션 1" in ass.read_text(encoding="utf-8")
    assert "나레이션 2" in ass.read_text(encoding="utf-8")
