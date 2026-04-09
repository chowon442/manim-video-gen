#!/usr/bin/env python3
"""Validate ElevenLabs Korean math narration + timestamp payload (Phase 1-2)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running without editable install
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from manim_video_gen.config import get_settings
from manim_video_gen.tts.elevenlabs import ElevenLabsTTS


SAMPLE_PHRASES = [
    "엑스 제곱 더하기 이 엑스 더하기 일은 영입니다.",
    "이 이차 방정식을 인수 분해하면 완전 제곱식이 됩니다.",
    "따라서 엑스는 마이너스 일입니다.",
]


async def main() -> int:
    settings = get_settings()
    settings.require_elevenlabs()
    tts = ElevenLabsTTS(settings)
    out_dir = _ROOT / "artifacts" / "tts_validation"
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, text in enumerate(SAMPLE_PHRASES):
        path = out_dir / f"sample_{i}.wav"
        result = await tts.synthesize(text, output_path=path)
        print(f"[{i}] wrote {result.audio_path} ({result.duration_seconds:.2f}s)")
        print(f"    timestamps entries: {len(result.word_timestamps)}")
        if result.word_timestamps[:3]:
            print(f"    first: {result.word_timestamps[:3]}")

    print("\nListen to WAV files under artifacts/tts_validation and decide if ElevenLabs is acceptable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
