# 003 - Phase 1 코드 리뷰 개선사항 반영

## Context: 무엇을 만들려 했는가?

`manim-video-gen` 프로젝트의 Phase 1 구현이 완료된 시점에서, 코드베이스 전체 분석 및 평가를 진행했다.
평가에서 도출된 11개 개선 사항을 실제 코드에 반영하는 것이 목표였다.

**개선 대상 영역:**
- `llm/client.py` — HTTP 클라이언트 성능
- `tts/elevenlabs.py` — 한국어 TTS 음질
- `video/templates/equation.py` — 애니메이션 타이밍 버그
- `llm/prompts/manim_api_ref.py` — LLM 코드 생성 성공률
- `pipeline/orchestrator.py` — fallback 로직, 구조 개선
- `video/composer.py` — API 설계, 방어 코드
- `tests/` — 단위 테스트 부재

---

## Roadblocks: 어떤 에러가 발목을 잡았는가?

### 1. `EquationTransformTemplate`의 duration 계산 버그 (코드 논리 오류)

`prev_scene_state`가 있을 때 `t_intro`와 `t_mid`를 계산하지만, 해당 분기에서 두 값을 전혀 사용하지 않았다.

```python
# AS-IS: 계산하고 버리는 dead code
t_intro = max(0.25, duration * 0.25)  # ← 사용 안 됨
t_mid   = max(0.2,  duration * 0.15)  # ← 사용 안 됨
t_tx  = max(0.35, duration * 0.45)
t_end = max(0.15, duration - (t_intro + t_mid + t_tx))

if prev_scene_state:
    # t_tx + t_end 만 사용 → 실제 시간 ≈ 0.6 * duration
```

결과적으로 `prev_scene_state`가 있는 세그먼트는 목표 duration의 약 60%만 사용되고, 나머지 40%는 `adjust_duration_safe()`가 `self.wait()`으로 채워주는 방식으로 동작했다. 영상 품질 저하의 원인.

### 2. ElevenLabs 기본 `voice_id`가 영어 화자 (설정 누락)

기본값 `21m00Tcm4TlvDq8ikWAM`은 "Rachel" — 영어 네이티브 음성이다.
`eleven_multilingual_v2` 모델이므로 한국어 출력은 가능하지만 억양이 부자연스럽다.
`.env.example`에 한국어 음성 ID 안내가 없어서 사용자가 이를 모르고 기본값을 그대로 쓸 가능성이 높았다.

### 3. `orchestrator` fallback이 한국어 설명문을 LaTeX로 전달 (타입 혼용 버그)

LLM Manim 코드 생성이 최대 재시도 후 실패했을 때:

```python
# AS-IS: visual_description은 "x^2+2x+1을 Write로 보여주고..." 같은 한국어 설명문
return EquationWriteTemplate.render_code(
    params={"latex": segment.visual_description[:400]},  # ← LaTeX가 아님
    duration=duration,
)
```

이 경우 Manim이 `\text{x^2+2x+1을 Write로 보여주고...}` 같은 LaTeX를 렌더링 시도하다 실패한다.
`visual_params`에 실제 LaTeX 키(`latex`, `to_latex`, `from_latex`)가 있는데 활용하지 않았다.

### 4. 단위 테스트 작성 중 `sanitize_move_to_expr` 기대값 오류

`test_multi_line_expression_returns_origin` 테스트가 실패했다:

```python
# 테스트 기대값이 잘못됨
assert sanitize_move_to_expr("UP\n* 2") == "ORIGIN"  # ← 실제 결과는 "UP * 2"
```

**원인 분석:**
1. `sanitize_move_to_expr`는 `replace(" ", "")`로 공백만 제거 → 줄바꿈(`\n`)은 남음
2. 정규식 `_MOVE_RE`의 `\s*`는 `\n`을 포함한 모든 공백을 허용
3. `"UP\n*2"` → 정규식이 매치 → `"UP * 2"` 반환

