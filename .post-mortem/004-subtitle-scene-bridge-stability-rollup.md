# 004 — 자막·씬 전환·브리지 안정화 통합 회고

> 범위: 최근 사용자 피드백(자막 수식 깨짐, 씬 겹침, `\text{}` 노출, 요약 가독성, 유기적 전환 요구)부터 최종 E2E 검증까지의 전체 정리

---

## 1) 배경 / 목표

사용자 피드백의 핵심은 다음 5가지였다.

1. 자막에서 수식 표기가 깨짐 (`f_{x₁x₁}` 류)
2. 화면 라벨에 LaTeX 조각이 그대로 노출 (`\text{ 극대}`)
3. 특정 구간 씬 겹침/잔상 재발
4. 마지막 요약의 줄 간격이 좁아 가독성 낮음
5. 씬-씬 연결이 더 자연스럽고 유기적이길 원함

목표는 “증상 완화”가 아니라 **재발 방지형 구조 개선**이었다.

---

## 2) Root Cause 조사 결과

### A. 자막 수식 깨짐

기존 자막 escape가 백슬래시를 제거한 뒤 중괄호를 escape하여,
`f_{x₁x₁}`가 사실상 `f_\{x₁x₁\}` 형태로 변질될 수 있었다.

```python
def _ass_escape(text: str) -> str:
    t = text.replace("\\", "")
    t = t.replace("{", "\\{").replace("}", "\\}")
```

### B. `Text(...)` 라벨 경로의 LaTeX 잔재

그래프/수직선 라벨에서 CJK 라벨이 `Text(...)`로 렌더될 때,
`\text{...}`, `\,` 같은 LaTeX 조각이 사전 정리 없이 들어가 literal 노출이 발생했다.

### C. 씬 잔상 겹침

- cleanup 주입 로직이 `FadeOut` 존재만으로 cleanup이 충분하다고 판단하는 경우가 있었고,
- 체인 렌더 일부 경로에서 “현재 상태”를 단일 수식(`cur`) 중심으로 다뤄 보조 객체 잔상이 남을 수 있었다.

### D. 요약 가독성

`outro_summary`가 멀티라인 단일 `Text(...)`라 줄 간격 제어가 제한적이었다.

### E. 씬 경계 전환 방식

기본은 하드컷/concat 중심이어서, 의미 기반 연결(브리지 transform)이 항상 있는 구조가 아니었다.

---

## 3) 적용한 수정

## 3-1. 자막 정규화 계층 추가

ASS escape 전에 LaTeX 잔재를 “읽을 수 있는 자막 문자열”로 정규화하는 계층을 도입했다.

```python
def _normalize_subtitle_narration(text: str) -> str:
    t = str(text)
    t = t.replace(r"\,", " ").replace(r"\;", " ").replace(r"\:", " ")
    t = _TEXT_CMD_RE.sub(r"\1", t)
    t = _SUBSCRIPT_BRACE_RE.sub(r"_(\1)", t)
    t = _SUPERSCRIPT_BRACE_RE.sub(r"^(\1)", t)
    t = _TEX_CMD_RE.sub("", t)
    t = t.replace("\\", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t
```

그 후 `_ass_escape()`는 이 정규화 결과를 기반으로만 동작하도록 변경했다.

---

## 3-2. Text 라벨용 sanitize 함수 분리

LaTeX 수식 경로(`MathTex`)와 일반 라벨 경로(`Text`)를 분리했다.

```python
def sanitize_latex_for_text_label(text: str) -> str:
    s = str(text)
    s = _SPACING_CMD_RE.sub(" ", s)
    s = _TEXT_CMD_CAPTURE_RE.sub(r"\1", s)
    s = _GENERIC_LATEX_CMD_RE.sub("", s)
    s = s.replace("\\", "")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s
```

`graph_plot`, `number_line_plot`의 CJK `Text(...)` 라벨에 이 함수를 적용했다.

---

## 3-3. cleanup 불변식 강화

핵심 정책: **`self.clear()`는 반드시 보장**.

```python
has_clear = "self.clear()" in code
has_fadeout = bool(re.search(...))
if has_clear and has_fadeout:
    return code

if not has_fadeout:
    # FadeOut 주입
if not has_clear:
    # self.clear() 주입
```

즉, `FadeOut`이 이미 있어도 `clear`가 없으면 반드시 추가한다.

