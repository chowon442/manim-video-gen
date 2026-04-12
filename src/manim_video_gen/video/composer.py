"""FFmpeg-based audio/video merge and concatenation."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from manim_video_gen.exceptions import CompositionError

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
        subtitle_path: Path | None = None,
        subtitle_safe_area_px: int = 0,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        video_path = Path(video_path).resolve()
        audio_path = Path(audio_path).resolve()
        output_path = Path(output_path).resolve()
        safe_px = max(0, int(subtitle_safe_area_px))

        if subtitle_path is not None:
            sp = Path(subtitle_path).resolve()
            if not sp.is_file():
                raise FileNotFoundError(f"Subtitle file not found: {sp}")
            # Use basename + cwd so Windows paths with spaces/colons work in -vf ass=
            if safe_px > 0:
                vf = (
                    f"scale=iw:ih-{safe_px}:flags=lanczos,"
                    f"pad=iw:ih+{safe_px}:0:0:black,"
                    f"ass={sp.name}"
                )
            else:
                vf = f"ass={sp.name}"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-vf",
                vf,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
            self._run(cmd, cwd=str(sp.parent))
            return output_path

        if safe_px > 0:
            vf = f"scale=iw:ih-{safe_px}:flags=lanczos,pad=iw:ih+{safe_px}:0:0:black"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-vf",
                vf,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
            self._run(cmd)
            return output_path

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
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        self._run(cmd)
        return output_path

    def mix_background_music(
        self,
        *,
        video_path: Path,
        bgm_path: Path,
        output_path: Path,
        bgm_volume: float = 0.2,
    ) -> Path:
        """Mix a BGM track under existing video audio (short BGM loops)."""
        video_path = Path(video_path).resolve()
        bgm_path = Path(bgm_path).resolve()
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not bgm_path.is_file():
            raise FileNotFoundError(f"BGM file not found: {bgm_path}")
        vol = max(0.01, min(float(bgm_volume), 1.0))
        filter_complex = (
            f"[1:a]volume={vol:.3f},aloop=loop=-1:size=2e+09[bm];"
            "[0:a][bm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(bgm_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        self._run(cmd)
        return output_path

    def concat_audio(self, audio_paths: list[Path], output_path: Path) -> Path:
        """Concatenate audio files (WAV/MP3/etc.) into one track via FFmpeg concat demuxer."""
        if not audio_paths:
            raise ValueError("No audio files to concatenate")
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        paths = [Path(p).resolve() for p in audio_paths]
        for p in paths:
            if not p.is_file():
                raise FileNotFoundError(f"Audio file not found: {p}")

        if len(paths) == 1:
            import shutil

            shutil.copy2(paths[0], output_path)
            return output_path

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            for p in paths:
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
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_path),
            ]
            self._run(cmd)
        finally:
            list_path.unlink(missing_ok=True)
        return output_path

    def generate_silence_audio(self, *, duration: float, output_path: Path) -> Path:
        """Generate silent AAC audio for bridge clips."""
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dur = max(0.05, float(duration))
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-t",
            f"{dur:.3f}",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]
        self._run(cmd)
        return output_path

    def compose_final(self, merged_paths: list[Path], output_path: Path) -> Path:
        """세그먼트별 병합 파일들을 받아 crossfade를 적용하며 최종 영상을 생성한다."""
        return self.concat_segments(merged_paths, output_path)

    def compose_final_with_bridges(
        self,
        merged_paths: list[Path],
        output_path: Path,
        *,
        bridge_specs: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Compose final video with optional semantic bridge transitions.

        Current safe implementation attempts bridge specs in caller,
        but always falls back to standard concat in this method.
        """
        _ = bridge_specs
        return self.compose_final(merged_paths, output_path)

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
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
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
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
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
            filter_parts.append(f"[{a_label}][{i}:a]acrossfade=d={crossfade}[{out_a}]")
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
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output_path),
        ]
        self._run(cmd)
        return output_path

    @staticmethod
    def _run(cmd: list[str], *, cwd: str | None = None) -> None:
        try:
            completed = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=3600,
                cwd=cwd,
            )
        except FileNotFoundError as exc:
            raise CompositionError(
                "ffmpeg not found on PATH",
                stage="compose",
                detail=str(exc),
            ) from exc
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or exc.stdout or "")[-8000:]
            logger.error("ffmpeg failed: %s", tail)
            raise CompositionError(
                "ffmpeg failed",
                stage="compose",
                detail=tail,
            ) from exc
