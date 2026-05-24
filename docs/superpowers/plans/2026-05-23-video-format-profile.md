# VideoFormatProfile + Subtitle PlayRes 동적화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 쇼츠 9:16 세로 영상 포맷 지원을 위한 VideoFormatProfile enum과 동적 PlayRes 설정 기반 마련

**Architecture:** config.py에 VideoFormatProfile enum과 VideoFormatPreset dataclass을 추가하고, subtitle.py의 _build_ass_header가 프로필에 따라 PlayRes를 동적 설정하도록 수정. 기존 landscape 모드는 기본값으로 동일 동작 보장.

**Tech Stack:** Python 3.12, Pydantic, pytest

---

## 파일 구조

- **Modify:** `src/manim_video_gen/config.py` — VideoFormatProfile enum + VideoFormatPreset dataclass 추가
- **Modify:** `src/manim_video_gen/video/subtitle.py` — _build_ass_header에 play_res 파라미터 추가
- **Modify:** `tests/test_video/test_subtitle.py` — 9:16 PlayRes 테스트 추가
- **Modify:** `tests/test_config_defaults.py` — VideoFormatProfile 기본값 테스트 추가

---

### Task 1: VideoFormatProfile enum 및 프리셋 정의

**Files:**
- Modify: `src/manim_video_gen/config.py`

- [ ] **Step 1: VideoFormatProfile enum과 VideoFormatPreset dataclass 작성**

```python
# config.py 상단 (import 영역 아래)에 추가

from dataclasses import dataclass
from enum import Enum


class VideoFormatProfile(str, Enum):
    """비디오 포맷 프로필."""
    LANDSCAPE = "landscape"
    SHORT_9_16 = "short_9_16"


@dataclass(frozen=True)
class VideoFormatPreset:
    """비디오 포맷 프리셋 상수."""
    width: int
    height: int
    safe_zone_top_pct: float   # 상단 safe zone 비율 (0.0~1.0)
    safe_zone_bottom_pct: float  # 하단 safe zone 비율 (0.0~1.0)


FORMAT_PRESETS: dict[VideoFormatProfile, VideoFormatPreset] = {
    VideoFormatProfile.LANDSCAPE: VideoFormatPreset(
        width=1920,
        height=1080,
        safe_zone_top_pct=0.0,
        safe_zone_bottom_pct=0.0,
    ),
    VideoFormatProfile.SHORT_9_16: VideoFormatPreset(
        width=1080,
        height=1920,
        safe_zone_top_pct=0.12,
        safe_zone_bottom_pct=0.20,
    ),
}
```

- [ ] **Step 2: Settings 클래스에 format_profile 필드 추가**

```python
# Settings 클래스 내부에 추가

video_format_profile: VideoFormatProfile = Field(
    default=VideoFormatProfile.LANDSCAPE,
    validation_alias="MANIM_VIDEO_GEN_VIDEO_FORMAT_PROFILE",
    description="비디오 포맷 프로필. landscape(16:9) 또는 short_9_16(9:16).",
)
```

- [ ] **Step 3: 포맷 프로필 관련 헬퍼 메서드 추가**

```python
# Settings 클래스 내부에 추가

def get_format_preset(self) -> VideoFormatPreset:
    """현재 포맷 프로필의 프리셋을 반환."""
    return FORMAT_PRESETS[self.video_format_profile]

def get_resolution(self) -> tuple[int, int]:
    """현재 포맷 프로필의 (width, height) 반환."""
    preset = self.get_format_preset()
    return (preset.width, preset.height)
```

- [ ] **Step 4: 테스트 작성 및 실행**

```python
# tests/test_config_defaults.py에 추가

from manim_video_gen.config import (
    FORMAT_PRESETS,
    VideoFormatPreset,
    VideoFormatProfile,
)


def test_video_format_profile_default_is_landscape(monkeypatch):
    monkeypatch.delenv("MANIM_VIDEO_GEN_VIDEO_FORMAT_PROFILE", raising=False)
    s = Settings()
    assert s.video_format_profile == VideoFormatProfile.LANDSCAPE


def test_video_format_profile_short_9_16(monkeypatch):
    monkeypatch.setenv("MANIM_VIDEO_GEN_VIDEO_FORMAT_PROFILE", "short_9_16")
    s = Settings()
    assert s.video_format_profile == VideoFormatProfile.SHORT_9_16


def test_format_preset_landscape():
    preset = FORMAT_PRESETS[VideoFormatProfile.LANDSCAPE]
    assert preset.width == 1920
    assert preset.height == 1080
    assert preset.safe_zone_top_pct == 0.0
    assert preset.safe_zone_bottom_pct == 0.0


def test_format_preset_short_9_16():
    preset = FORMAT_PRESETS[VideoFormatProfile.SHORT_9_16]
    assert preset.width == 1080
    assert preset.height == 1920
    assert preset.safe_zone_top_pct == 0.12
    assert preset.safe_zone_bottom_pct == 0.20


def test_get_resolution_landscape(monkeypatch):
    monkeypatch.setenv("MANIM_VIDEO_GEN_VIDEO_FORMAT_PROFILE", "landscape")
    s = Settings()
    assert s.get_resolution() == (1920, 1080)


def test_get_resolution_short_9_16(monkeypatch):
    monkeypatch.setenv("MANIM_VIDEO_GEN_VIDEO_FORMAT_PROFILE", "short_9_16")
    s = Settings()
    assert s.get_resolution() == (1080, 1920)
```

