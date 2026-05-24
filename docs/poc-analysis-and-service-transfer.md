# Manim 해설 동영상 생성 PoC 분석 및 서비스 이관 가이드

## 목적

이 문서는 현재 `manim-video-gen` 코드베이스를 실제 서비스 레포지토리에서 처음부터 재구현하기 위한 분석 자료다. 현재 저장소는 PoC 구현이 끝난 상태이며, 여기서 가져갈 것은 완성 코드 그 자체보다 다음이다.

- 어떤 파이프라인 구성이 실제로 동작했는지
- 어떤 장애가 반복됐고 어떤 방어 계층이 생겼는지
- 어떤 설계 결정은 서비스에서도 유지해야 하는지
- 어떤 구현 방식은 서비스 레포에 그대로 복사하면 안 되는지
- 자유형 Manim Python 장면과 템플릿을 어떻게 함께 제품화할지

## 한 줄 결론

실제 서비스에서는 `visual_scene` 자유형 Manim Python 생성을 막지 않는다. 좋은 장면 품질을 위해 선택적 핵심 경로로 유지하되, API 서버에서 직접 실행하지 않고 `AST 검증 + 네트워크 차단 샌드박스 + smoke render + retry taxonomy + intent-preserving fallback`으로 감싸야 한다. 템플릿은 자유형의 대체재가 아니라 안정적인 품질 하한선과 fallback 품질을 만드는 기반으로 고도화해야 한다.

## 현재 PoC의 전체 흐름

현재 파이프라인은 다음 단계로 구성된다.

```text
사용자 문제 입력
→ LLM 풀이 계획 생성
→ LLM 영상 대본 생성
→ consistency / quality guard
→ segment별 TTS 생성
→ TTS duration 기준으로 render unit 구성
→ template 또는 freeform Manim 코드 생성
→ Manim render
→ ASS 자막 생성
→ FFmpeg mux / concat / crossfade
→ 선택적 BGM mix
→ 선택적 diagnostic dump
→ final MP4
```

핵심 orchestration은 하나의 함수에 모여 있다. 서비스에서는 이 구조를 그대로 동기 API에 붙이면 안 되고, stage별 job worker로 분해해야 한다.

```python
async def generate_video(
    problem_text: str,
    *,
    settings: Settings | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[Path, SessionWorkspace]:
    """
    Run full pipeline. Returns (final_mp4_path, workspace).

    Caller should `copy` the mp4 elsewhere then `workspace.cleanup()`.
    """
    settings = settings or get_settings()
    t0 = time.perf_counter()

    problem = MathProblem(problem_text=problem_text)
    tts = get_tts_provider(settings)
    registry = TemplateRegistry()
    composer = VideoComposer(
        crossfade_duration=settings.crossfade_duration,
        inter_scene_gap_seconds=settings.inter_scene_gap_seconds,
    )

    workspace = SessionWorkspace()
```

LLM 단계는 풀이 계획과 영상 대본을 분리한다.

```python
plan = await client.complete_json_model(
    model=settings.model_solve,
    messages=[
        {"role": "system", "content": SOLVE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": solve_user_prompt(problem.problem_text),
        },
    ],
    response_model=SolutionPlan,
)
```

```python
(
    script,
    consistency_report,
    script_quality_report,
) = await _scriptify_with_quality_guard(
    client=client,
    settings=settings,
    plan=plan,
)
```

TTS 결과의 길이가 이후 장면 길이, 자막 길이, 최종 합성의 기준이 된다.

```python
for seg in script.segments:
    audio_path = workspace.root / f"seg_{seg.id:02d}.wav"
    tts_result = await tts.synthesize(
        seg.effective_tts_text, output_path=audio_path
    )
    tts_results.append(tts_result)

chains = group_into_chains(script.segments, tts_results)
```

## 핵심 데이터 계약

서비스 레포에서도 유지해야 할 가장 중요한 계약은 `Segment`다.

