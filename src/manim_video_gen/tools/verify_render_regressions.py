"""Post-render regression checks for overlap and text issues.

Usage:
  python scripts/verify_render_regressions.py --video artifacts/final.mp4 --at 48 --at 62
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FrameSignal:
    t: float
    bright_box_ratio: float
    overlap_ratio: float


def _run(cmd: list[str]) -> str:
    cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
    out = cp.stdout or ""
    err = cp.stderr or ""
    if out and err:
        return out + "\n" + err
    return out or err


def _ffprobe_duration(video: Path) -> float:
    out = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video),
        ]
    )
    return float(json.loads(out)["format"]["duration"])


def _extract_frame(video: Path, t: float, out_png: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            str(out_png),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _frame_signals(frame_png: Path, t: float) -> FrameSignal:
    # Detect suspicious bright box pixels (e.g., tofu/white square)
    box_raw = _run(
        [
            "ffmpeg",
            "-i",
            str(frame_png),
            "-vf",
            "signalstats,metadata=print",
            "-f",
            "null",
            "-",
        ]
    )
    yhigh = 0.0
    for line in box_raw.splitlines():
        if "lavfi.signalstats.YHIGH=" in line:
            try:
                yhigh = float(line.split("=")[-1].strip())
            except ValueError:
                pass

    # Edge-density proxy for heavy overlap/crowding (Canny + blackframe ratio)
    overlap_raw = _run(
        [
            "ffmpeg",
            "-i",
            str(frame_png),
            "-vf",
            "format=gray,edgedetect=low=0.1:high=0.3,blackframe=amount=98:threshold=8",
            "-f",
            "null",
            "-",
        ]
    )
    pblack = 100.0
    for line in overlap_raw.splitlines():
        if "pblack:" in line:
            try:
                pblack = float(line.split("pblack:")[-1].split()[0])
            except ValueError:
                pass

    # Heuristic: lower pblack after edge-detect => denser edge content (possible overlap)
    overlap_ratio = max(0.0, min(1.0, (100.0 - pblack) / 100.0))
    bright_box_ratio = max(0.0, min(1.0, yhigh / 255.0))
    return FrameSignal(
        t=t, bright_box_ratio=bright_box_ratio, overlap_ratio=overlap_ratio
    )


def _print_report(video: Path, signals: list[FrameSignal]) -> int:
    print(f"[verify] video={video}")
    print("[verify] t(s)  overlap_ratio  bright_box_ratio  flags")
    fail = 0
    for s in signals:
        flags: list[str] = []
        if s.overlap_ratio > 0.82:
            flags.append("OVERLAP_SUSPECT")
        if s.bright_box_ratio > 0.98:
            flags.append("BRIGHT_BOX_SUSPECT")
        if flags:
            fail += 1
        print(
            f"[verify] {s.t:6.1f}  {s.overlap_ratio:13.3f}  {s.bright_box_ratio:16.3f}  {'|'.join(flags) if flags else '-'}"
        )

    if fail:
        print(f"[verify] FAIL: suspicious frames={fail}")
        return 2
    print("[verify] PASS: no suspicious overlap/box signals")
    return 0


def run_cli() -> int:
    p = argparse.ArgumentParser(
        description="Verify render regressions on selected timestamps"
    )
    p.add_argument("--video", type=Path, required=True)
    p.add_argument(
        "--at",
        type=float,
        action="append",
        default=[],
        help="Timestamp seconds to inspect (repeatable)",
    )
    args = p.parse_args()

    video = args.video
    if not video.is_file():
        raise SystemExit(f"video not found: {video}")

    duration = _ffprobe_duration(video)
    times = sorted({t for t in args.at if 0.0 <= t <= duration})
    if not times:
        raise SystemExit("no valid --at timestamps provided")

    signals: list[FrameSignal] = []
    with tempfile.TemporaryDirectory(prefix="mvgen_verify_") as td:
        root = Path(td)
        for idx, t in enumerate(times):
            png = root / f"f_{idx:03d}.png"
            _extract_frame(video, t, png)
            signals.append(_frame_signals(png, t))

    return _print_report(video, signals)
