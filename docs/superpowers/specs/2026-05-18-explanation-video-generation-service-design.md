# 해설 동영상 생성 기능 서비스화 기획

## 1. 배경

현재 PoC는 수학 문제를 입력받아 한국어 해설 동영상을 생성하는 end-to-end 파이프라인이다. 흐름은 LLM 풀이 생성, 영상 대본 생성, TTS, Manim 렌더링, 자막 생성, FFmpeg 합성으로 이어진다.

실제 서비스 레포에서는 이 기능을 단순 CLI 또는 동기 함수 호출로 붙이면 안 된다. 생성 시간이 길고, LLM/TTS/Manim/FFmpeg/LaTeX 같은 외부 의존성이 많으며, 좋은 장면을 만들기 위해 자유형 Manim Python 생성이 필요하기 때문이다.

이번 서비스화의 핵심 방향은 다음과 같다.

- `visual_scene` 자유형 Manim Python 생성을 선택적 핵심 경로로 유지한다.
- 템플릿은 안전한 기본 경로이자 품질 하한선으로 고도화한다.
- 자유형 생성은 금지하지 않고, 샌드박스·정적 검증·smoke render·재시도·fallback으로 운영 가능하게 만든다.
- API 요청은 동기 생성이 아니라 비동기 job으로 처리한다.
- 생성 산출물과 진단 정보는 서비스 저장소와 권한 체계에 맞춰 관리한다.

## 2. PoC에서 확인한 현재 구조

파이프라인 진입점은 하나의 orchestration 함수에 집중되어 있다.

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

LLM 단계는 풀이 생성과 영상 대본 생성을 분리한다.

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

대본 모델은 자막용 문장, TTS용 발화문, 화면 지시를 분리한다. 이 분리는 실제 서비스에서도 유지해야 한다.

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
```

템플릿 레지스트리는 `visual_type` 문자열을 Manim 코드 생성기로 매핑한다.

```python
_TEMPLATE_RENDERERS: dict[str, Callable[[Segment, float], str]] = {
    EquationWriteTemplate.visual_type: _render_equation_write,
    EquationTransformTemplate.visual_type: _render_equation_transform,
    EquationStepsTemplate.visual_type: _render_steps,
    EquationDerivationTemplate.visual_type: _render_equation_derivation,
    GraphPlotTemplate.visual_type: _render_graph,
    NumberLinePlotTemplate.visual_type: _render_number_line,
    AnnotatedEquationTemplate.visual_type: _render_annotated_equation,
    HighlightResultTemplate.visual_type: _render_highlight,
    TitleCardTemplate.visual_type: _render_title,
    IntroProblemTemplate.visual_type: _render_intro,
    OutroSummaryTemplate.visual_type: _render_outro,
}
```

템플릿이 부족하거나 커스텀 장면이 필요하면 LLM으로 Manim Python을 생성한다. 이 경로가 좋은 장면 품질에 중요하다.

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

`visual_scene` 자체도 프롬프트에 이미 정식 catalog로 정의되어 있다.

```python
12) visual_scene
   - Screen: NOT a fixed template — the pipeline runs LLM Manim code generation for this segment (rich visuals: unit circle, areas, custom diagrams).
   - Use when number_line_plot / graph_plot / annotated_equation are not enough and a bespoke scene is worth the risk of codegen failure (fallback may simplify).
   - visual_description MUST be a concrete director brief (what objects, layout, animation order). visual_params may include hints: { "hints": "..." } or free-form keys the coder can use.
   - narration must still match what you ask the code to show; avoid promising something not in visual_description.
```

따라서 서비스 설계에서 자유형 Manim을 제거하면 PoC가 발견한 품질 장점을 잃는다. 대신 자유형 경로를 제품 안전장치 안으로 넣어야 한다.

## 3. 과거 문제에서 얻은 제약

### 3.1 TTS와 길이 동기화

TTS 결과의 duration이 Manim scene duration, 자막 타이밍, 최종 합성의 기준이다.

```python
tts_result = await tts.synthesize(
    seg.effective_tts_text, output_path=audio_path
)
tts_results.append(tts_result)