```python
class Segment(BaseModel):
    """One narrated segment with visual instructions."""

    id: int = Field(..., ge=0)
    narration: str = Field(
        ...,
        description="Readable Korean for subtitles; may include light math notation like x², 6x",
    )
    tts_text: str = Field(
        default="",
        description="Fully phonetic Korean for TTS engine (e.g. '엑스 제곱 더하기 육엑스')",
    )
    visual_description: str = Field(
        ...,
        description="What should appear on screen",
    )
    visual_type: str = Field(
        ...,
        description="equation_write | equation_transform | ...",
    )
    visual_params: dict[str, Any] = Field(default_factory=dict)
    prev_scene_state: list[SceneObjectState] | None = Field(
        default=None,
        description="Objects that should already be on screen at segment start",
    )
```

이 구조가 중요한 이유는 각 필드의 책임이 다르기 때문이다.

| 필드 | 책임 | 서비스 이관 판단 |
| --- | --- | --- |
| `narration` | 자막과 사용자에게 보이는 설명 | 유지 |
| `tts_text` | TTS provider에 넣는 자연 발화문 | 유지 |
| `visual_description` | 자유형 Manim 장면 director brief | 강화 |
| `visual_type` | 템플릿 또는 자유형 렌더 경로 선택 | metadata registry로 강화 |
| `visual_params` | 렌더러 입력 | schema 검증 추가 |
| `prev_scene_state` | 장면 연속성 정보 | 기본 비활성 유지, 고품질 모드에서만 검토 |

TTS 결과 계약도 서비스 데이터 모델로 가져갈 수 있다.

```python
class TTSResult(BaseModel):
    """Output of TTS synthesis for one segment."""

    audio_path: Path
    duration_seconds: float = Field(..., ge=0.0)
    word_timestamps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of {word,start,end} or provider-specific keys",
    )
```

## 현재 방식에서 잘한 점

### 1. 풀이와 영상 대본을 분리했다

`SolutionPlan`은 수학 풀이의 구조를 만들고, `VideoScript`는 영상 세그먼트로 바꾼다. 이 분리는 서비스에서도 유지해야 한다. 풀이 정확도와 영상 연출 품질은 다른 문제이기 때문이다.

```python
class SolutionPlan(BaseModel):
    """Full solution broken into steps."""

    title: str = Field(default="풀이", description="Short title for the solution")
    steps: list[SolutionStep] = Field(default_factory=list, min_length=1)
    visualization_hints: list[str] = Field(
        default_factory=list,
        description="Optional ideas for on-screen visuals (graphs, number line, geometry) for the video pass",
    )
```

### 2. 자막과 TTS 발화를 분리했다

자막은 `x² + 6x + 9 = 0`처럼 읽기 쉬운 표기가 필요하고, TTS는 “엑스 제곱 더하기 육엑스...”처럼 발화 가능한 문장이 필요하다. 이 분리는 여러 post-mortem 이후 생긴 핵심 자산이다.

```python
def _ensure_tts_text(script: VideoScript, settings: Settings) -> VideoScript:
    """Ensure every segment has a usable tts_text.

    If the LLM provided tts_text, apply polish as safety net (except Grok/xAI,
    where speech tags must be preserved).
    Otherwise, derive tts_text from narration via polish_tts_text.
    """
    provider = (settings.tts_provider or "").strip().lower()
    use_grok_tags = provider in ("grok", "xai")
    updated = []
    for s in script.segments:
        tts = s.tts_text.strip() if s.tts_text else ""
        if not tts:
            tts = polish_tts_text(s.narration)
        elif use_grok_tags:
            tts = tts.strip()
        else:
            tts = polish_tts_text(tts)
        updated.append(s.model_copy(update={"tts_text": tts}))
    return script.model_copy(update={"segments": updated})
```

### 3. 템플릿과 자유형 Manim 경로를 함께 둔다

현재 구현은 템플릿이 있으면 템플릿을 쓰고, 템플릿이 부족하면 LLM이 Manim Python을 생성한다.

```python
if registry.has(seg.visual_type) and not force_llm:
    code = registry.render_code_for_segment(seg, duration)
    code = normalize_llm_manim_tex_backslashes(code)
    code = inject_cjk_if_needed(code)
    code = adjust_duration_safe(code, duration)
    code = ensure_scene_cleanup(code, enabled=cleanup_enabled)
else:
    code, n_try = await _llm_manim_with_retries_counted(
        client=client,
        settings=settings,
        segment=seg,
        duration=duration,
        workspace=workspace.root,
        stem=f"scene_{seg.id:02d}",
    )
```

