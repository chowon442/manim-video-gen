# 001 — TTS·Manim·LaTeX 파이프라인 장애 기록

> 목적: 동일 장애를 다시 겪지 않기 위한 사후 정리. (manim-video-gen, 2026)

---

## context: 무엇을 만들려 했는가?

- **프로젝트:** `manim-video-gen` — 수학 문제를 받아 **한국어 해설 영상**까지 만드는 파이프라인.
- **흐름:** OpenRouter(LLM: 풀이 → 스크립트 → 필요 시 Manim 코드) → **ElevenLabs TTS** → **Manim 렌더** → FFmpeg 합성.
- **전제:** 로컬에 `manim`, `ffmpeg`/`ffprobe`, LaTeX(`latex`) 등이 설치되어 있음.

---

## roadblocks: 어떤 에러가 발목을 잡았는가?

### 1) ElevenLabs API

| 증상 | 원인 (근본) |
|------|-------------|
| `with-timestamps` **402** | 플랜/크레딧·엔드포인트 제한 등으로 해당 API가 거절될 수 있음. |
| 표준 TTS도 **402**, 본문에 `paid_plan_required`, *library voices* | **무료 플랜은 API로 “라이브러리(프리셋) 보이스” 사용 불가** — **남은 문자 크레딧과 무관**한 제한. |
| Voice ID를 넣었는데도 라이브러리 보이스로 요청됨 | **`ELEVENLABS_VOICE_ID`가 비어 있음** — `pydantic-settings`의 `env_file=".env"`가 **실행 시 CWD 기준**이라, `scripts/` 등에서 실행하면 루트 `.env`를 못 읽고 기본 보이스(Rachel 등)로 나감. |

### 2) Manim / LaTeX 환경

| 증상 | 원인 |
|------|------|
| `FileNotFoundError: ... 'latex'` | 시스템에 **LaTeX 미설치** 또는 **PATH에 `latex` 없음**. `MathTex`/`Tex`는 내부에서 `latex`를 호출함. |

### 3) Manim 코드·TeX 컴파일 (`latex error converting to dvi`)

| 증상 | 원인 |
|------|------|
| `MathTex(r'... \\frac ... \\sqrt ...')` 형태 | LLM/JSON 습관으로 **raw 문자열 안에 백슬래시가 이중**(`\\frac`) → TeX에서 `\frac`이 아니라 잘못된 입력. |
| `MathTex(r{repr(latex)})` 템플릿 | `repr()`가 이미 `\`를 이스케이프하는데 **`r'...'`와 겹쳐** 소스에 `\\quad` 등이 남음 → `\quad`가 아니라 **줄바꿈용 `\\` + `quad`**로 해석될 수 있음. |
| `\text{또는}` 등 **한글** 포함 | Manim 기본 **pdfLaTeX** 경로는 **한글 조판 설정이 없으면** `\text{한국어}`에서 **컴파일 실패**. 스크립트 LLM이 “LaTeX는 ASCII만” 규칙을 어길 때 발생. |

---

## the fix: 결국 어떻게 풀었는가?

### ElevenLabs

- **`with-timestamps` 실패(402/403/404 등) 시** 표준 `text-to-speech`로 **폴백**; 타임스탬프 없이도 duration은 ffprobe로 처리.
- **402 본문 파싱:** `paid_plan_required` / *library voices* 메시지면 **크레딧 부족이 아니라 플랜·보이스 종류**임을 한국어로 안내.
- **설정:** 저장소 루트의 `.env`를 **패키지 기준 절대 경로**로 읽도록 변경 (CWD와 무관).
- **운영:** 무료 API는 **Voice Lab에서 만든 본인 보이스 ID**를 `ELEVENLABS_VOICE_ID`에 설정; 필요 시 `MANIM_VIDEO_GEN_ELEVENLABS_TRY_TIMESTAMPS=false`로 타임스탬프 시도 생략.

### LaTeX 설치

- macOS: `brew install --cask basictex` 또는 `mactex` 후 터미널 재시작, `which latex` 확인.

### Manim 코드 품질

- **`normalize_llm_manim_tex_backslashes`:** AST로 `MathTex`/`Tex` 등 **문자열 인자 값**에 대해 `\\frac` → `\frac`류 정규화 + `sanitize_latex_for_compilation` 적용.
- **템플릿:** `MathTex(r{repr(...)})` 제거 → **`MathTex({repr(...)})`** (일반 문자열 리터럴 + `repr`만 사용).
- **`sanitize_latex_for_compilation`:** `\text`/`\mathrm`/`\mbox` 등 **인자에 비ASCII**면 `\quad`로 치환, 반복 적용 후 **남는 비ASCII 문자 제거**; 이중 백슬래시 명령도 선행 정리.
- **프롬프트:** Manim/스크립트 쪽에 **MathTex 안에 한글 넣지 말 것**, `\text{or}` / `\quad`만 사용 등 명시.

---

## learning: 새로 알게 된 것·꼭 기억할 것

1. **ElevenLabs 무료 + API:** “크레딧이 있다”와 “라이브러리 보이스 API 허용”은 **다른 축**이다. `paid_plan_required` + *library voices*면 **본인 보이스 ID 또는 유료 플랜**을 떠올릴 것.
2. **`.env` 로딩:** `env_file=".env"`만 쓰면 **실행 디렉터리**에 묶인다. CLI/스크립트는 **항상 루트 `.env`**를 읽게 설계하는 편이 안전하다.
3. **생성 코드에서 LaTeX + Python 문자열:** `r'...'` + 이중 `\\command` , 또는 **`r` + `repr()`** 조합은 **TeX와 파이썬 이스케이프가 겹쳐** 자주 깨진다. 생성기는 **`repr`만 쓰거나**, 후처리로 **문자열 “값”** 기준으로 정규화할 것.
4. **Manim + pdfLaTeX:** 수식 안 **한글·CJK**는 기본 도구로는 깨지기 쉽다. **나레이션은 TTS**, 화면 수식은 **ASCII LaTeX**로 두는 정책이 재현성이 좋다. (한글을 굳이 씌우려면 XeLaTeX/LuaLaTeX·폰트 등 별도 설계가 필요.)
5. **장애 재발 방지:** 스크립트 JSON의 `latex` 필드에 **비ASCII 검증**(Pydantic validator 등)을 두면, 렌더 직전까지 가지 않고 막을 수 있다.

---

## 빠른 체크리스트 (다음에 막힐 때)

- [ ] `latex --version` / `which latex`
- [ ] 프로젝트 루트에서 실행하거나, **루트 `.env`가 로드되는지** 확인
- [ ] ElevenLabs 402 시 응답 JSON의 **`code` / `message`** 확인 (크레딧 vs 라이브러리 보이스 vs 기타)
- [ ] Manim TeX 에러 시 생성된 `scene_*.py`에서 **`MathTex` 인자**에 `\\frac`, `\\quad`, `\text{한글}` 없는지 확인
- [ ] 최신 코드에 **sanitize + normalize** 경로가 타는지(설치 경로가 `src`인지 site-packages 구버전인지) 확인
