"""Group consecutive equation segments into chains for merged Manim rendering."""

from __future__ import annotations

from manim_video_gen.models.script import Segment, SegmentChain, TTSResult

EQUATION_TYPES = frozenset(
    {
        "equation_write",
        "equation_transform",
        "equation_steps",
        "highlight_result",
    }
)


def _is_equation_segment(seg: Segment) -> bool:
    return seg.visual_type in EQUATION_TYPES


def group_into_chains(
    segments: list[Segment],
    tts_results: list[TTSResult],
) -> list[SegmentChain]:
    """Split script into chains: equation segments with continuity merge into one chain."""
    if not segments:
        return []
    if len(segments) != len(tts_results):
        raise ValueError(
            f"segments ({len(segments)}) and tts_results ({len(tts_results)}) length mismatch"
        )

    chains: list[SegmentChain] = []

    for seg, tts in zip(segments, tts_results, strict=True):
        duration = float(tts.duration_seconds)
        extend = (
            _is_equation_segment(seg)
            and seg.prev_scene_state is not None
            and chains
            and _is_equation_segment(chains[-1].segments[-1])
        )

        if extend:
            ch = chains[-1]
            ch.segments.append(seg)
            ch.durations.append(duration)
            ch.tts_results.append(tts)
        else:
            chains.append(
                SegmentChain(
                    segments=[seg],
                    durations=[duration],
                    tts_results=[tts],
                    is_equation_chain=False,
                )
            )

    for ch in chains:
        ch.is_equation_chain = (
            len(ch.segments) >= 2
            and all(_is_equation_segment(s) for s in ch.segments)
        )

    return chains
