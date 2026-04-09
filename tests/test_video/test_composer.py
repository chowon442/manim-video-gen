"""VideoComposer helper tests."""

from pathlib import Path

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