이 방향은 유지해야 한다. 템플릿만으로는 좋은 장면이 부족하고, 자유형만으로는 실패율과 보안 문제가 커진다.

### 4. 자유형 Manim retry에 이전 실패 맥락을 넣는다

이전 에러와 이전 코드를 prompt에 넣는 방식은 서비스에서도 반드시 유지한다.

```python
if prior_errors:
    prior += "\n\nPrevious errors (fix them):\n" + "\n".join(
        f"- {e}" for e in prior_errors
    )
    prior += (
        "\n\nRetry instruction:\n"
        "- Analyze the exact root causes in the previous errors above.\n"
        "- Rewrite the scene to avoid those failures.\n"
        "- Do not repeat the failing patterns from previous attempts.\n"
        "- Explain briefly in code comments where you changed the risky part."
    )
if prior_codes:
    prior += "\n\nPrevious full code attempts (rewrite or fix; do not repeat mistakes):\n"
```

### 5. LaTeX 백슬래시 보정을 AST 기반으로 처리한다

과거 장애의 핵심은 코드 텍스트 정규식으로 백슬래시를 건드리면 정상 문자열까지 손상된다는 점이었다. 현재는 AST로 `MathTex`/`Tex` 문자열 값만 보정한다.

```python
def normalize_llm_manim_tex_backslashes(code: str) -> str:
    """MathTex/Tex 호출의 문자열 인자 *값*에서 이중 백슬래시를 정규화한다.

    AST 기반으로 동작하여 raw/non-raw string 구분 없이 안전하게 처리한다.
    변경이 필요 없으면 원본 코드를 그대로 반환하므로 포맷이 유지된다.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
```

### 6. 자막은 LaTeX가 아니라 평문/Unicode로 정규화한다

ASS 자막은 LaTeX renderer가 아니므로 수식 조각을 사람이 읽을 수 있는 형태로 변환한다.

```python
def _normalize_subtitle_narration(text: str) -> str:
    """Normalize LaTeX-like remnants so subtitles stay readable."""
    t = str(text)
    t = _strip_math_delimiters(t)
    t = t.replace(r"\,", " ").replace(r"\;", " ").replace(r"\:", " ")
    t = _TEXT_CMD_RE.sub(r"\1", t)
    t = _latex_fragments_to_unicode(t)
    t = _apply_unicode_math_scripts(t)
    t = _TEX_CMD_RE.sub("", t)
    t = t.replace("\\", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t
```

### 7. 영상과 음성 중 짧은 쪽을 자르지 않는다

최근 안정화의 핵심이다. `-shortest`로 자르는 대신 긴 쪽에 맞춰 padding한다.

```python
def _merge_padding_seconds(video_s: float, audio_s: float) -> tuple[float, float, float]:
    """Return (video_tpad, audio_apad, target) so both match max(v, a)."""
    t = max(float(video_s), float(audio_s))
    v_pad = max(0.0, t - float(video_s))
    a_pad = max(0.0, t - float(audio_s))
    return v_pad, a_pad, t
```

```python
if v_pad > 0:
    tpad = f"tpad=stop_mode=clone:stop_duration={v_pad:.6f}"
    vf = f"{vf0},{tpad}" if vf0 != "null" else tpad

if a_pad > 0:
    base_cmd.extend(["-af", f"apad=pad_dur={a_pad:.6f}"])
```

### 8. 브리지는 기본 OFF로 둔다

semantic bridge는 기능적으로 가능하지만 실제 UX에서는 어색할 수 있었다. 기본값은 단순하고 안정적인 전환이 맞다.

```python
crossfade_duration: float = Field(
    default=0.2,
    validation_alias="MANIM_VIDEO_GEN_CROSSFADE_DURATION",
)
scene_bridge_enabled: bool = Field(
    default=False,
    validation_alias="MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED",
    description="Enable semantic bridge transition generation between adjacent rendered chains/scenes.",
)
```

