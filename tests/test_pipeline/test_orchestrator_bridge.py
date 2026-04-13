from pathlib import Path

from manim_video_gen.models.script import ProcessedSegment, Segment, TTSResult
from manim_video_gen.pipeline.orchestrator import (
    _adaptive_bridge_duration_seconds,
    _build_bridge_spec_for_boundary,
    _build_bridge_specs_for_chains,
    _build_bridge_specs_for_processed,
    _segment_bridge_latex,
)


def _processed(
    sid: int,
    vt: str,
    params: dict,
    *,
    merged: str,
) -> ProcessedSegment:
    seg = Segment(
        id=sid,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type=vt,
        visual_params=params,
        prev_scene_state=None,
    )
    return ProcessedSegment(
        segment=seg,
        tts=TTSResult(audio_path=Path("/tmp/a.wav"), duration_seconds=1.0),
        manim_code=None,
        video_path=None,
        merged_segment_path=Path(merged),
    )


def test_segment_bridge_latex_extracts_equation_derivation_last_step():
    seg = Segment(
        id=1,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type="equation_derivation",
        visual_params={
            "steps": [
                {"latex": r"x^2+1=0"},
                {"latex": r"x=\pm i", "annotation": "결론"},
            ]
        },
        prev_scene_state=None,
    )
    assert _segment_bridge_latex(seg) == r"x=\pm i"


def test_segment_bridge_latex_extracts_equation_derivation_first_step_for_first_anchor():
    seg = Segment(
        id=1,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type="equation_derivation",
        visual_params={
            "steps": [
                {"latex": r"x^2+1=0"},
                {"latex": r"x=\pm i", "annotation": "결론"},
            ]
        },
        prev_scene_state=None,
    )
    assert _segment_bridge_latex(seg, anchor="first") == r"x^2+1=0"


def test_build_bridge_specs_for_processed_adjacent_equation_like():
    p0 = _processed(0, "equation_write", {"latex": r"x^2+1=0"}, merged="/tmp/m0.mp4")
    p1 = _processed(1, "highlight_result", {"latex": r"x=\pm i"}, merged="/tmp/m1.mp4")
    specs = _build_bridge_specs_for_processed(
        [p0, p1],
        merged_paths=[Path("/tmp/m0.mp4"), Path("/tmp/m1.mp4")],
    )
    assert len(specs) == 1
    assert specs[0]["from_segment_id"] == 0
    assert specs[0]["to_segment_id"] == 1
    assert specs[0]["fallback"] == "hard_cut"
    assert specs[0]["to_latex"] == r"x=\pm i"
    assert 0.6 <= float(specs[0]["duration"]) <= 1.2


def test_build_bridge_specs_skips_non_equation_boundary():
    p0 = _processed(
        0, "graph_plot", {"func_python": "lambda x: x"}, merged="/tmp/m0.mp4"
    )
    p1 = _processed(1, "outro_summary", {"summary_text": "정리"}, merged="/tmp/m1.mp4")
    specs = _build_bridge_specs_for_processed(
        [p0, p1],
        merged_paths=[Path("/tmp/m0.mp4"), Path("/tmp/m1.mp4")],
    )
    assert specs == []


def test_build_bridge_specs_uses_chain_boundary_last_to_first():
    p0 = _processed(0, "equation_write", {"latex": r"a=b"}, merged="/tmp/c0.mp4")
    p1 = _processed(
        1,
        "equation_derivation",
        {"steps": [{"latex": r"b=c"}, {"latex": r"c=d"}]},
        merged="/tmp/c0.mp4",
    )
    p2 = _processed(2, "highlight_result", {"latex": r"d=e"}, merged="/tmp/c1.mp4")
    specs = _build_bridge_specs_for_processed(
        [p0, p1, p2],
        merged_paths=[Path("/tmp/c0.mp4"), Path("/tmp/c1.mp4")],
    )
    assert len(specs) == 1
    assert specs[0]["from_segment_id"] == 1
    assert specs[0]["to_segment_id"] == 2
    assert specs[0]["from_latex"] == r"c=d"
    assert specs[0]["to_latex"] == r"d=e"


def test_build_bridge_specs_uses_right_first_anchor_not_last():
    p0 = _processed(0, "equation_write", {"latex": r"a=b"}, merged="/tmp/c0.mp4")
    p1 = _processed(
        1,
        "equation_derivation",
        {"steps": [{"latex": r"b=c"}, {"latex": r"c=d"}]},
        merged="/tmp/c1.mp4",
    )
    specs = _build_bridge_specs_for_processed(
        [p0, p1],
        merged_paths=[Path("/tmp/c0.mp4"), Path("/tmp/c1.mp4")],
    )
    assert len(specs) == 1
    assert specs[0]["from_latex"] == r"a=b"
    assert specs[0]["to_latex"] == r"b=c"


def test_build_bridge_spec_skips_low_confidence_pair():
    left = Segment(
        id=0,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type="equation_write",
        visual_params={"latex": r"x^2+1=0"},
        prev_scene_state=None,
    )
    right = Segment(
        id=1,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type="highlight_result",
        visual_params={"latex": r"y=mx+b"},
        prev_scene_state=None,
    )
    assert _build_bridge_spec_for_boundary(left, right) is None


def test_build_bridge_specs_for_chains_uses_chain_boundaries():
    left_seg = Segment(
        id=10,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type="equation_derivation",
        visual_params={"steps": [{"latex": r"x+y=1"}, {"latex": r"x=1-y"}]},
        prev_scene_state=None,
    )
    right_seg = Segment(
        id=11,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type="equation_derivation",
        visual_params={"steps": [{"latex": r"x-y=1"}, {"latex": r"y=1-x"}]},
        prev_scene_state=None,
    )

    from manim_video_gen.models.script import SegmentChain

    ch0 = SegmentChain(
        segments=[left_seg],
        durations=[1.0],
        tts_results=[TTSResult(audio_path=Path("/tmp/a.wav"), duration_seconds=1.0)],
        is_equation_chain=False,
    )
    ch1 = SegmentChain(
        segments=[right_seg],
        durations=[1.0],
        tts_results=[TTSResult(audio_path=Path("/tmp/b.wav"), duration_seconds=1.0)],
        is_equation_chain=False,
    )
    specs = _build_bridge_specs_for_chains([ch0, ch1])
    assert len(specs) == 1
    assert specs[0]["from_segment_id"] == 10
    assert specs[0]["to_segment_id"] == 11


def test_adaptive_bridge_duration_within_bounds():
    d = _adaptive_bridge_duration_seconds(
        r"x_1 = \\frac{1}{7}, \\quad x_2 = \\frac{5}{7}",
        r"x_1 + 4x_2 = 3",
    )
    assert 0.6 <= d <= 1.2
