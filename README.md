# manim-video-gen

수학 문제를 입력받아 풀이 해설 동영상을 자동 생성하는 파이프라인입니다.

## 요구 사항

- Python 3.11+
- FFmpeg / ffprobe (시스템 PATH; ElevenLabs MP3→WAV 변환 및 합성에 필요)
- LaTeX (Manim `MathTex`용, TeX Live 등)
- `OPENROUTER_API_KEY`
- TTS: 기본 `ELEVENLABS_API_KEY` 또는 `MANIM_VIDEO_GEN_TTS_PROVIDER=azure` 시 `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`

OpenRouter는 공식 OpenAI 호환 REST(`httpx`)로 호출합니다. 모델은 `.env`의 `MANIM_VIDEO_GEN_MODEL_*`로 지정합니다.

일시적 OpenRouter/provider 오류(예: 429, 5xx, provider code 524)는 아래 설정으로 동일 요청 재시도합니다.
- `MANIM_VIDEO_GEN_OPENROUTER_RETRIES`
- `MANIM_VIDEO_GEN_OPENROUTER_RETRY_BASE_SECONDS`
- `MANIM_VIDEO_GEN_OPENROUTER_RETRY_MAX_SECONDS`

선택 기능: 하단 자막(`MANIM_VIDEO_GEN_BURN_SUBTITLES`), 배경음(`MANIM_VIDEO_GEN_BGM_PATH`), 출력 해상도/FPS(`MANIM_VIDEO_GEN_VIDEO_*`), 진행 콜백(`generate_video(..., on_progress=...)`), Docker(`Dockerfile`).

추가 옵션:
- 자막 줄바꿈/스타일(`MANIM_VIDEO_GEN_SUBTITLE_WRAP_MODE=auto|char`, `MANIM_VIDEO_GEN_SUBTITLE_MAX_CHARS`, `MANIM_VIDEO_GEN_SUBTITLE_FONT_SIZE`, `MANIM_VIDEO_GEN_SUBTITLE_MARGIN_*`)
- 자막과 영상 비겹침 하단 safe area(`MANIM_VIDEO_GEN_SUBTITLE_SAFE_AREA_PX`)
- 씬 간 의미 기반 브리지 전환(`MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED`, 실패 시 즉시 fallback)
- 겹침 방지 안전 모드(`MANIM_VIDEO_GEN_DISABLE_EQUATION_CHAIN`, `MANIM_VIDEO_GEN_DISABLE_PREV_SCENE_STATE`)
- 나레이션-시각화 정합성 검사(`MANIM_VIDEO_GEN_CONSISTENCY_MODE=off|warn|error`)
- error 모드 자동복구(`MANIM_VIDEO_GEN_CONSISTENCY_AUTO_REPAIR`, `MANIM_VIDEO_GEN_CONSISTENCY_AUTO_REPAIR_MAX_ATTEMPTS`)
- 사후 분석 덤프(`MANIM_VIDEO_GEN_DIAGNOSTIC_DUMP=true`) 및 워크스페이스 유지(`MANIM_VIDEO_GEN_KEEP_WORKSPACE=true`)

환경변수 의미 요약:
- `MANIM_VIDEO_GEN_SUBTITLE_WRAP_MODE`
  - `auto`(기본): 수동 `\N` 삽입 없이 ASS 렌더러가 마진/가로폭 기준 자동 줄바꿈
  - `char`: `MANIM_VIDEO_GEN_SUBTITLE_MAX_CHARS` 기준으로 수동 `\N` 삽입
- `MANIM_VIDEO_GEN_SUBTITLE_MAX_CHARS`
  - `wrap_mode=char`일 때만 사용되는 문자 수 기반 줄바꿈 임계치
- `MANIM_VIDEO_GEN_SUBTITLE_FONT_SIZE`, `MANIM_VIDEO_GEN_SUBTITLE_MARGIN_L/R/V`
  - ASS 스타일 폰트 크기/마진(px)
- `MANIM_VIDEO_GEN_SUBTITLE_SAFE_AREA_PX`
  - 0이면 비활성, 1 이상이면 하단 해당 픽셀 높이를 자막 전용 영역으로 확보(영상 scale+pad)
- `MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED`
  - `true`: 인접 씬 경계에서 의미 기반 브리지(현재는 수식 중심 transform) 시도
  - 매핑 확신이 낮거나 브리지 렌더 실패 시 즉시 기존 전환(hard cut)으로 fallback
- `MANIM_VIDEO_GEN_DISABLE_EQUATION_CHAIN`
  - `true`(기본): 연속 수식 chain 병합 렌더를 끄고 segment 독립 렌더 + concat
  - 겹침/중첩 재발 방지를 최우선으로 할 때 권장
- `MANIM_VIDEO_GEN_DISABLE_PREV_SCENE_STATE`
  - `true`(기본): standalone scene에서 `prev_scene_state` 주입을 비활성화
  - 이전 수식 재주입으로 인한 레이아웃 충돌을 방지
- `MANIM_VIDEO_GEN_CONSISTENCY_MODE`
  - `off`: 검사 비활성
  - `warn`: 불일치 이슈를 로그만 남기고 진행
  - `error`: error-level 이슈 발견 시 실행 중단
- `MANIM_VIDEO_GEN_CONSISTENCY_AUTO_REPAIR`
  - `true`: `error` 모드에서 오류 발견 시 scriptify JSON 자동 보정 루프 시도
  - `false`: `error` 발견 즉시 중단
- `MANIM_VIDEO_GEN_CONSISTENCY_AUTO_REPAIR_MAX_ATTEMPTS`
  - 자동 보정 재시도 횟수(정수, 기본 2)