chains = group_into_chains(script.segments, tts_results)
```

최근 안정화는 비디오와 오디오 중 짧은 쪽을 자르지 않고 긴 쪽에 맞추는 방향이었다.

```python
def _merge_padding_seconds(video_s: float, audio_s: float) -> tuple[float, float, float]:
    """Return (video_tpad, audio_apad, target) so both match max(v, a)."""
    t = max(float(video_s), float(audio_s))
    v_pad = max(0.0, t - float(video_s))
    a_pad = max(0.0, t - float(audio_s))
    return v_pad, a_pad, t
```

서비스에서도 TTS duration을 신뢰하되, `ffprobe` 실패 시 1초 fallback 같은 PoC 동작은 운영 기본값으로 두지 않는다. duration 측정 실패는 job 실패 또는 해당 provider 재시도로 분류한다.

### 3.2 LaTeX, CJK, 자막 문제

PoC는 LaTeX 백슬래시 손상과 한국어 렌더링 문제를 겪은 뒤 AST 기반 보정과 XeLaTeX 주입을 도입했다.

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

```python
_CJK_SETUP_TEMPLATE = """\
from manim import TexTemplate as _TexTemplate, config as _manim_config
_cjk_tpl = _TexTemplate()
_cjk_tpl.tex_compiler = "xelatex"
_cjk_tpl.output_format = ".xdv"
_cjk_tpl.add_to_preamble(r"\\usepackage{{xeCJK}}")
_cjk_tpl.add_to_preamble(r"\\setCJKmainfont{{{font}}}")
_manim_config.tex_template = _cjk_tpl
"""
```

자막은 LaTeX가 아니라 읽을 수 있는 Unicode/평문으로 정규화한다.

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

서비스 이미지에는 `ffmpeg`, `ffprobe`, `manim`, `latex`, `xelatex`, `dvisvgm`, `xeCJK`, CJK font가 모두 health check 대상이어야 한다.

### 3.3 브리지 전환 정책

브리지 전환은 구현됐지만 실제 피드백에서 어색한 전환이 발생해 기본 OFF로 롤백됐다. 서비스 기본값도 단순하고 안정적인 전환을 유지한다.

```python
crossfade_duration: float = Field(
    default=0.2,
    validation_alias="MANIM_VIDEO_GEN_CROSSFADE_DURATION",
)
scene_bridge_enabled: bool = Field(
    default=False,
    validation_alias="MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED",
)
```

좋은 장면 품질은 브리지보다 각 scene 자체의 연출 품질에서 먼저 확보한다.

### 3.4 narration과 TTS 분리

PoC는 자막과 TTS 대본이 서로 오염되는 문제를 겪었다. 현재는 TTS 텍스트를 후처리한다.

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

실서비스에서도 `narration`은 자막/사용자 표시용, `tts_text`는 음성 합성용으로 별도 저장한다.

## 4. 제품 방향 결정

`visual_scene`은 MVP에서 선택적 핵심 경로로 연다.

선택적 핵심 경로란 다음을 뜻한다.

- scriptify 단계가 장면 품질상 필요하다고 판단하면 `visual_scene`을 선택할 수 있다.
- 단순 수식 전개, 결과 강조, 수직선, 주석 수식은 템플릿을 우선한다.
- 단위원, 넓이, 기하 도형, 공간/벡터, 여러 객체의 동시 움직임처럼 템플릿으로 좋은 장면이 어려운 경우 `visual_scene`을 쓴다.
- `visual_scene` 실패 시 단순 `equation_write`로 바로 축소하지 않고, 가능하면 같은 intent를 표현하는 더 안전한 템플릿 fallback을 고른다.
- 자유형 생성은 사용자 요청 처리 스레드가 아니라 렌더 샌드박스 워커에서만 실행한다.

템플릿은 “자유형을 없애기 위한 대체재”가 아니라 “품질 하한선과 fallback 품질을 높이는 장치”로 본다.

## 5. 서비스 아키텍처

권장 구조는 비동기 job + generation worker + render sandbox이다.

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

주요 컴포넌트는 다음 책임을 가진다.

| 컴포넌트 | 책임 |
| --- | --- |
| `VideoGenerationService` | 요청 검증, job 생성, 사용자 권한/쿼터 확인 |
| `GenerationWorker` | solve, scriptify, TTS, render, compose 단계 orchestration |
| `LlmClientPort` | OpenRouter 및 향후 provider 추상화 |
| `TtsProviderPort` | ElevenLabs, Replicate, Inworld, Grok 등 교체 가능 구조 |
| `ScenePlanner` | segment별 템플릿/자유형 선택 정책 적용 |
| `TemplateRenderer` | 안전한 템플릿 기반 Manim 코드 생성 |
| `FreeformSceneGenerator` | `visual_scene`용 Manim Python 생성과 retry prompt 관리 |
| `ManimCodeSafetyChecker` | AST allowlist, import 제한, 금지 API 검사 |
| `RenderSandbox` | Manim 실행 격리, timeout, CPU/memory 제한, network off |
| `ArtifactStore` | 최종 MP4, segment artifacts, redacted diagnostics 저장 |
| `GenerationRepository` | job/run/segment 상태 저장 |
| `RuntimeHealthCheck` | ffmpeg, ffprobe, manim, xelatex, font 검증 |

## 6. 자유형 Manim Python 설계

현재 PoC의 Manim retry prompt는 이전 실패 원인과 이전 코드를 다음 시도에 넣는다. 이 방향은 유지한다.

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
```

