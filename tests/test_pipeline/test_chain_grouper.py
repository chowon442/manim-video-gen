"""Tests for chain_grouper.group_into_chains."""

from pathlib import Path

import pytest

from manim_video_gen.models.script import SceneObjectState, Segment, TTSResult
from manim_video_gen.pipeline.chain_grouper import EQUATION_TYPES, group_into_chains


def _seg(
    sid: int,
    vt: str,
    *,
    prev: list[SceneObjectState] | None = None,
    params: dict | None = None,
) -> Segment:
    return Segment(
        id=sid,
        narration="n",
        tts_text="t",
        visual_description="d",
        visual_type=vt,
        visual_params=params or {},
        prev_scene_state=prev,
    )


def _tts(dur: float = 1.0) -> TTSResult:
    return TTSResult(audio_path=Path("/tmp/x.wav"), duration_seconds=dur)


def test_empty_segments_returns_empty():
    assert group_into_chains([], []) == []


def test_length_mismatch_raises():
    with pytest.raises(ValueError, match="length mismatch"):
        group_into_chains([_seg(0, "equation_write")], [])


def test_single_segment_standalone():
    s = _seg(0, "intro_problem")
    chains = group_into_chains([s], [_tts()])
    assert len(chains) == 1
    assert len(chains[0].segments) == 1
    assert chains[0].is_equation_chain is False


def test_equation_chain_two_with_prev_state():
    prev = [SceneObjectState(latex=r"x^2", position_expr="ORIGIN")]
    s0 = _seg(0, "equation_write", params={"latex": r"x^2+1"})
    s1 = _seg(1, "equation_transform", prev=prev, params={"from_latex": r"x^2", "to_latex": r"x^2+1"})
    chains = group_into_chains([s0, s1], [_tts(2.0), _tts(3.0)])
    assert len(chains) == 1
    assert len(chains[0].segments) == 2
    assert chains[0].is_equation_chain is True
    assert chains[0].total_duration == 5.0


def test_graph_splits_equation_chains():
    prev = [SceneObjectState(latex=r"a", position_expr="ORIGIN")]
    s0 = _seg(0, "equation_write", params={"latex": r"x"})
    s1 = _seg(1, "graph_plot", params={"func_python": "lambda x: x"})
    s2 = _seg(2, "equation_write", prev=prev, params={"latex": r"y"})
    chains = group_into_chains([s0, s1, s2], [_tts(), _tts(), _tts()])
    assert len(chains) == 3
    assert all(len(c.segments) == 1 for c in chains)
    assert all(c.is_equation_chain is False for c in chains)


def test_prev_none_starts_new_chain_even_after_equation():
    s0 = _seg(0, "equation_write", params={"latex": r"a"})
    s1 = _seg(1, "equation_write", params={"latex": r"b"})
    chains = group_into_chains([s0, s1], [_tts(), _tts()])
    assert len(chains) == 2


def test_equation_types_constant():
    assert "equation_write" in EQUATION_TYPES
    assert "equation_derivation" in EQUATION_TYPES
    assert "highlight_result" in EQUATION_TYPES


def test_equation_derivation_chains_with_prev():
    prev = [SceneObjectState(latex=r"a", position_expr="ORIGIN")]
    s0 = _seg(0, "equation_write", params={"latex": r"x"})
    s1 = _seg(1, "equation_derivation", prev=prev, params={"steps": [{"latex": r"1=1"}]})
    chains = group_into_chains([s0, s1], [_tts(1.0), _tts(2.0)])
    assert len(chains) == 1
    assert chains[0].is_equation_chain is True
