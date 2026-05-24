"""FFmpeg atempo-based audio speed adjustment."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_ATEMPO_MIN = 0.5
_ATEMPO_MAX = 2.0


@dataclass(frozen=True, slots=True)
class SpeedResult:
    """Result of speeding up an audio file."""

    audio_path: Path
    duration_seconds: float


def tempo_filter_args(rate: float) -> list[str]:
    """Decompose *rate* into chained ffmpeg ``atempo`` filter arguments.

    ``atempo`` only accepts values in [0.5, 2.0].  Rates outside that range
    are decomposed into a chain (e.g. 4.0 → ``["atempo=2.0", "atempo=2.0"]``).

    Returns a list of ``"atempo=<value>"`` strings suitable for
    ``-filter_complex`` or ``-af`` chaining.

    Raises ``ValueError`` when *rate* is not positive.
    """
    if rate <= 0:
        raise ValueError(f"rate must be positive, got {rate}")

    if abs(rate - 1.0) < 1e-9:
        return []

    args: list[str] = []
    remaining = rate

    if remaining > _ATEMPO_MAX:
        while remaining > _ATEMPO_MAX + 1e-9:
            args.append(f"atempo={_ATEMPO_MAX:.6g}")
            remaining /= _ATEMPO_MAX
        args.append(f"atempo={remaining:.6g}")
    elif remaining < _ATEMPO_MIN:
        while remaining < _ATEMPO_MIN - 1e-9:
            args.append(f"atempo={_ATEMPO_MIN:.6g}")
            remaining /= _ATEMPO_MIN
        args.append(f"atempo={remaining:.6g}")
    else:
        args.append(f"atempo={remaining:.6g}")

    return args


def _ffprobe_duration(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    meta = json.loads(completed.stdout)
    return float(meta["format"]["duration"])


def speed_up_audio(
    input_path: Path | str,
    rate: float,
    output_path: Path | str,
) -> SpeedResult:
    """Speed up an audio file using ffmpeg ``atempo`` filter.

    When *rate* is 1.0 the file is copied unchanged.  The output duration
    is measured via ``ffprobe`` and returned in :class:`SpeedResult`.

    Raises ``ValueError`` if *rate* is not positive.
    Raises ``FileNotFoundError`` if *input_path* does not exist.
    Raises ``subprocess.CalledProcessError`` on ffmpeg failure.
    """
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    if abs(rate - 1.0) < 1e-9:
        import shutil

        shutil.copy2(input_path, output_path)
        return SpeedResult(
            audio_path=output_path,
            duration_seconds=_ffprobe_duration(output_path),
        )

    filters = tempo_filter_args(rate)
    af = ",".join(filters)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-af", af,
        "-c:a", "pcm_s16le",
        str(output_path),
    ]

    logger.info("speed_up_audio: rate=%.3f af=%s", rate, af)
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)

    duration = _ffprobe_duration(output_path)
    logger.info(
        "speed_up_audio: output=%.3fs (expected ~%.3fs)",
        duration,
        _ffprobe_duration(input_path) / rate,
    )

    return SpeedResult(audio_path=output_path, duration_seconds=duration)