운영 설계에서는 자유형 장면을 다음 단계로 처리한다.

1. `visual_description`을 director brief로 정규화한다.
2. 금지된 요구를 제거한다. 예: 파일 접근, 네트워크 접근, 외부 다운로드, 무한 루프 가능 요구.
3. LLM이 `class Segment(Scene)`만 출력하도록 한다.
4. Python AST로 import, call, attribute 접근을 검사한다.
5. low-quality smoke render를 샌드박스에서 실행한다.
6. 실패 시 error taxonomy와 이전 코드를 넣어 재시도한다.
7. 최대 재시도 후에는 intent-preserving fallback을 선택한다.
8. 최종 high-quality render는 별도 sandbox execution으로 실행한다.

PoC의 render 검증은 Python syntax와 Manim low-quality render를 수행한다.

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
    if ok2:
        return True, ""
    return False, err2
```

서비스에서는 여기에 AST safety check와 container isolation을 추가한다.

### 6.1 자유형 장면 허용 기준

`visual_scene`을 쓰기 좋은 경우는 다음이다.

- 도형 구성, 각도, 넓이, 회전, 벡터, 행렬 변환, 단위원 등 템플릿 표현력이 부족한 경우
- 그래프 하나보다 여러 객체의 관계나 움직임이 설명의 핵심인 경우
- 학생이 “왜 그런지”를 시각적으로 이해해야 하는 장면
- 한 장면에서 object choreography가 필요한 경우

템플릿을 우선할 경우는 다음이다.

- 수식 한 줄 표시
- A 식에서 B 식으로 변환
- 2~5줄의 연속 유도
- 최종 정답 강조
- 수직선의 근/구간 표시
- 계수나 항의 간단한 brace annotation

### 6.2 자유형 fallback 정책

현재 PoC는 실패하면 `equation_write`로 단순화한다.

```python
return (
    EquationWriteTemplate.render_code(
        params={"latex": str(fallback_latex)},
        duration=duration,
        prev_scene_state=segment.prev_scene_state,
    ),
    max_retries,
)
```

서비스에서는 fallback을 다음 순서로 바꾼다.

1. 같은 intent를 표현하는 특화 템플릿 fallback을 찾는다.
2. `graph_plot`, `number_line_plot`, `annotated_equation`, `equation_derivation` 중 가장 가까운 것을 선택한다.
3. 그래도 없을 때만 `highlight_result` 또는 `equation_write`로 축소한다.
4. fallback이 narration과 불일치하면 script repair를 다시 수행한다.

## 7. 템플릿 고도화 계획

템플릿 품질 개선은 1차 범위에 포함한다. 이유는 자유형 장면을 살리더라도 템플릿이 좋아야 다음이 가능하기 때문이다.

- 빠르고 안정적인 장면 생성
- 자유형 실패 시 납득 가능한 fallback
- LLM이 무리하게 `visual_scene`을 남용하지 않도록 유도
- 품질이 일정한 반복 패턴 확보

### 7.1 템플릿 카탈로그 정리

현재 visual type catalog는 prompt와 registry에 중복되어 있다. 서비스에서는 단일 registry metadata를 만들고, prompt도 이 metadata에서 생성한다.

현재 prompt catalog는 코드 안에 긴 문자열로 존재한다.

```python
## Available visual_type catalog (ONLY these strings are allowed)