## 그대로 가져가면 안 되는 부분

### 1. 단일 함수 orchestration

PoC에서는 적절하지만, 실제 서비스에서는 API 요청이 이 전체 흐름을 붙잡으면 안 된다. 생성은 오래 걸리고 실패 지점이 많으며 취소/재시도/상태 저장이 필요하다.

개선안:

```text
API Server
→ job 생성
→ Queue
→ Generation Worker
→ Render Sandbox Worker
→ Object Storage
→ 상태 조회 / 알림
```

### 2. 자유형 Python을 단순 smoke render만으로 신뢰하는 구조

현재는 문법 검사와 low-quality render를 통과하면 최종 렌더로 간다.

```python
def validate_and_test_render(
    *,
    code: str,
    workspace: Path,
    settings: Settings,
    stem: str,
) -> tuple[bool, str]:
    ok, err = validate_python_syntax(code)
    if not ok:
        return False, err

    scene_path = workspace / f"{stem}.py"
    media_dir = workspace / "media"
    ok2, err2 = run_manim_render(
        code=code,
        scene_path=scene_path,
        quality=settings.manim_quality_low,
        timeout_seconds=settings.manim_render_timeout_seconds,
        media_dir=media_dir,
        settings=settings,
    )
```

서비스에서는 여기에 다음이 추가되어야 한다.

- AST allowlist
- import 제한
- 파일/네트워크/프로세스 API 금지
- network-off sandbox
- CPU/memory/pid/wall-clock 제한
- read-only root filesystem
- writable temp workspace만 허용
- artifact size 제한

### 3. `func_python` code string 삽입

템플릿도 안전하다고 가정하면 안 된다. 현재 `graph_plot`은 Python 코드를 문자열로 받아 생성 코드에 삽입한다.

```python
func_python = str(params.get("func_python", "lambda x: x**2")).strip()
if not func_python.startswith("lambda"):
    func_python = f"lambda x: ({func_python})"
```

```python
graph = axes.plot({func_python}, color={color})
```

서비스에서는 expression DSL로 바꾼다.

```json
{
  "expr": "x^2 - 4*x + 3",
  "domain": [-1, 5],
  "features": [
    {"type": "root", "x": 1, "label": "x=1"},
    {"type": "root", "x": 3, "label": "x=3"},
    {"type": "vertex", "x": 2, "y": -1, "label": "최솟값"}
  ]
}
```

### 4. 자유형 실패 시 `equation_write` 직행

현재 fallback은 너무 단순하다.

```python
logger.warning("LLM Manim failed after retries; falling back to equation_write")
fallback_latex = (
    segment.visual_params.get("latex")
    or segment.visual_params.get("to_latex")
    or segment.visual_params.get("from_latex")
    or segment.visual_description[:400]
)
return (
    EquationWriteTemplate.render_code(
        params={"latex": str(fallback_latex)},
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    ),
    max_retries,
)
```

이 방식은 “그래프로 보면”, “도형을 보면”, “넓이를 색칠하면” 같은 narration과 화면이 불일치할 수 있다.

개선안:

```text
visual_scene 실패
→ director brief와 narration intent 분석
→ graph_plot / number_line_plot / annotated_equation / equation_derivation 후보 선택
→ fallback 후 consistency validation
→ 불일치하면 script repair
→ 마지막에만 equation_write 또는 highlight_result
```

### 5. `ffprobe` 실패 시 1초 fallback

PoC에서는 실용적인 방어지만 서비스에서는 품질을 무너뜨릴 수 있다. 1초 duration은 장면 길이, 자막 길이, 합성 전체에 전파된다.

```python
except (
    FileNotFoundError,
    subprocess.CalledProcessError,
    KeyError,
    ValueError,
    json.JSONDecodeError,
) as exc:
    logger.warning("ffprobe failed, using fallback duration: %s", exc)
    return 1.0
```

서비스 기본 정책:

```text
duration probe 실패
→ provider retry
→ 그래도 실패하면 job failed
→ dev/debug profile에서만 1초 fallback 허용
```