- `MANIM_VIDEO_GEN_DIAGNOSTIC_DUMP`
  - `artifacts/runs/<run_id>/`에 script/segments/scene code/ass/summary 저장
- `MANIM_VIDEO_GEN_KEEP_WORKSPACE`
  - `.tmp/manim_video_*` 작업 디렉토리 보존(디버깅 시 권장)

`MANIM_VIDEO_GEN_SUBTITLE_WRAP_MODE` 기본값은 `auto`이며, 수동 `\N` 삽입 없이 ASS 렌더러가 가로폭/마진 기준으로 자동 줄바꿈합니다. `char`를 사용하면 `SUBTITLE_MAX_CHARS` 기준 수동 줄바꿈을 적용합니다.

연속 수식 세그먼트(`prev_scene_state`로 이어지는 `equation_*` / `equation_derivation` / `highlight_result`)는 **하나의 Manim Scene으로 병합**되어 `TransformMatchingTex` 등으로 자연스럽게 전환됩니다. 렌더 실패 시 자동으로 세그먼트별 렌더로 폴백합니다. 템플릿·체인 렌더는 TTS 길이에 맞추되 `Write`/`Transform` 시간에 **상한**을 두어 앞쪽에서 빠르게 연출하고 나머지는 `wait`로 맞춥니다.

`equation_derivation`은 한 세그먼트에서 위에서 아래로 화살표·짧은 주석과 함께 수식 단계를 **누적** 표시합니다(연속 이항·인수분해 등).

추가 시각 타입: **`number_line_plot`**(수직선·구간 음영·해 점), **`annotated_equation`**(`{{토큰}}` 부분에 Brace+텍스트 주석), **`visual_scene`**(등록 템플릿 없음 → LLM이 Manim 코드 직접 생성). 풀이 단계 JSON에 **`visualization_hints`**(선택)를 두어 scriptify가 그래프·수직선 등을 쓰기 쉽게 합니다.

`graph_plot`은 `visual_params.points`(또는 `extrema_points`)를 받아 그래프 위 강조 점(예: 극대/극소/교점)을 표시할 수 있습니다.

## 설치

```bash
cd manim-video-gen
pip install -e ".[dev]"
cp .env.example .env
# .env에 API 키 입력
```

## 사용

```bash
python -m manim_video_gen "x^2 + 2x + 1 = 0 을 풀어라"
```

## TTS 사전 검증

```bash
python3 scripts/test_tts.py
```

생성된 `artifacts/tts_validation/*.wav`를 청취해 한국어·수학 발음이 데모에 적합한지 판단하세요. 부적절하면 `tts/base.py`에 다른 `TTSProvider` 구현체를 추가해 교체할 수 있습니다.

## LLM 연결 확인 (선택)

```bash
python3 scripts/test_openrouter.py
python3 scripts/test_prompt_chain.py
```

## 렌더 회귀 점검 스크립트 (겹침/흰 네모 감시)

아래 스크립트로 특정 시점 프레임을 자동 점검할 수 있습니다.

```bash
python scripts/verify_render_regressions.py --video artifacts/final_bridge_verify.mp4 --at 48 --at 62 --at 87 --at 98 --at 167 --at 219
```

- `OVERLAP_SUSPECT`: 겹침 가능성이 큰 프레임
- `BRIGHT_BOX_SUSPECT`: 흰 네모(tofu) 가능성이 큰 프레임

---

## Windows 설치 주의사항

macOS/Linux와 달리 Windows에서는 아래 추가 작업이 필요합니다.

### 1. FFmpeg 설치

```powershell
winget install Gyan.FFmpeg
```

설치 후 새 터미널을 열고 확인:

```powershell
ffmpeg -version
ffprobe -version
```

> `ffprobe`는 FFmpeg 패키지에 포함되어 있으므로 별도 설치 불필요.

### 2. LaTeX 설치 (MiKTeX 권장)

```powershell
winget install MiKTeX.MiKTeX
```

설치 후 **MiKTeX Console을 관리자 권한으로 실행**하여 아래 작업을 반드시 수행:

1. `Updates` 탭 → `Check for updates` → `Update now`
2. `Packages` 탭 → `dvisvgm` 검색 → 설치 확인

또는 CLI로:

```powershell
miktex packages update-package-database
miktex packages update
miktex packages install miktex-dvisvgm-bin-x64-2.9
```

설치 확인:

```powershell
pdflatex --version
dvisvgm --version
```

### 3. Python 패키지 설치

Windows에서는 `python3` 대신 `python`을 사용합니다:

```powershell
pip install -e ".[dev]"
```

### 4. .env 설정

```powershell
copy .env.example .env
# .env 파일을 열어 API 키 입력
```

---

## 알려진 이슈

### Windows: MiKTeX dvisvgm 크로스 드라이브 변환 실패

**증상:** 프로젝트가 C: 이외의 드라이브(예: D:)에 있을 때 아래 에러 발생:

```
ValueError: Your installation does not support converting .dvi files to SVG.
```

**원인:** MiKTeX에 포함된 `dvisvgm`은 작업 디렉토리와 다른 드라이브에 있는 파일을
DVI → SVG 변환할 때 실패하는 버그가 있음. 기본 `tempfile.mkdtemp()`는 시스템 TEMP
폴더(`C:\Users\...\AppData\Local\Temp`)를 사용하므로, 프로젝트가 다른 드라이브에
있으면 드라이브가 엇갈려 변환이 실패함.

**해결:** `utils/file_manager.py`에서 임시 디렉토리를 시스템 TEMP 대신 프로젝트 루트
아래 `.tmp/`에 생성하도록 수정되어 있음 (동일 드라이브 유지). `.tmp/`는 `.gitignore`에
추가 권장.
