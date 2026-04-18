"""Application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# CWD와 무관하게 저장소 루트의 .env를 읽음 (예: scripts/에서 스크립트 실행 시에도 Voice ID 적용)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_DOTENV = _REPO_ROOT / ".env"
_ENV_FILE = str(_REPO_DOTENV) if _REPO_DOTENV.is_file() else ".env"


class Settings(BaseSettings):
    """Runtime configuration for manim-video-gen."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    openrouter_api_key: str = Field(
        default="",
        validation_alias="OPENROUTER_API_KEY",
    )
    openrouter_retries: int = Field(
        default=2,
        validation_alias="MANIM_VIDEO_GEN_OPENROUTER_RETRIES",
        description="Retry attempts for transient OpenRouter/provider errors.",
    )
    openrouter_retry_base_seconds: float = Field(
        default=1.5,
        validation_alias="MANIM_VIDEO_GEN_OPENROUTER_RETRY_BASE_SECONDS",
        description="Base backoff seconds for OpenRouter retries.",
    )
    openrouter_retry_max_seconds: float = Field(
        default=15.0,
        validation_alias="MANIM_VIDEO_GEN_OPENROUTER_RETRY_MAX_SECONDS",
        description="Maximum backoff seconds for OpenRouter retries.",
    )
    llm_json_parse_max_attempts: int = Field(
        default=3,
        ge=1,
        validation_alias="MANIM_VIDEO_GEN_LLM_JSON_PARSE_MAX_ATTEMPTS",
        description=(
            "Max completion rounds when JSON parse or schema validation fails "
            "(each round is a new model completion)."
        ),
    )
    elevenlabs_api_key: str = Field(
        default="",
        validation_alias="ELEVENLABS_API_KEY",
    )
    elevenlabs_voice_id: str | None = Field(
        default=None,
        validation_alias="ELEVENLABS_VOICE_ID",
    )
    # If true: try /with-timestamps first, then fall back to standard TTS on 402/403 etc.
    # If false: only standard /text-to-speech (no word timestamps; duration still via ffprobe).
    elevenlabs_try_timestamps: bool = Field(
        default=True,
        validation_alias="MANIM_VIDEO_GEN_ELEVENLABS_TRY_TIMESTAMPS",
    )

    model_solve: str = Field(
        default="openai/gpt-4o",
        validation_alias="MANIM_VIDEO_GEN_MODEL_SOLVE",
    )
    model_script: str = Field(
        default="openai/gpt-4o",
        validation_alias="MANIM_VIDEO_GEN_MODEL_SCRIPT",
    )
    model_manim: str = Field(
        default="openai/gpt-4o",
        validation_alias="MANIM_VIDEO_GEN_MODEL_MANIM",
    )

    manim_quality_low: Literal["l", "m", "h", "p", "k"] = Field(
        default="l",
        validation_alias="MANIM_VIDEO_GEN_MANIM_QUALITY_LOW",
    )
    manim_quality_high: Literal["l", "m", "h", "p", "k"] = Field(
        default="h",
        validation_alias="MANIM_VIDEO_GEN_MANIM_QUALITY_HIGH",
    )

    crossfade_duration: float = Field(
        default=0.2,
        validation_alias="MANIM_VIDEO_GEN_CROSSFADE_DURATION",
    )
    inter_scene_gap_seconds: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="MANIM_VIDEO_GEN_INTER_SCENE_GAP_SECONDS",
        description=(
            "After each scene except the last, hold the final video frame and pad silence "
            "for this many seconds before the next scene (ffmpeg tpad+apad). "
            "When > 0, crossfade is not applied (simple concat). Default 0 disables."
        ),
    )
    scene_bridge_enabled: bool = Field(
        default=False,
        validation_alias="MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED",
        description="Enable semantic bridge transition generation between adjacent rendered chains/scenes.",
    )
    disable_equation_chain: bool = Field(
        default=True,
        validation_alias="MANIM_VIDEO_GEN_DISABLE_EQUATION_CHAIN",
        description=(
            "Disable merged equation-chain rendering and render each segment independently. "
            "Recommended when prioritizing no-overlap stability over transition continuity."
        ),
    )
    disable_prev_scene_state: bool = Field(
        default=True,
        validation_alias="MANIM_VIDEO_GEN_DISABLE_PREV_SCENE_STATE",
        description=(
            "Do not inject prev_scene_state objects into standalone scenes. "
            "Helps prevent visual overlaps caused by stale carry-over state."
        ),
    )

    tts_provider: Literal["elevenlabs", "azure", "replicate", "inworld"] = Field(
        default="elevenlabs",
        validation_alias="MANIM_VIDEO_GEN_TTS_PROVIDER",
    )
    dialogue_qa_enabled: bool = Field(
        default=False,
        validation_alias="MANIM_VIDEO_GEN_DIALOGUE_QA_ENABLED",
        description="Enable dialogue mode with student questions and teacher answers.",
    )

    replicate_api_token: str = Field(
        default="",
        validation_alias="REPLICATE_API_TOKEN",
    )
    replicate_tts_mode: Literal["custom_voice", "voice_clone", "voice_design"] = Field(
        default="custom_voice",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_MODE",
    )
    replicate_tts_speaker: str = Field(
        default="Aiden",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_SPEAKER",
    )
    replicate_tts_language: str = Field(
        default="auto",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_LANGUAGE",
    )
    replicate_tts_voice_description: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_VOICE_DESC",
    )
    replicate_tts_reference_audio: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_REF_AUDIO",
    )
    replicate_tts_reference_text: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_REF_TEXT",
    )
    replicate_tts_style_instruction: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_STYLE",
    )
    replicate_student_tts_speaker: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_SPEAKER",
    )
    replicate_student_tts_language: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_LANGUAGE",
    )
    replicate_student_tts_style_instruction: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_STUDENT_TTS_STYLE",
    )
    replicate_tts_min_interval_seconds: float = Field(
        default=0.0,
        validation_alias="MANIM_VIDEO_GEN_REPLICATE_TTS_MIN_INTERVAL",
        description=(
            "Minimum seconds between Replicate prediction calls. "
            "Use ~11 when account credit is under $5 (6/min limit) to avoid 429."
        ),
    )
    azure_speech_key: str = Field(
        default="",
        validation_alias="AZURE_SPEECH_KEY",
    )
    azure_speech_region: str = Field(
        default="",
        validation_alias="AZURE_SPEECH_REGION",
    )
    azure_tts_voice: str = Field(
        default="ko-KR-SunHiNeural",
        validation_alias="MANIM_VIDEO_GEN_AZURE_TTS_VOICE",
    )

    inworld_tts_api_key: str = Field(
        default="",
        validation_alias="INWORLD_TTS_API_KEY",
    )
    inworld_tts_model_id: str = Field(
        default="inworld-tts-1.5-max",
        validation_alias="MANIM_VIDEO_GEN_INWORLD_TTS_MODEL",
    )
    inworld_tts_voice_id: str = Field(
        default="Hyunwoo",
        validation_alias="MANIM_VIDEO_GEN_INWORLD_TTS_VOICE",
    )
    inworld_student_tts_voice_id: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_INWORLD_STUDENT_TTS_VOICE",
    )
    inworld_tts_speaking_rate: float = Field(
        default=1.0,
        validation_alias="MANIM_VIDEO_GEN_INWORLD_TTS_SPEAKING_RATE",
    )
    inworld_tts_temperature: float = Field(
        default=1.0,
        validation_alias="MANIM_VIDEO_GEN_INWORLD_TTS_TEMPERATURE",
    )
    inworld_tts_timestamp_type: Literal["NONE", "WORD"] = Field(
        default="NONE",
        validation_alias="MANIM_VIDEO_GEN_INWORLD_TTS_TIMESTAMP_TYPE",
        description="Inworld non-streaming: WORD enables timestampInfo (not mapped to word_timestamps yet).",
    )

    burn_subtitles: bool = Field(
        default=True,
        validation_alias="MANIM_VIDEO_GEN_BURN_SUBTITLES",
    )

    subtitle_max_chars: int = Field(
        default=56,
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_MAX_CHARS",
    )
    subtitle_wrap_mode: Literal["auto", "char"] = Field(
        default="auto",
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_WRAP_MODE",
        description="Subtitle line-wrapping mode. auto lets ASS renderer wrap by width, char inserts manual \\N by character count.",
    )
    subtitle_font_size: int = Field(
        default=42,
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_FONT_SIZE",
    )
    subtitle_margin_l: int = Field(
        default=56,
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_MARGIN_L",
    )
    subtitle_margin_r: int = Field(
        default=56,
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_MARGIN_R",
    )
    subtitle_margin_v: int = Field(
        default=44,
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_MARGIN_V",
    )
    subtitle_safe_area_px: int = Field(
        default=0,
        validation_alias="MANIM_VIDEO_GEN_SUBTITLE_SAFE_AREA_PX",
        description=(
            "Reserve bottom area for subtitles by shrinking video vertically and padding black bar. "
            "0 disables this behavior."
        ),
    )

    consistency_mode: Literal["off", "warn", "error"] = Field(
        default="warn",
        validation_alias="MANIM_VIDEO_GEN_CONSISTENCY_MODE",
    )
    consistency_auto_repair: bool = Field(
        default=True,
        validation_alias="MANIM_VIDEO_GEN_CONSISTENCY_AUTO_REPAIR",
        description="When consistency_mode=error, try script-level auto-repair loop before failing.",
    )
    consistency_auto_repair_max_attempts: int = Field(
        default=2,
        validation_alias="MANIM_VIDEO_GEN_CONSISTENCY_AUTO_REPAIR_MAX_ATTEMPTS",
        description="Maximum additional scriptify attempts for consistency auto-repair.",
    )

    script_quality_enabled: bool = Field(
        default=False,
        validation_alias="MANIM_VIDEO_GEN_SCRIPT_QUALITY_ENABLED",
        description="Enable script-level quality guard (score + minimal-change repair loop).",
    )
    script_quality_profile: Literal["quality_first", "balanced", "stable"] = Field(
        default="quality_first",
        validation_alias="MANIM_VIDEO_GEN_SCRIPT_QUALITY_PROFILE",
        description="Quality scoring profile. quality_first emphasizes explanation quality.",
    )
    script_quality_min_total: float = Field(
        default=0.82,
        ge=0.0,
        le=1.0,
        validation_alias="MANIM_VIDEO_GEN_SCRIPT_QUALITY_MIN_TOTAL",
        description="Minimum acceptable script quality score (0~1).",
    )
    script_quality_max_attempts: int = Field(
        default=2,
        ge=0,
        validation_alias="MANIM_VIDEO_GEN_SCRIPT_QUALITY_MAX_ATTEMPTS",
        description="Maximum additional script repair attempts for quality guard.",
    )
    script_quality_max_segments_per_attempt: int = Field(
        default=2,
        ge=0,
        validation_alias="MANIM_VIDEO_GEN_SCRIPT_QUALITY_MAX_SEGMENTS_PER_ATTEMPT",
        description="Maximum number of segment IDs that may change per quality-repair attempt.",
    )
    script_quality_fail_on_soft_after_max: bool = Field(
        default=False,
        validation_alias="MANIM_VIDEO_GEN_SCRIPT_QUALITY_FAIL_ON_SOFT_AFTER_MAX",
        description="If true, fail pipeline when soft quality issues remain after max attempts.",
    )

    diagnostic_dump: bool = Field(
        default=False,
        validation_alias="MANIM_VIDEO_GEN_DIAGNOSTIC_DUMP",
    )
    keep_workspace: bool = Field(
        default=False,
        validation_alias="MANIM_VIDEO_GEN_KEEP_WORKSPACE",
    )

    video_width: int = Field(
        default=0,
        validation_alias="MANIM_VIDEO_GEN_VIDEO_WIDTH",
        description="0 = Manim default",
    )
    video_height: int = Field(
        default=0,
        validation_alias="MANIM_VIDEO_GEN_VIDEO_HEIGHT",
    )
    video_fps: int = Field(
        default=0,
        validation_alias="MANIM_VIDEO_GEN_VIDEO_FPS",
    )

    bgm_path: str = Field(
        default="",
        validation_alias="MANIM_VIDEO_GEN_BGM_PATH",
    )
    bgm_volume: float = Field(
        default=0.2,
        validation_alias="MANIM_VIDEO_GEN_BGM_VOLUME",
    )

    llm_timeout_seconds: float = 120.0
    tts_timeout_seconds: float = 120.0
    manim_render_timeout_seconds: float = 600.0

    def require_openrouter(self) -> None:
        if not self.openrouter_api_key.strip():
            raise ValueError("OPENROUTER_API_KEY is not set")

    def require_elevenlabs(self) -> None:
        if not self.elevenlabs_api_key.strip():
            raise ValueError("ELEVENLABS_API_KEY is not set")

    def require_replicate(self) -> None:
        if not self.replicate_api_token.strip():
            raise ValueError("REPLICATE_API_TOKEN is not set")


def get_settings() -> Settings:
    return Settings()


def project_root() -> Path:
    """Repository root (parent of src/)."""
    return Path(__file__).resolve().parents[2]