실행:
```bash
pytest tests/test_config_defaults.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/manim_video_gen/config.py tests/test_config_defaults.py
git commit -m "feat(config): add VideoFormatProfile enum with landscape/short_9_16 presets"
```

---

### Task 2: Subtitle PlayRes 동적화

**Files:**
- Modify: `src/manim_video_gen/video/subtitle.py:254-276`
- Modify: `tests/test_video/test_subtitle.py`

- [ ] **Step 1: _build_ass_header에 play_res 파라미터 추가**

```python
# subtitle.py의 _build_ass_header 함수 수정

def _build_ass_header(
    *,
    font_size: int,
    margin_l: int,
    margin_r: int,
    margin_v: int,
    play_res_x: int = 1920,
    play_res_y: int = 1080,
) -> str:
    return f"""[Script Info]
Title: manim-video-gen
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {play_res_x}
PlayResY: {play_res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans KR,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,{margin_l},{margin_r},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
```

- [ ] **Step 2: generate_ass_subtitle에 play_res 파라미터 전달**

```python
# generate_ass_subtitle 함수 시그니처 및 호출부 수정

def generate_ass_subtitle(
    narration: str,
    duration_seconds: float,
    output_path: Path,
    *,
    style_name: str = "Default",
    max_chars: int = 56,
    wrap_mode: str = "auto",
    font_size: int = 42,
    margin_l: int = 56,
    margin_r: int = 56,
    margin_v: int = 44,
    play_res_x: int = 1920,
    play_res_y: int = 1080,
) -> Path:
    # ... 기존 코드 ...
    output_path.write_text(
        _build_ass_header(
            font_size=font_size,
            margin_l=margin_l,
            margin_r=margin_r,
            margin_v=margin_v,
            play_res_x=play_res_x,
            play_res_y=play_res_y,
        )
        + dialogue,
        encoding="utf-8",
    )
    return output_path
```

- [ ] **Step 3: generate_chain_ass_subtitle에도 play_res 파라미터 전달**

```python
# generate_chain_ass_subtitle 함수 시그니처 및 호출부 수정

def generate_chain_ass_subtitle(
    narrations: list[str],
    durations: list[float],
    output_path: Path,
    *,
    style_name: str = "Default",
    max_chars: int = 56,
    wrap_mode: str = "auto",
    font_size: int = 42,
    margin_l: int = 56,
    margin_r: int = 56,
    margin_v: int = 44,
    play_res_x: int = 1920,
    play_res_y: int = 1080,
) -> Path:
    # ... 기존 코드 ...
    output_path.write_text(
        _build_ass_header(
            font_size=font_size,
            margin_l=margin_l,
            margin_r=margin_r,
            margin_v=margin_v,
            play_res_x=play_res_x,
            play_res_y=play_res_y,
        )
        + "".join(lines),
        encoding="utf-8",
    )
    return output_path
```

- [ ] **Step 4: 9:16 PlayRes 테스트 작성**

```python
# tests/test_video/test_subtitle.py에 추가

def test_generate_ass_short_9_16_play_res(tmp_path: Path):
    """9:16 포맷에서 PlayRes가 1080×1920으로 설정되어야 함."""
    out = tmp_path / "short.ass"
    generate_ass_subtitle(
        "쇼츠 자막 테스트",
        3.0,
        out,
        play_res_x=1080,
        play_res_y=1920,
    )
    text = out.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in text
    assert "PlayResY: 1920" in text


def test_generate_chain_ass_short_9_16_play_res(tmp_path: Path):
    """체인 자막에서도 9:16 PlayRes가 적용되어야 함."""
    out = tmp_path / "chain_short.ass"
    generate_chain_ass_subtitle(
        ["첫 줄", "둘째"],
        [2.0, 3.0],
        out,
        play_res_x=1080,
        play_res_y=1920,
    )
    text = out.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in text
    assert "PlayResY: 1920" in text


def test_generate_ass_default_play_res_is_landscape(tmp_path: Path):
    """기본 PlayRes는 1920×1080(landscape)이어야 함."""
    out = tmp_path / "default.ass"
    generate_ass_subtitle("기본 자막", 2.0, out)
    text = out.read_text(encoding="utf-8")
    assert "PlayResX: 1920" in text
    assert "PlayResY: 1080" in text
```

- [ ] **Step 5: 전체 테스트 실행 및 regression 확인**

```bash
pytest tests/test_video/test_subtitle.py -v
pytest tests/test_config_defaults.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/manim_video_gen/video/subtitle.py tests/test_video/test_subtitle.py
git commit -m "feat(subtitle): make PlayRes dynamic via play_res_x/y parameters"
```

---

### Task 3: 통합 검증 및 regression 테스트

- [ ] **Step 1: 전체 테스트 스위트 실행**

```bash
pytest tests/ -v
```

- [ ] **Step 2: worktree에서 main branch로 cherry-pack 또는 merge 준비**

```bash
git log --oneline -5
```