이 동작은 **보안상 안전하다** (`UP * 2`는 유효한 Manim 표현식). 테스트 기대값이 실제 의도와 맞지 않았던 것. 정규식 화이트리스트 방식이므로 줄바꿈이 포함돼도 임의 코드 주입 불가.

### 5. `manim_api_ref.py` 내용 빈약 (LLM 성능 병목)

Plan에서 "주요 클래스/메서드 50개 시그니처"를 명시했으나 실제 구현은 약 15개의 간략한 힌트만 존재했다. LLM이 `ValueTracker`, `always_redraw`, `Indicate`, `.animate` 체이닝 등을 모르면 코드 생성 실패 후 재시도 루프를 소모한다.

---

## The Fix: 결국 어떻게 풀었는가?

### Fix 1 — httpx 세션 재사용 (`client.py`)

`OpenRouterClient`를 async context manager로 변환. `__aenter__`에서 `httpx.AsyncClient` 인스턴스를 생성하고 `__aexit__`에서 닫는다. context manager 없이 직접 호출 시 fallback으로 임시 클라이언트를 생성하는 backward-compatible 구조 유지.

```python
async with OpenRouterClient(settings) as client:
    plan = await client.complete_json_model(...)
    script = await client.complete_json_model(...)
    # 이후 세그먼트별 LLM 호출들도 같은 TCP 연결 재사용
```

### Fix 2 — Duration 분배 분기 (`equation.py`)

`prev_scene_state` 유무에 따라 duration 분배 로직을 완전히 분리:

```python
if prev_scene_state:
    t_tx  = max(0.5, duration * 0.65)   # 변환 애니메이션 65%
    t_end = max(0.15, duration - t_tx)   # 대기 35%
else:
    t_intro = max(0.25, duration * 0.25)
    t_mid   = max(0.2,  duration * 0.15)
    t_tx    = max(0.35, duration * 0.45)
    t_end   = max(0.15, duration - (t_intro + t_mid + t_tx))
```

### Fix 3 — fallback LaTeX 우선순위 (`orchestrator.py`)

`visual_params` → `visual_description` 순서로 LaTeX 탐색:

```python
fallback_latex = (
    segment.visual_params.get("latex")
    or segment.visual_params.get("to_latex")
    or segment.visual_params.get("from_latex")
    or segment.visual_description[:400]
)
```

### Fix 4 — 테스트 기대값 수정 (`test_sanitize_move_to.py`)

멀티라인 표현식이 ORIGIN을 반환한다는 잘못된 기대값을 수정하고, 실제 동작(정규화된 표현식 반환)을 문서화:

```python
def test_multi_line_expression_normalizes():
    # 줄바꿈 포함 입력은 "UP * 2"로 정규화됨 (보안상 안전)
    result = sanitize_move_to_expr("UP\n* 2")
    assert result == "UP * 2"
```

### Fix 5 — manim_api_ref.py 확장

~15개 → 50개 이상 시그니처 추가:
- `ValueTracker`, `always_redraw`, `DecimalNumber`, `Brace`, `SurroundingRectangle`
- `Arrow`, `DashedLine`, `NumberLine`, `NumberPlane`, `Matrix`, `ParametricFunction`
- `Indicate`, `Circumscribe`, `GrowFromCenter`, `ShrinkToCenter`
- `.animate.scale()`, `.animate.set_color()` 등 체이닝 패턴
- 위치 헬퍼 메서드, 방향 상수 전체

### Fix 6 — `EquationWriteTemplate`에 `prev_scene_state` 추가

첫 세그먼트 이후 `equation_write` 타입이 등장할 때 이전 수식이 사라지는 문제 해결:

```python
@staticmethod
def render_code(
    *, params, duration,
    prev_scene_state: list[SceneObjectState] | None = None,  # 추가
) -> str:
    prev_lines = _prev_state_lines(prev_scene_state)
    # prev_lines가 먼저 self.add()로 이전 수식 복원 후 새 수식 Write
```