Each segment MUST use exactly one of the following. The narration MUST describe ONLY what that type can show.
```

서비스에서는 각 visual type에 다음 metadata를 둔다.

- `visual_type`
- 용도
- 필수 params schema
- optional params schema
- narration alignment rule
- render risk level
- fallback candidates
- example params
- template capability tags

### 7.2 1차 개선 대상 템플릿

우선순위가 높은 템플릿은 다음이다.

| 템플릿 | 개선 방향 |
| --- | --- |
| `graph_plot` | 함수 DSL 안전화, 다중 곡선, 접선/교점/극값/영역 음영, label 배치 개선 |
| `number_line_plot` | 열린/닫힌 점, 부등식 구간, 방향 화살표, 여러 구간 표현 |
| `annotated_equation` | brace target 실패 fallback, 여러 annotation 배치 충돌 회피 |
| `equation_derivation` | 긴 수식 frame fitting, 단계별 highlight, annotation 정렬 개선 |
| `intro_problem` | 긴 문제 본문 자동 축소, 줄바꿈, 핵심 조건 강조 |
| `outro_summary` | 줄별 요약, 답 강조, 다음 학습 안내 옵션 |

### 7.3 `graph_plot` 안전화

현재 `func_python`은 문자열 그대로 삽입되어 보안 리스크가 크다.

```python
func_python = str(params.get("func_python", "lambda x: x**2")).strip()
if not func_python.startswith("lambda"):
    func_python = f"lambda x: ({func_python})"