### 6. 로컬 `.env`와 repo-local `.tmp` 운영 방식

현재 `.env`는 repo root 기준으로 로딩한다. CLI PoC에는 편리하지만 서비스에서는 secret manager가 원천이어야 한다.

```python
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_DOTENV = _REPO_ROOT / ".env"
_ENV_FILE = str(_REPO_DOTENV) if _REPO_DOTENV.is_file() else ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )
```

서비스에서는 다음을 적용한다.

- repo root `.env` 자동 탐색 금지
- secret manager 사용
- provider별 scoped secret
- key rotation 가능 구조
- logs/diagnostics redaction

## 템플릿 고도화 방향

템플릿은 자유형 장면을 없애기 위한 것이 아니라, 다음을 위해 필요하다.

- 빠르고 안정적인 장면 생성
- 자유형 실패 시 납득 가능한 fallback
- LLM이 무리하게 `visual_scene`을 남용하지 않도록 유도
- 반복되는 좋은 자유형 패턴을 제품 품질로 흡수

우선순위 높은 템플릿 개선 대상:

| 템플릿 | 개선 방향 |
| --- | --- |
| `graph_plot` | expression DSL, 다중 곡선, 접선, 교점, 극값, 영역 음영, label 배치 |
| `number_line_plot` | 열린/닫힌 점, 부등식 구간, 방향 화살표, 복수 구간 |
| `annotated_equation` | brace target 실패 fallback, annotation 충돌 회피 |
| `equation_derivation` | 긴 수식 frame fit, 단계별 highlight, annotation 정렬 |
| `intro_problem` | 긴 문제 본문 자동 축소, 핵심 조건 강조 |
| `outro_summary` | 답 강조, 줄별 요약, 다음 학습 안내 |

추가하면 좋은 신규 템플릿:

| 신규 템플릿 | 용도 |
| --- | --- |
| `geometry_diagram` | 삼각형, 각도, 평행선, 원, 접선 |
| `unit_circle` | 삼각함수, 라디안, 좌표 대응 |
| `area_under_curve` | 적분, 넓이, 누적량 |
| `table_template` | 값 대입표, 부호표, 함수 증감표 |
| `matrix_transform` | 행렬, 벡터, 선형변환 |
| `coordinate_geometry` | 두 점, 기울기, 직선, 교점, 거리 |
| `probability_tree` | 경우의 수, 확률, 조건 분기 |

## 자유형 Manim 제품화 전략

`visual_scene`은 선택적 핵심 경로로 둔다.

사용 기준:

- 도형 구성, 각도, 넓이, 회전, 벡터, 행렬 변환, 단위원처럼 템플릿 표현력이 부족한 경우
- 여러 객체의 관계나 움직임이 설명의 핵심인 경우
- 학생이 “왜 그런지”를 시각적으로 이해해야 하는 장면
- 한 장면 안에서 object choreography가 필요한 경우

사용하지 않을 기준:

- 수식 한 줄 표시
- A 식에서 B 식으로 변환
- 2~5줄 연속 유도
- 최종 답 강조
- 수직선 근/구간 표시
- 단순 계수/항 annotation

서비스 처리 흐름:

```text
visual_scene segment 수신
→ director brief 정규화
→ 금지 요구 제거
→ LLM Manim code 생성
→ AST safety check
→ sandbox low-quality smoke render
→ 실패 시 taxonomy + prior code/error로 retry
→ 실패 지속 시 intent-preserving fallback
→ consistency validation
→ sandbox high-quality render
→ artifact 저장
```

## Runtime / Docker / Health Check

현재 Dockerfile은 PoC 실행 이미지다.

```dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    fonts-noto-cjk \
    texlive-latex-extra \
    texlive-fonts-recommended \
    dvipng \
    && rm -rf /var/lib/apt/lists/*
```

서비스 이미지에서 추가할 것:

- production dependency만 설치
- non-root user
- render worker entrypoint 분리
- build-time smoke check
- runtime health check
- read-only root filesystem
- writable workspace volume
- CPU/memory/pid 제한

필수 health check:

```text
ffmpeg -version
ffprobe -version
manim --version
latex --version
xelatex --version
dvisvgm --version
CJK font 존재 확인
최소 CJK MathTex smoke render
```

