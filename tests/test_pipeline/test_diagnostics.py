from pathlib import Path

from manim_video_gen.models.script import (
    ProcessedSegment,
    Segment,
    TTSResult,
    VideoScript,
)
from manim_video_gen.models.solution import SolutionPlan, SolutionStep
from manim_video_gen.pipeline.diagnostics import dump_generation_diagnostics
from manim_video_gen.utils.file_manager import SessionWorkspace


def _segment() -> Segment:
    return Segment(
        id=0,
        narration="나레이션",
        tts_text="나레이션",
        visual_description="desc",
        visual_type="equation_write",
        visual_params={"latex": "x=1"},
    )


def test_dump_generation_diagnostics_writes_core_files(tmp_path: Path):
    ws = SessionWorkspace(root=tmp_path / "ws")
    (ws.root / "seg_00.ass").write_text("dummy", encoding="utf-8")

    seg = _segment()
    processed = [
        ProcessedSegment(
            segment=seg,
            tts=TTSResult(audio_path=ws.root / "seg_00.wav", duration_seconds=1.2),
            manim_code="from manim import *\nclass Segment(Scene):\n    def construct(self):\n        self.wait(1)",
            video_path=None,
            merged_segment_path=None,
        )
    ]

    run_dir = dump_generation_diagnostics(
        run_id="test_run",
        problem_text="x+1=0",
        workspace=ws,
        plan=SolutionPlan(
            title="t", steps=[SolutionStep(step_number=1, explanation="e")]
        ),
        script=VideoScript(title="v", segments=[seg]),
        consistency_report=None,
        processed_segments=processed,
        llm_manim_retries=0,
        elapsed_seconds=3.4,
        final_path=None,
        error=None,
        output_root=tmp_path / "runs",
    )

    assert (run_dir / "problem.txt").is_file()
    assert (run_dir / "solution_plan.json").is_file()
    assert (run_dir / "script.json").is_file()
    assert (run_dir / "segments.json").is_file()
    assert (run_dir / "summary.json").is_file()
    assert (run_dir / "ass" / "seg_00.ass").is_file()
    assert (run_dir / "segment_code" / "segment_00.py").is_file()
