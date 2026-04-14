"""Diagnostic dump helpers for post-run analysis."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from manim_video_gen.config import project_root
from manim_video_gen.models.script import ProcessedSegment, VideoScript
from manim_video_gen.models.solution import SolutionPlan
from manim_video_gen.utils.file_manager import SessionWorkspace


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{uuid.uuid4().hex[:8]}"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _serialize_consistency_report(report: Any | None) -> dict[str, Any]:
    if report is None:
        return {
            "issue_count": 0,
            "error_count": 0,
            "warn_count": 0,
            "issues": [],
        }
    issues: list[dict[str, Any]] = []
    for issue in getattr(report, "issues", []):
        issues.append(
            {
                "severity": str(getattr(issue, "severity", "warn")),
                "code": str(getattr(issue, "code", "UNKNOWN")),
                "message": str(getattr(issue, "message", "")),
                "segment_id": int(getattr(issue, "segment_id", -1)),
            }
        )
    return {
        "issue_count": len(issues),
        "error_count": sum(1 for i in issues if i["severity"] == "error"),
        "warn_count": sum(1 for i in issues if i["severity"] == "warn"),
        "issues": issues,
    }


def _serialize_script_quality_report(report: Any | None) -> dict[str, Any]:
    if report is None:
        return {
            "enabled": False,
            "profile": None,
            "total_score": None,
            "dimensions": {},
            "hard_failures": [],
            "soft_issues": [],
            "repair_targets": [],
        }

    def _issue_to_dict(issue: Any) -> dict[str, Any]:
        return {
            "severity": str(getattr(issue, "severity", "warn")),
            "code": str(getattr(issue, "code", "UNKNOWN")),
            "message": str(getattr(issue, "message", "")),
            "segment_id": int(getattr(issue, "segment_id", -1)),
        }

    hard = [_issue_to_dict(i) for i in getattr(report, "hard_failures", [])]
    soft = [_issue_to_dict(i) for i in getattr(report, "soft_issues", [])]
    return {
        "enabled": True,
        "profile": str(getattr(report, "profile", "balanced")),
        "total_score": float(getattr(report, "total_score", 0.0)),
        "dimensions": dict(getattr(report, "dimensions", {}) or {}),
        "hard_failures": hard,
        "soft_issues": soft,
        "repair_targets": [
            int(x) for x in list(getattr(report, "repair_targets", []) or [])
        ],
    }


def dump_generation_diagnostics(
    *,
    run_id: str,
    problem_text: str,
    workspace: SessionWorkspace,
    plan: SolutionPlan | None,
    script: VideoScript | None,
    consistency_report: Any | None,
    script_quality_report: Any | None,
    processed_segments: list[ProcessedSegment],
    llm_manim_retries: int,
    elapsed_seconds: float,
    final_path: Path | None,
    error: str | None,
    output_root: Path | None = None,
) -> Path:
    root = output_root or (project_root() / "artifacts" / "runs")
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "problem.txt").write_text(problem_text, encoding="utf-8")

    if plan is not None:
        _write_json(run_dir / "solution_plan.json", plan.model_dump())
    if script is not None:
        _write_json(run_dir / "script.json", script.model_dump())

    _write_json(
        run_dir / "consistency_report.json",
        _serialize_consistency_report(consistency_report),
    )
    _write_json(
        run_dir / "script_quality_report.json",
        _serialize_script_quality_report(script_quality_report),
    )

    code_dir = run_dir / "segment_code"
    code_dir.mkdir(parents=True, exist_ok=True)
    segments_payload: list[dict[str, Any]] = []
    for item in processed_segments:
        seg = item.segment
        segments_payload.append(
            {
                "id": seg.id,
                "visual_type": seg.visual_type,
                "narration": seg.narration,
                "visual_params": seg.visual_params,
                "tts_duration_seconds": float(item.tts.duration_seconds),
                "audio_path": str(item.tts.audio_path),
                "video_path": str(item.video_path) if item.video_path else None,
                "merged_segment_path": str(item.merged_segment_path)
                if item.merged_segment_path
                else None,
            }
        )
        if item.manim_code:
            (code_dir / f"segment_{seg.id:02d}.py").write_text(
                item.manim_code,
                encoding="utf-8",
            )

    _write_json(run_dir / "segments.json", segments_payload)

    ass_dir = run_dir / "ass"
    ass_dir.mkdir(parents=True, exist_ok=True)
    for ass in workspace.root.glob("*.ass"):
        shutil.copy2(ass, ass_dir / ass.name)

    _write_json(
        run_dir / "summary.json",
        {
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "workspace_root": str(workspace.root),
            "final_path": str(final_path) if final_path else None,
            "final_exists": bool(final_path and final_path.is_file()),
            "llm_manim_retries": llm_manim_retries,
            "elapsed_seconds": float(elapsed_seconds),
            "segments": len(processed_segments),
            "error": error,
        },
    )

    return run_dir