## Diagnostic / Artifact 정책

현재 diagnostic은 문제 원문, solution plan, script, generated code, ASS, summary를 저장한다.

```python
(run_dir / "problem.txt").write_text(problem_text, encoding="utf-8")

if plan is not None:
    _write_json(run_dir / "solution_plan.json", plan.model_dump())
if script is not None:
    _write_json(run_dir / "script.json", script.model_dump())
```

```python
if item.manim_code:
    (code_dir / f"segment_{seg.id:02d}.py").write_text(
        item.manim_code,
        encoding="utf-8",
    )
```

서비스에서는 반드시 두 계층으로 분리한다.

| 계층 | 포함 내용 | 접근 권한 |
| --- | --- | --- |
| internal diagnostic | 문제 원문, script, generated code, stderr, segment artifacts | 운영자 전용 |
| user diagnostic | 실패 단계, safe error code, 재시도 가능 여부, 최종 URL | 사용자 가능 |

Object storage key 예시:

```text
video-generations/{job_id}/final.mp4
video-generations/{job_id}/clean.mp4
video-generations/{job_id}/subtitles.ass
video-generations/{job_id}/subtitles.srt
video-generations/{job_id}/segments/{segment_id}/audio.wav
video-generations/{job_id}/segments/{segment_id}/video.mp4
video-generations/{job_id}/segments/{segment_id}/merged.mp4
video-generations/{job_id}/diagnostics/internal.json
video-generations/{job_id}/diagnostics/segment-code/{segment_id}.py
```

## 테스트 전략

현재 테스트는 단위/통합 mock 중심으로 넓게 존재한다. 확인된 test function 수는 226개다. 실제 서비스 레포에서는 다음 전략으로 재구성한다.

### 빠른 단위 테스트

- JSON extraction/repair
- prompt catalog generation
- visual type schema validation
- `narration` / `tts_text` 분리 후처리
- consistency validator
- script quality scoring
- subtitle normalization
- LaTeX backslash normalization
- graph expression DSL parser
- Manim AST safety checker
- fallback selector
- provider capability metadata

### 통합 테스트

- Fake LLM + Fake TTS + Fake render로 job 상태 전이 검증
- object storage mock 업로드 검증
- FFmpeg 최소 합성 검증
- sandbox timeout / memory / network block 검증
- `visual_scene` retry taxonomy 검증

### Heavy / nightly E2E

- 이차방정식 인수분해
- 이차함수 그래프와 근
- 수직선과 구간
- 계수 annotation
- 긴 한국어 문제 본문
- CJK 포함 LaTeX
- 단위원 / 삼각함수
- 도형 / 기하 장면
- 자유형 `visual_scene` 실패 후 fallback
- provider별 TTS smoke

### 프레임 기반 회귀

이미 overlap/tofu 의심을 감지하는 도구가 있다.

```python
if s.overlap_ratio > 0.82:
    flags.append("OVERLAP_SUSPECT")
if s.bright_box_ratio > 0.98:
    flags.append("BRIGHT_BOX_SUSPECT")
```

서비스에서는 이 신호를 nightly metric으로 올린다.

## 서비스 레포 목표 아키텍처

```text
Client
→ API Server
→ video_generation_jobs 저장
→ Queue
→ Generation Worker
→ LLM Solve / Scriptify
→ TTS Provider
→ Render Sandbox Worker
→ FFmpeg Composer
→ Object Storage
→ Job Status / Notification
```

권장 모듈:

| 모듈 | 책임 |
| --- | --- |
| `VideoGenerationApi` | job 생성, 상태 조회, 취소 |
| `VideoGenerationService` | 권한, quota, profile/options 해석 |
| `GenerationRepository` | job, segment, artifact, event 저장 |
| `GenerationQueue` | enqueue, retry, dead-letter |
| `GenerationWorker` | solve/scriptify/tts/render/compose orchestration |
| `LlmClientPort` | OpenRouter 또는 내부 LLM 추상화 |
| `TtsProviderPort` | provider별 합성 추상화 |
| `VisualTypeRegistry` | visual type schema/prompt/fallback 단일 출처 |
| `TemplateRenderer` | 안전한 템플릿 Manim 생성 |
| `FreeformSceneGenerator` | `visual_scene` codegen/retry |
| `ManimCodeSafetyChecker` | AST allowlist |
| `RenderSandbox` | 격리 실행 |
| `VideoComposer` | FFmpeg 합성 |
| `ArtifactStore` | MP4/diagnostic/object storage |
| `RuntimeHealthCheck` | 외부 binary/font 검증 |

