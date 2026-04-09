#!/usr/bin/env python3
"""Minimal OpenRouter connectivity check (Phase 1-4c)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from manim_video_gen.config import get_settings
from manim_video_gen.llm.client import OpenRouterClient


async def main() -> int:
    settings = get_settings()
    settings.require_openrouter()
    client = OpenRouterClient(settings)
    text = await client.complete_text(
        model=settings.model_solve,
        messages=[{"role": "user", "content": 'Reply with exactly: "pong"'}],
        temperature=0,
    )
    print(text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
