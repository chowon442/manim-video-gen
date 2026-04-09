"""TTS provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from manim_video_gen.models.script import TTSResult


class TTSProvider(ABC):
    """Pluggable text-to-speech (WAV + duration + optional word alignment)."""

    @abstractmethod
    async def synthesize(self, text: str, *, output_path: Path) -> TTSResult:
        """Synthesize speech to a WAV file and return metadata."""
