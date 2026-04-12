from pathlib import Path

from manim_video_gen.tools.verify_render_regressions import (
    _frame_signals,
    _print_report,
)


def test_frame_signals_parses_outputs(monkeypatch, tmp_path: Path):
    frame = tmp_path / "f.png"
    frame.write_bytes(b"png")

    def _fake_run(cmd: list[str]) -> str:
        s = " ".join(cmd)
        if "signalstats" in s:
            return "lavfi.signalstats.YHIGH=252\n"
        if "edgedetect" in s:
            return "blackframe pblack:12.50\n"
        return ""

    monkeypatch.setattr(
        "manim_video_gen.tools.verify_render_regressions._run", _fake_run
    )

    sig = _frame_signals(frame, 48.0)
    assert sig.t == 48.0
    assert 0.995 > sig.bright_box_ratio > 0.98
    assert sig.overlap_ratio == 0.875


def test_print_report_fails_when_suspicious(capsys):
    from manim_video_gen.tools.verify_render_regressions import FrameSignal

    code = _print_report(
        Path("artifacts/final_bridge_verify.mp4"),
        [FrameSignal(t=48.0, bright_box_ratio=0.99, overlap_ratio=0.91)],
    )
    out = capsys.readouterr().out
    assert "OVERLAP_SUSPECT" in out
    assert "BRIGHT_BOX_SUSPECT" in out
    assert code == 2