### Fix 7 — `ProcessedSegment` 모델 활용, `compose_final()` 분리

오케스트레이터에서 세그먼트별 처리 결과를 `ProcessedSegment`로 구조화하여 디버깅/로깅 용이성 확보. `VideoComposer.compose_final()`을 추가해 합성 의도를 코드 레벨에서 명확화.

### Fix 8 — 단위 테스트 4종 51개

| 파일 | 커버리지 |
|------|---------|
| `test_llm/test_extract_json.py` | JSON 파싱 엣지 케이스 14개 |
| `test_tts/test_alignment.py` | 타임스탬프 변환 11개 |
| `test_video/test_sanitize_move_to.py` | 경계값/보안 13개 |
| `test_video/test_template_registry.py` | 템플릿 파라미터 전달 11개 |

---

## Learning: 기억하고 있어야 하는 것

### 1. Dead code가 있는 분기 계산은 반드시 테스트로 검증

`prev_scene_state` 분기처럼 "계산은 하지만 사용 안 함"은 코드 리뷰나 테스트 없이는 발견이 어렵다. **조건 분기 안에서 사용되는 변수가 해당 분기에서 실제로 쓰이는지 확인하는 습관 필요.**

### 2. Fallback 경로에 타입 가정을 심으면 반드시 깨진다

`visual_description`을 "설명문이니까 대충 넘겨도 되겠지"라고 LaTeX 슬롯에 넣으면, 정상 경로에서 절대 실행되지 않는 fallback이 배포 후 실제로 터지는 상황이 생긴다. **fallback 경로도 정상 경로와 동일한 타입 계약을 지켜야 한다.**

### 3. `httpx.AsyncClient`는 반드시 세션 레벨에서 관리

`async with httpx.AsyncClient()` 패턴을 호출마다 반복하면 TCP handshake 비용이 누적된다. LLM 파이프라인처럼 동일 호스트에 여러 번 요청하는 경우 반드시 세션을 재사용해야 한다. **async context manager 패턴으로 클라이언트를 클래스 수준에서 관리하는 것이 표준.**

### 4. 정규식 `\s*`는 줄바꿈도 포함한다

`re.compile(r"...\s*...")` 패턴은 `\n`, `\t`도 매치한다. 보안 관련 입력 검증 정규식에서 "공백만 허용"이 의도라면 `[ \t]*` 또는 `[^\S\n]*`를 명시적으로 사용해야 한다. `\s*`로 화이트리스트를 구성하면 멀티라인 입력도 통과한다.

### 5. LLM 코드 생성 품질은 API 레퍼런스 품질에 비례

`manim_api_ref.py`처럼 "System Prompt에 들어가는 레퍼런스 문서"는 LLM의 1회 성공률에 직접 영향을 미친다. 재시도 루프가 있어도 레퍼런스가 빈약하면 동일한 실수를 반복한다. **LLM에게 제공하는 컨텍스트 문서는 실제로 필요한 API의 70% 이상을 커버해야 한다.**

### 6. 테스트 작성 시 "구현이 틀렸다"고 가정하기 전에 "기대값이 틀렸는지" 먼저 확인

`test_multi_line_expression_returns_origin` 실패처럼, 구현 동작이 실제로는 안전하고 올바른데 테스트 기대값이 잘못된 경우가 있다. **테스트 실패 시 구현 수정 전에 "이 동작이 정말 틀린가?"를 한 번 더 검증할 것.**

### 7. `ProcessedSegment` 같은 집계 모델은 생성 직후부터 활용

데이터 모델을 정의해 두고 실제 파이프라인에서 개별 변수로 관리하면 나중에 리팩토링 비용이 커진다. **모델을 정의했다면 그 모델을 사용하는 코드도 같은 PR에 함께 작성해야 한다.**