```

```python
graph = axes.plot({func_python}, color={color})
```

서비스에서는 `func_python` 대신 제한된 expression DSL을 받는다.

예시 schema:

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

허용 연산은 `+`, `-`, `*`, `/`, `**`, 괄호, 숫자, `x`, `sin`, `cos`, `tan`, `sqrt`, `log`, `exp`, `abs`로 제한한다. Python 코드 문자열은 생성하지 않는다.

### 7.4 장면 primitive 라이브러리

자유형 Manim 코드 품질을 높이려면 LLM이 매번 low-level Manim API를 직접 조합하지 않게 해야 한다. 서비스 레포에는 scene primitive를 제공한다.

예시 primitive:

- `safe_mathtex(text, max_width, font_size)`
- `safe_text(text, max_width, font_size)`
- `place_title_and_body(title, body)`
- `make_axes_with_graph(expr, features)`
- `make_number_line_with_regions(points, regions)`
- `fade_out_all(scene)`
- `fit_to_frame(mobject)`

자유형 prompt에는 이 primitive 사용을 권장하거나 강제한다. 이렇게 하면 visual_scene의 표현력은 유지하면서 실패율을 줄일 수 있다.

## 8. Job 상태와 데이터 모델

API 서버는 동영상 생성을 즉시 수행하지 않고 job을 만든다.

`video_generation_jobs` 권장 필드:

| 필드 | 설명 |
| --- | --- |
| `id` | job id |
| `user_id` | 요청자 |
| `problem_text_ref` | 원문 또는 암호화 저장 참조 |
| `status` | queued/running/completed/failed/cancelled |
| `stage` | solve/scriptify/tts/render/compose 등 |
| `progress_message` | 사용자 표시 메시지 |
| `settings_profile` | stable/quality/fast |
| `visual_scene_policy` | selective_core |
| `output_video_url` | 최종 MP4 |
| `diagnostic_summary_url` | redacted diagnostic |
| `error_code` | 실패 분류 |
| `error_detail_safe` | 안전한 실패 설명 |
| `created_at`, `started_at`, `finished_at` | 타임스탬프 |

`video_generation_segments` 권장 필드:

| 필드 | 설명 |
| --- | --- |
| `job_id` | job 참조 |
| `segment_id` | 대본 세그먼트 번호 |
| `visual_type` | 템플릿 또는 `visual_scene` |
| `selected_renderer` | template/freeform/fallback |
| `duration_seconds` | TTS 기준 길이 |
| `render_status` | segment 상태 |
| `llm_retry_count` | 자유형 코드 재시도 횟수 |
| `fallback_reason` | fallback 발생 시 사유 |
| `artifact_refs` | segment mp4, ass, code, stderr 참조 |

## 9. 설정 기본값

서비스 기본값은 품질과 안정성의 균형으로 둔다.

| 설정 | 서비스 기본값 | 이유 |
| --- | --- | --- |
| `visual_scene_policy` | `selective_core` | 좋은 장면 확보 |
| `scene_bridge_enabled` | `false` | 기존 피드백상 브리지 기본 ON은 부적합 |
| `disable_equation_chain` | `true` | 겹침 안정성 우선 |
| `disable_prev_scene_state` | `true` | stale object 재발 방지 |
| `consistency_mode` | `error` | narration/visual 불일치 fail-fast |
| `consistency_auto_repair` | `true` | 사용자가 보는 실패율 감소 |
| `script_quality_enabled` | 내부 베타에서 `true` | 점수 정책 calibration 필요 |
| `diagnostic_dump` | 내부 저장소에만 `true` | 장애 분석 필요, 외부 노출 금지 |

현재 PoC의 관련 기본값은 다음과 같다.

```python
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
```

## 10. 저장소와 보안

PoC는 diagnostic dump에 원문, script, visual params, 생성 코드가 저장된다.

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

서비스에서는 diagnostic을 두 계층으로 분리한다.

- 내부 diagnostic: 문제 원문, script, generated code, stderr tail, segment artifacts 포함
- 사용자 diagnostic: 실패 단계, 안전한 오류 메시지, 재시도 가능 여부, 최종 산출물 링크만 포함

내부 diagnostic은 object storage private bucket에 저장하고, 접근은 운영자 권한으로 제한한다.

## 11. API 제안

생성 요청:

```http
POST /api/video-generations
```

요청 body:

```json
{
  "problemText": "x^2 + 2x + 1 = 0을 풀어라",
  "profile": "quality",
  "options": {
    "allowVisualScene": true,
    "burnSubtitles": true
  }
}
```

응답:

```json
{
  "jobId": "vg_...",
  "status": "queued"
}
```

상태 조회:

```http
GET /api/video-generations/{jobId}
```

응답:

```json
{
  "jobId": "vg_...",
  "status": "rendering",
  "stage": "render",
  "progressMessage": "5번째 장면을 렌더링 중입니다.",
  "outputVideoUrl": null,
  "error": null
}
```

## 12. 테스트 계획

### 12.1 단위 테스트

- JSON extraction/repair
- script consistency validator
- script quality scoring
- `narration`/`tts_text` 분리 후처리
- subtitle normalization
- LaTeX backslash normalization
- template registry metadata generation
- graph expression DSL parser
- Manim AST safety checker
- freeform fallback selector

### 12.2 통합 테스트

- Fake LLM + Fake TTS + fake render로 job 상태 전이 검증
- 실제 FFmpeg 최소 합성 검증
- Manim smoke render는 별도 heavy CI 또는 nightly에서 실행
- sandbox timeout, memory limit, network block 검증

### 12.3 E2E 회귀 세트

- 이차방정식 인수분해
- 이차함수 그래프와 근
- 수직선과 구간
- 계수 주석 설명
- 기하 도형 설명
- 단위원/삼각함수
- 긴 한국어 문제 본문
- CJK 포함 LaTeX
- TTS provider 429/retry
- 자유형 `visual_scene` 실패 후 intent-preserving fallback

## 13. 단계별 구현 계획

### Phase 1: PoC 코어 이식과 job화

- API는 job 생성과 상태 조회만 제공한다.
- Generation worker에서 PoC pipeline을 stage 단위로 감싼다.
- object storage에 최종 MP4와 내부 diagnostic을 저장한다.
- 템플릿 경로와 자유형 경로를 모두 살린다.

### Phase 2: 자유형 Manim 안전장치

- AST safety checker 추가
- render sandbox worker 분리
- network off, CPU/memory/wall-clock timeout 적용
- retry taxonomy와 fallback selector 도입
- `visual_scene` 사용률, 실패율, fallback율을 metric으로 저장

### Phase 3: 템플릿 고도화

- visual type metadata registry 도입
- prompt catalog를 metadata에서 생성
- graph DSL로 `func_python` 제거
- number line, annotated equation, equation derivation layout 개선
- scene primitive 라이브러리 추가

### Phase 4: 품질 자동화

- script quality guard를 내부 베타에서 먼저 활성화하고, curated E2E 기준을 만족하면 `quality` profile의 기본값으로 승격
- curated E2E set nightly 운영
- 프레임 기반 겹침/tofu heuristic을 worker diagnostic에 연결
- 좋은 자유형 장면을 template 또는 primitive로 흡수하는 개선 루프 운영

## 14. 성공 기준

MVP 성공 기준은 다음이다.

- `visual_scene`을 포함한 curated 문제 세트에서 최종 MP4 생성률 90% 이상
- 자유형 장면 실패 시 job 전체 실패 대신 fallback 또는 script repair로 복구되는 비율 80% 이상
- 생성 job은 API 요청 스레드를 점유하지 않는다.
- 렌더 샌드박스는 timeout과 리소스 제한을 강제한다.
- 최종 MP4, segment metadata, 내부 diagnostic이 저장된다.
- 사용자에게 노출되는 오류 메시지에는 API key, raw stderr 전체, generated code가 포함되지 않는다.
- 템플릿 기반 fallback 영상도 narration과 화면이 불일치하지 않는다.

## 15. 결론

실제 서비스에서는 자유형 Manim Python을 막지 않는다. 좋은 장면을 만들려면 `visual_scene`이 필요하다. 다만 자유형 코드를 API 서버에서 직접 실행하거나, 실패 시 무조건 `equation_write`로 축소하는 PoC 방식은 운영 품질에 부족하다.

따라서 제품 방향은 `visual_scene`을 선택적 핵심 경로로 유지하고, 템플릿 고도화·샌드박스·정적 검증·smoke render·intent-preserving fallback을 함께 구현하는 것이다. 템플릿은 자유형의 대체재가 아니라 안정성과 품질 하한선을 만드는 기반으로 다룬다.
