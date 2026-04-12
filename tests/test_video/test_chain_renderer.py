"""ChainRenderer merged scene code generation tests."""

from pathlib import Path

import pytest

from manim_video_gen.models.script import (
    SceneObjectState,
    Segment,
    SegmentChain,
    TTSResult,
)
from manim_video_gen.video.chain_renderer import ChainRenderer


def _chain(*items: tuple[Segment, float]) -> SegmentChain:
    segs = [s for s, _ in items]
    durs = [d for _, d in items]
    tts = [
        TTSResult(audio_path=Path(f"/tmp/s{i}.wav"), duration_seconds=d)
        for i, d in enumerate(durs)
    ]
    return SegmentChain(
        segments=segs, durations=durs, tts_results=tts, is_equation_chain=True
    )


def test_write_then_transform_has_transform_matching_tex():
    prev = [SceneObjectState(latex=r"x^2", position_expr="ORIGIN")]
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="equation_write",
        visual_params={"latex": r"x^2+6x+9=x"},
    )
    s1 = Segment(
        id=1,
        narration="b",
        visual_description="d",
        visual_type="equation_transform",
        visual_params={"from_latex": r"x^2+6x+9=x", "to_latex": r"x^2+5x+9=0"},
        prev_scene_state=prev,
    )
    ch = _chain((s0, 3.5), (s1, 4.0))
    code = ChainRenderer().render_chain(ch)
    assert "TransformMatchingTex" in code
    assert "class Segment(Scene):" in code
    compile(code, "<chain>", "exec")


def test_three_segment_chain_compiles():
    prev1 = [SceneObjectState(latex=r"a", position_expr="ORIGIN")]
    prev2 = [SceneObjectState(latex=r"b", position_expr="ORIGIN")]
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="equation_write",
        visual_params={"latex": r"1=1"},
    )
    s1 = Segment(
        id=1,
        narration="b",
        visual_description="d",
        visual_type="equation_transform",
        visual_params={"from_latex": r"1=1", "to_latex": r"2=2"},
        prev_scene_state=prev1,
    )
    s2 = Segment(
        id=2,
        narration="c",
        visual_description="d",
        visual_type="highlight_result",
        visual_params={"latex": r"2=2"},
        prev_scene_state=prev2,
    )
    ch = _chain((s0, 2.0), (s1, 2.5), (s2, 2.0))
    code = ChainRenderer().render_chain(ch)
    assert "SurroundingRectangle" in code
    assert "FadeOut(box_" in code
    compile(code, "<chain>", "exec")


def test_chain_ends_with_mobjects_fadeout():
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="equation_write",
        visual_params={"latex": r"x"},
    )
    ch = _chain((s0, 2.0))
    code = ChainRenderer().render_chain(ch)
    assert "FadeOut(m)" in code
    assert "self.clear()" not in code


def test_equation_derivation_in_chain():
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="equation_derivation",
        visual_params={
            "steps": [
                {"latex": r"x^2+1=0"},
                {"latex": r"x^2=-1", "annotation": "정리"},
            ]
        },
    )
    ch = _chain((s0, 6.0))
    code = ChainRenderer().render_chain(ch)
    assert r"\Downarrow" in code or "Downarrow" in code
    assert "Text(" in code
    assert "active = VGroup(*list(self.mobjects))" in code
    compile(code, "<chain>", "exec")


def test_highlight_after_derivation_replaces_active_group():
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="equation_derivation",
        visual_params={
            "steps": [
                {"latex": r"x^2+1=0"},
                {"latex": r"x^2=-1", "annotation": "정리"},
            ]
        },
    )
    s1 = Segment(
        id=1,
        narration="b",
        visual_description="d",
        visual_type="highlight_result",
        visual_params={"latex": r"x=\pm i"},
        prev_scene_state=[SceneObjectState(latex=r"x^2=-1", position_expr="ORIGIN")],
    )
    ch = _chain((s0, 6.0), (s1, 2.5))
    code = ChainRenderer().render_chain(ch)
    assert "ReplacementTransform(active, eq_1)" in code
    compile(code, "<chain_active_replace>", "exec")


def test_equation_steps_in_chain():
    prev = [SceneObjectState(latex=r"old", position_expr="ORIGIN")]
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="equation_steps",
        visual_params={"steps": [r"a=b", r"b=c"]},
        prev_scene_state=prev,
    )
    ch = _chain((s0, 4.0))
    code = ChainRenderer().render_chain(ch)
    assert "VGroup" in code
    compile(code, "<chain>", "exec")


def test_unsupported_type_raises():
    s0 = Segment(
        id=0,
        narration="a",
        visual_description="d",
        visual_type="graph_plot",
        visual_params={"func_python": "lambda x: x"},
    )
    ch = _chain((s0, 2.0))
    with pytest.raises(KeyError):
        ChainRenderer().render_chain(ch)
