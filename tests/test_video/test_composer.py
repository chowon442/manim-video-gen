"""VideoComposer helper tests."""

import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from manim_video_gen.video.composer import VideoComposer


def test_concat_audio_single_file_copies(tmp_path: Path):
    src = tmp_path / "only.wav"
    src.write_bytes(b"RIFF" + b"\x00" * 100)
    out = tmp_path / "out.m4a"
    composer = VideoComposer(crossfade_duration=0.25)
    result = composer.concat_audio([src], out)
    assert result == out
    assert out.is_file()
    assert out.read_bytes() == src.read_bytes()


def test_merge_segment_includes_safe_area_filter_when_subtitle_present(tmp_path: Path):
    composer = VideoComposer(crossfade_duration=0.25)
    video = tmp_path / "v.mp4"
    audio = tmp_path / "a.wav"
    sub = tmp_path / "s.ass"
    out = tmp_path / "o.mp4"
    video.write_bytes(b"x")
    audio.write_bytes(b"y")
    sub.write_text("dummy", encoding="utf-8")

    with patch.object(VideoComposer, "_run") as run_mock:
        composer.merge_segment(
            video_path=video,
            audio_path=audio,
            output_path=out,
            subtitle_path=sub,
            subtitle_safe_area_px=160,
        )

    cmd = run_mock.call_args[0][0]
    vf = cmd[cmd.index("-vf") + 1]
    assert "scale=iw:ih-160" in vf
    assert "pad=iw:ih+160" in vf
    assert "ass=s.ass" in vf


def test_generate_silence_audio_builds_ffmpeg_command(tmp_path: Path):
    composer = VideoComposer(crossfade_duration=0.25)
    out = tmp_path / "silence.m4a"

    with patch.object(VideoComposer, "_run") as run_mock:
        composer.generate_silence_audio(duration=0.7, output_path=out)

    cmd = run_mock.call_args[0][0]
    assert cmd[0] == "ffmpeg"
    assert "anullsrc=r=24000:cl=mono" in cmd
    assert "-t" in cmd
    assert str(out.resolve()) == cmd[-1]


def test_compose_final_with_bridges_falls_back_to_compose_final(tmp_path: Path):
    composer = VideoComposer(crossfade_duration=0.0)
    seg = tmp_path / "seg.mp4"
    seg.write_bytes(b"x")
    out = tmp_path / "out.mp4"

    with patch.object(VideoComposer, "compose_final") as compose_mock:
        compose_mock.return_value = out
        result = composer.compose_final_with_bridges(
            [seg],
            out,
            bridge_specs=[{"from_segment_id": 0, "to_segment_id": 1}],
        )

    compose_mock.assert_called_once_with([seg], out)
    assert result == out


def test_concat_segments_normalizes_mismatched_audio_specs_before_concat(
    tmp_path: Path,
):
    composer = VideoComposer(crossfade_duration=0.0)
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    out = tmp_path / "out.mp4"
    a.write_bytes(b"a")
    b.write_bytes(b"b")

    def _fake_run(cmd, **kwargs):
        if cmd[0] != "ffprobe":
            raise AssertionError(f"unexpected subprocess.run call: {cmd}")
        target = Path(cmd[-1])
        payload = {
            "streams": [
                {
                    "sample_rate": "24000",
                    "channels": 1,
                }
            ]
        }
        if target == b:
            payload = {
                "streams": [
                    {
                        "sample_rate": "48000",
                        "channels": 2,
                    }
                ]
            }
        return subprocess.CompletedProcess(
            cmd, 0, stdout=json.dumps(payload), stderr=""
        )

    with patch("manim_video_gen.video.composer.subprocess.run", side_effect=_fake_run):
        with patch.object(VideoComposer, "_run") as run_mock:
            composer.concat_segments([a, b], out)

    calls = [c[0][0] for c in run_mock.call_args_list]
    assert any(cmd[0] == "ffmpeg" and "-f" in cmd and "concat" in cmd for cmd in calls)
    assert any(
        cmd[0] == "ffmpeg"
        and "-ar" in cmd
        and cmd[cmd.index("-ar") + 1] == "24000"
        and "-ac" in cmd
        and cmd[cmd.index("-ac") + 1] == "1"
        for cmd in calls
    )


def test_concat_segments_inter_scene_gap_extends_tail_and_skips_crossfade(
    tmp_path: Path,
):
    a = tmp_path / "a.mp4"
    b = tmp_path / "b.mp4"
    out = tmp_path / "out.mp4"
    a.write_bytes(b"a")
    b.write_bytes(b"b")

    composer = VideoComposer(crossfade_duration=0.25, inter_scene_gap_seconds=0.4)

    def _fake_run(cmd, **kwargs):
        if cmd[0] != "ffprobe":
            raise AssertionError(f"unexpected subprocess.run call: {cmd}")
        target = Path(cmd[-1])
        payload = {
            "streams": [
                {
                    "sample_rate": "48000",
                    "channels": 2,
                }
            ]
        }
        if target in (a, b):
            pass
        else:
            raise AssertionError(f"unexpected ffprobe target: {target}")
        return subprocess.CompletedProcess(
            cmd, 0, stdout=json.dumps(payload), stderr=""
        )

    with patch("manim_video_gen.video.composer.subprocess.run", side_effect=_fake_run):
        with patch.object(composer, "extend_segment_tail_with_last_frame_hold") as hold_mock:

            def _touch_hold(**kw):
                Path(kw["output_path"]).write_bytes(b"hold")

            hold_mock.side_effect = _touch_hold
            with patch.object(composer, "_concat_demuxer") as demux_mock:
                demux_mock.return_value = out
                result = composer.concat_segments([a, b], out)

    assert result == out
    hold_mock.assert_called_once()
    demux_mock.assert_called_once()
    prepared = demux_mock.call_args[0][0]
    assert len(prepared) == 2
    assert prepared[1] == b.resolve()
    assert hold_mock.call_args[1]["hold_seconds"] == 0.4