---

## 3-4. 체인 렌더 active-state 개선

파생 단계/스텝 이후 현재 화면 상태를 전체 mobjects 기반으로 갱신해,
다음 전환에서 잔상 누수를 줄였다.

```python
active = VGroup(*list(self.mobjects))
```

또한 highlight 전환 시 group 상태를 대상으로 치환되도록 경로를 정리했다.

---

## 3-5. outro summary 가독성 개선

멀티라인 단일 텍스트 대신 줄별 `VGroup + arrange`로 변경.

```python
summary_group = VGroup(
    Text('...'),
    Text('...'),
    Text('...'),
).arrange(DOWN, aligned_edge=LEFT, buff=0.32)
```

줄 간격(`buff`)을 명시적으로 제어 가능하게 만들었다.

---

## 3-6. 의미 기반 브리지 전환 도입 (전 경계 시도 + 즉시 fallback)

새 설정:

```env
MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED=true
```

구현 정책:

1. 인접 경계마다 브리지 후보를 계산
2. 수식 기반 매핑이 가능하면 짧은 transform 브리지 렌더
3. 실패/불확실하면 즉시 기존 hard cut 유지

브리지 렌더는 `equation_transform` 템플릿 + 무음 오디오 merge로 삽입했다.

---

## 4) 테스트 보강

다음 회귀 테스트를 추가/보강했다.

- subtitle 정규화/escape 회귀
- latex_korean 라벨 sanitize 회귀
- graph_plot CJK 라벨 sanitize 반영 확인
- cleanup 주입(`FadeOut`만 있고 `clear` 없는 케이스) 회귀
- chain renderer active-state/치환 회귀
- outro summary 레이아웃 문자열 회귀
- orchestrator bridge spec 계산 회귀
- composer bridge API fallback 동작 회귀

결과:

- 타깃 테스트: `56 passed`
- 전체 테스트: `155 passed`

---

## 5) E2E 검증 결과

크레딧 복구 후 전체 파이프라인 재실행 성공.

- 출력 파일: `artifacts/final_bridge_verify.mp4`
- 진단 덤프: `artifacts/runs/20260411_213306_159fa9a4/`
- final exists: `true`
- segments: `17`
- elapsed: `~959.64s`

실행 로그에서 브리지 삽입 확인:

```text
inserted semantic bridge between seg 5 -> 6
```

생성된 브리지 세그먼트 코드 예:

```python
eq1 = MathTex('H = \\begin{pmatrix} {{2}} & {{1}} \\\\ {{1}} & {{4}} \\end{pmatrix}')
eq2 = MathTex('\\Rightarrow H \\succ 0 \\quad (\\text{Positive Definite})')
self.play(TransformMatchingTex(eq1, eq2), run_time=0.350)
```

또한 run 산출물에서 아래를 확인했다.

- ASS 파일에 `\text{...}`/`_{...}` 깨짐 패턴 미검출
- `Text('...\\text{...')` / `Text('...\\,')` 패턴 미검출
- 각 세그먼트 코드 종료부 `FadeOut + clear` 보장
- outro summary가 줄별 `VGroup(...).arrange(..., buff=0.32)`로 생성

---

## 6) 남은 리스크 / 한계

1. 일부 equation chain은 여전히 chain 렌더 실패 후 fallback 로그가 발생할 수 있음.
   - 단, fallback 경로에서도 cleanup/자막/라벨 정리는 유지됨.

2. 브리지 매핑은 현재 “수식 중심”이다.
   - `visual_scene` 같은 자유형 장면 간 의미 브리지는 추가 설계 여지가 큼.

3. 브리지 품질 고도화(객체 단위 token map)는 다음 단계 과제.

---

## 7) 운영 메모

- 브리지 비활성화가 필요하면:

```env
MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED=false
```

- 재현 분석 권장 옵션:

```env
MANIM_VIDEO_GEN_DIAGNOSTIC_DUMP=true
MANIM_VIDEO_GEN_KEEP_WORKSPACE=true
```

---

## 8) 이번 배치 커밋

- commit: `e1560e6`
- message: `fix: 자막·씬 전환 안정화와 브리지 전환 보강`

핵심 변화는 “문제별 임시 패치”가 아니라,
**정규화 계층 + cleanup 불변식 + 안전한 브리지 fallback**으로 구조화한 점이다.
