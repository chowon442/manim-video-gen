"""Select TTS implementation from settings."""

from __future__ import annotations

from manim_video_gen.config import Settings
from manim_video_gen.tts.azure_tts import AzureSpeechTTS
from manim_video_gen.tts.base import TTSProvider
from manim_video_gen.tts.elevenlabs import ElevenLabsTTS
from manim_video_gen.tts.replicate_tts import ReplicateTTS


def get_tts_provider(settings: Settings) -> TTSProvider:
    provider = (settings.tts_provider or "elevenlabs").strip().lower()
    if provider == "azure":
        return AzureSpeechTTS(settings)
    if provider == "replicate":
        return ReplicateTTS(settings)
    return ElevenLabsTTS(settings)
