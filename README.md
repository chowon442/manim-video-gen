# manim-video-gen

수학 문제를 입력받아 풀이 해설 동영상을 자동 생성하는 파이프라인입니다.

## 요구 사항

- Python 3.11+
- FFmpeg / ffprobe (시스템 PATH; ElevenLabs MP3→WAV 변환 및 합성에 필요)
- LaTeX (Manim `MathTex`용, TeX Live 등)
- `OPENROUTER_API_KEY`
- TTS: 기본 `ELEVENLABS_API_KEY` 또는 `MANIM_VIDEO_GEN_TTS_PROVIDER=azure` 시 `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`

OpenRouter는 공식 OpenAI 호환 REST(`httpx`)로 호출합니다. 모델은 `.env`의 `MANIM_VIDEO_GEN_MODEL_*`로 지정합니다.

선택 기능: 하단 자막(`MANIM_VIDEO_GEN_BURN_SUBTITLES`), 배경음(`MANIM_VIDEO_GEN_BGM_PATH`), 출력 해상도/FPS(`MANIM_VIDEO_GEN_VIDEO_*`), 진행 콜백(`generate_video(..., on_progress=...)`), Docker(`Dockerfile`).

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