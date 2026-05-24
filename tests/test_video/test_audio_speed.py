"""Tests for video.audio_speed module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from manim_video_gen.video.audio_speed import (
    SpeedResult,
    speed_up_audio,
    tempo_filter_args,
)


class TestTempoFilterArgs:
    """Unit tests for tempo_filter_args decomposition."""

    def test_rate_1_returns_empty(self):
        assert tempo_filter_args(1.0) == []

    def test_rate_within_range(self):
        assert tempo_filter_args(1.25) == ["atempo=1.25"]
        assert tempo_filter_args(0.5) == ["atempo=0.5"]
        assert tempo_filter_args(2.0) == ["atempo=2"]

    def test_rate_above_max_chains(self):
        result = tempo_filter_args(4.0)
        assert len(result) == 2
        assert result[0] == "atempo=2"
        # 4.0 / 2.0 = 2.0
        assert result[1] == "atempo=2"

    def test_rate_below_min_chains(self):
        result = tempo_filter_args(0.25)
        assert len(result) == 2
        assert result[0] == "atempo=0.5"
        # 0.25 / 0.5 = 0.5
        assert result[1] == "atempo=0.5"

    def test_rate_slightly_above_max(self):
        result = tempo_filter_args(2.5)
        assert len(result) == 2
        assert result[0] == "atempo=2"
        # 2.5 / 2.0 = 1.25
        assert result[1] == "atempo=1.25"

    def test_rate_slightly_below_min(self):
        result = tempo_filter_args(0.4)
        assert len(result) == 2
        assert result[0] == "atempo=0.5"
        # 0.4 / 0.5 = 0.8
        assert result[1] == "atempo=0.8"

    def test_rate_3_chains(self):
        result = tempo_filter_args(3.0)
        assert len(result) == 2
        assert result[0] == "atempo=2"
        # 3.0 / 2.0 = 1.5
        assert result[1] == "atempo=1.5"

    def test_rate_8_chains_three(self):
        result = tempo_filter_args(8.0)
        assert len(result) == 3
        assert result[0] == "atempo=2"
        assert result[1] == "atempo=2"
        assert result[2] == "atempo=2"

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="positive"):
            tempo_filter_args(-1.0)

    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="positive"):
            tempo_filter_args(0.0)


class TestSpeedUpAudio:
    """Tests for speed_up_audio ffmpeg wrapper."""

    def test_rate_1_copies_file(self, tmp_path: Path):
        src = tmp_path / "input.wav"
        src.write_bytes(b"RIFF" + b"\x00" * 100)
        out = tmp_path / "output.wav"

        def _fake_run(cmd, **kwargs):
            if cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd, 0,
                    stdout=json.dumps({"format": {"duration": "5.0"}}),
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("manim_video_gen.video.audio_speed.subprocess.run", side_effect=_fake_run):
            result = speed_up_audio(src, 1.0, out)

        assert result.audio_path == out
        assert result.duration_seconds == 5.0
        assert out.is_file()

    def test_rate_125_calls_ffmpeg_with_atempo(self, tmp_path: Path):
        src = tmp_path / "input.wav"
        src.write_bytes(b"RIFF" + b"\x00" * 100)
        out = tmp_path / "output.wav"

        calls: list[list[str]] = []

        def _fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "ffprobe":
                if "input.wav" in str(cmd):
                    return subprocess.CompletedProcess(
                        cmd, 0,
                        stdout=json.dumps({"format": {"duration": "10.0"}}),
                        stderr="",
                    )
                return subprocess.CompletedProcess(
                    cmd, 0,
                    stdout=json.dumps({"format": {"duration": "8.0"}}),
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("manim_video_gen.video.audio_speed.subprocess.run", side_effect=_fake_run):
            result = speed_up_audio(src, 1.25, out)

        ffmpeg_calls = [c for c in calls if c[0] == "ffmpeg"]
        assert len(ffmpeg_calls) == 1
        cmd = ffmpeg_calls[0]
        af_idx = cmd.index("-af")
        assert cmd[af_idx + 1] == "atempo=1.25"
        assert result.duration_seconds == 8.0

    def test_rate_25_chains_atempo(self, tmp_path: Path):
        src = tmp_path / "input.wav"
        src.write_bytes(b"RIFF" + b"\x00" * 100)
        out = tmp_path / "output.wav"

        calls: list[list[str]] = []

        def _fake_run(cmd, **kwargs):
            calls.append(cmd)
            if cmd[0] == "ffprobe":
                return subprocess.CompletedProcess(
                    cmd, 0,
                    stdout=json.dumps({"format": {"duration": "4.0"}}),
                    stderr="",
                )
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with patch("manim_video_gen.video.audio_speed.subprocess.run", side_effect=_fake_run):
            result = speed_up_audio(src, 2.5, out)

        ffmpeg_calls = [c for c in calls if c[0] == "ffmpeg"]
        cmd = ffmpeg_calls[0]
        af_idx = cmd.index("-af")
        assert "atempo=2" in cmd[af_idx + 1]
        assert "atempo=1.25" in cmd[af_idx + 1]

    def test_missing_input_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            speed_up_audio(tmp_path / "missing.wav", 1.25, tmp_path / "out.wav")

    def test_speed_result_dataclass(self):
        result = SpeedResult(audio_path=Path("/tmp/test.wav"), duration_seconds=5.0)
        assert result.audio_path == Path("/tmp/test.wav")
        assert result.duration_seconds == 5.0
