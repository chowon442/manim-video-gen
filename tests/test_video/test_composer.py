"""VideoComposer helper tests."""

from pathlib import Path
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
    assert "anullsrc=r=48000:cl=stereo" in cmd
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