## Job 상태 모델

권장 상태:

| 상태 | 의미 |
| --- | --- |
| `queued` | 요청 접수 |
| `solving` | 풀이 생성 |
| `scriptifying` | 영상 대본 생성 |
| `tts_generating` | 음성 생성 |
| `rendering` | Manim 렌더 |
| `composing` | FFmpeg 합성 |
| `uploading` | object storage 업로드 |
| `completed` | 완료 |
| `failed` | 실패 |
| `cancelled` | 취소 |

권장 segment record:

| 필드 | 설명 |
| --- | --- |
| `segment_id` | 대본 segment id |
| `narration` | 자막 문장 |
| `tts_text` | 발화문 |
| `visual_type` | 장면 타입 |
| `visual_params` | 장면 입력 |
| `selected_renderer` | template/freeform/fallback |
| `duration_seconds` | TTS 기준 duration |
| `render_status` | 렌더 상태 |
| `llm_retry_count` | 자유형 retry 수 |
| `fallback_reason` | fallback 사유 |
| `artifact_refs` | audio/video/ass/code refs |

## Rollout 계획

1. API는 job 생성/상태 조회만 제공한다.
2. PoC pipeline의 개념을 stage 단위 worker로 재구현한다.
3. object storage와 private diagnostic 저장을 붙인다.
4. `VisualTypeRegistry`를 만들고 prompt catalog와 renderer schema를 단일화한다.
5. `visual_scene`을 sandbox worker 뒤로 격리한다.
6. AST safety checker와 resource limit을 적용한다.
7. `func_python`을 graph expression DSL로 대체한다.
8. intent-preserving fallback selector를 도입한다.
9. curated E2E set을 nightly로 운영한다.
10. `script_quality_enabled`를 내부 베타에서 켠 뒤 profile별 기본값을 조정한다.
11. metrics를 붙인다: 성공률, stage별 실패율, `visual_scene` 사용률, retry율, fallback율, 평균 생성 시간.
12. 내부 사용자부터 `quality` profile을 점진 공개한다.

## 우선순위 체크리스트

### P0: 서비스 전 필수

- Render sandbox 분리
- AST safety checker 추가
- `func_python` 제거 또는 DSL화
- internal/user diagnostic 분리
- secret/error redaction
- object storage와 private artifact ACL
- runtime health check
- API는 job 생성/상태 조회만 담당
- `visual_scene`은 유지하되 sandbox에서만 실행

### P1: 운영 안정성

- `VisualTypeRegistry` 단일화
- intent-preserving fallback selector
- LLM retry taxonomy
- provider capability metadata
- duration probe 실패 시 1초 fallback 제거
- workspace quota/TTL cleanup
- structured logs/metrics/traces
- stage별 timeout/concurrency/rate limit

### P2: 품질 고도화

- 템플릿 카탈로그 확장
- phrase/word-level subtitle 옵션
- BGM loudness normalization/ducking
- curated E2E nightly
- frame-based overlap/tofu/safe-area detection metric화
- 좋은 자유형 장면을 primitive/template로 흡수하는 개선 루프

## 최종 원칙

```text
API 서버는 Manim 코드를 실행하지 않는다.
Generation worker도 신뢰되지 않은 Python을 직접 실행하지 않는다.
모든 render는 network-off, resource-limited sandbox worker에서만 실행한다.
visual_scene은 유지하되 AST 검증, smoke render, retry taxonomy, intent-preserving fallback으로 감싼다.
템플릿은 자유형의 대체재가 아니라 품질 하한선과 fallback 품질을 높이는 기반으로 고도화한다.
```
