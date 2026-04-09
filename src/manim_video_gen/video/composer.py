"""FFmpeg-based audio/video merge and concatenation."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def ffprobe_duration_seconds(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    meta = json.loads(completed.stdout)
    return float(meta["format"]["duration"])


class VideoComposer:
    def __init__(self, *, crossfade_duration: float) -> None:
        self.crossfade_duration = float(crossfade_duration)

    def merge_segment(
        self,
        *,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        self._run(cmd)
        return output_path

    def compose_final(self, merged_paths: list[Path], output_path: Path) -> Path:
        """세그먼트별 병합 파일들을 받아 crossfade를 적용하며 최종 영상을 생성한다."""
        return self.concat_segments(merged_paths, output_path)

    def concat_segments(self, segment_paths: list[Path], output_path: Path) -> Path:
        if not segment_paths:
            raise ValueError("No segments to concatenate")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if len(segment_paths) == 1:
            # Copy via ffmpeg to normalize container
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(segment_paths[0]),
                "-c",
                "copy",
                str(output_path),
            ]
            self._run(cmd)
            return output_path

        cf = self.crossfade_duration
        if cf <= 0:
            return self._concat_demuxer(segment_paths, output_path)

        return self._concat_xfade(segment_paths, output_path, cf)

    def _concat_demuxer(self, segment_paths: list[Path], output_path: Path) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            for p in segment_paths:
                handle.write(f"file '{p.as_posix()}'\n")
            list_path = Path(handle.name)
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(output_path),
            ]
            self._run(cmd)
        finally:
            list_path.unlink(missing_ok=True)
        return output_path

    def _concat_xfade(
        self,
        segment_paths: list[Path],
        output_path: Path,
        crossfade: float,
    ) -> Path:
        for p in segment_paths:
            if not p.exists():
                raise FileNotFoundError(f"세그먼트 파일이 존재하지 않습니다: {p}")

        durs = [ffprobe_duration_seconds(p) for p in segment_paths]

        if any(d <= 0 for d in durs):
            bad = [str(p) for p, d in zip(segment_paths, durs) if d <= 0]
            raise ValueError(
                f"오디오 스트림이 없거나 지속 시간이 0인 세그먼트: {bad}. "
                "merge_segment() 이후에 concat_segments()를 호출했는지 확인하세요."
            )

        inputs: list[str] = []
        for p in segment_paths:
            inputs.extend(["-i", str(p)])

        n = len(segment_paths)
        v_label = "0:v"
        a_label = "0:a"
        run_len = float(durs[0])

        filter_parts: list[str] = []
        for i in range(1, n):
            out_v = f"v{i}"
            out_a = f"a{i}"
            offset = max(0.0, run_len - crossfade)
            filter_parts.append(
                f"[{v_label}][{i}:v]xfade=transition=fade:duration={crossfade}:"
                f"offset={offset}[{out_v}]"
            )
            filter_parts.append(
                f"[{a_label}][{i}:a]acrossfade=d={crossfade}[{out_a}]"
            )
            v_label = out_v
            a_label = out_a
            run_len = run_len + float(durs[i]) - crossfade

        filter_complex = ";".join(filter_parts)
        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            f"[{v_label}]",
            "-map",
            f"[{a_label}]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            str(output_path),
        ]
        self._run(cmd)
        return output_path

    @staticmethod
    def _run(cmd: list[str]) -> None:
        try:
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=3600,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("ffmpeg not found on PATH") from exc
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or exc.stdout or "")[-8000:]
            logger.error("ffmpeg failed: %s", tail)
            raise RuntimeError(f"ffmpeg failed: {tail}") from exc
