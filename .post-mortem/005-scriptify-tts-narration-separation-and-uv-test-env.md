# 005 — narration/tts 분리 품질 개선 & `uv run pytest` 실행 경로 정리

> 범위: 사용자 피드백(해설 톤, TTS 발화 자연스러움, 자막/음성 분리 오염) 대응 + 테스트 실행 환경 혼선 정리

---

## 1) Context

사용자 요구는 3가지였다.

1. **나레이션을 해설 영상 톤(선생님 설명 스타일)으로 개선**
2. **`tts_text`를 실제 사람이 말하는 것처럼 자연스럽게 개선**
   - 특히 `(x+3)`를 `"괄호 열기 ... 괄호 닫기"`로 읽는 문제 제거
3. **자막(narration)과 TTS 대본(tts_text) 분리 오염 원인 확인**

추가로, 테스트 실행 시 `python/pytest`와 `uv run` 경로가 섞이며 재현성이 흔들리는 문제가 있었다.

---

## 2) Root Cause 조사

### A. split 이후 `tts_text` 재보정 누락

스크립트 생성 직후에는 `tts_text` 보정이 한 번 수행되지만, 그래프 전환 문장 분리(split) 이후에는 재보정이 없었다.

```python
script = _ensure_tts_text(script)
script = split_script_transition_tails(script)
```

split 내부에서 lead/tail 생성 시 `tts_text`를 다시 세팅하고 있었기 때문에, 이 구간에서 자연 발화 품질이 다시 저하될 수 있었다.

---

### B. 프롬프트가 비자연 발화를 허용

기존 scriptify 규칙이 괄호 발화를 다음처럼 허용했다.

```text
"괄호 엑스 더하기 일 괄호닫기 의 제곱"
```

이 규칙 자체가 비자연 발화를 생성하도록 유도했다.

---

### C. validator의 분리 품질 규칙 부족

기존 정합성 검사는 narration-visual 불일치 중심이었다.

- `tts_text`에 `괄호 열기/닫기`가 포함되어도 통과 가능
- equation 계열에서 narration이 과도한 발화체(`엑스 세제곱 더하기 ...`)여도 탐지 불가

---

### D. 테스트 실행 환경 혼선

초기에는 아래처럼 서로 다른 인터프리터/pytest 경로가 섞였다.

```text
python3 -m pip show replicate -> not found
uv run python -m pip show replicate -> replicate installed
uv run which pytest -> /Library/.../bin/pytest  (시스템 pytest)
uv run python -m pytest --version -> No module named pytest
```

즉, `uv run`을 써도 `.venv`에 `pytest`가 없으면 시스템 pytest로 새는 상황이었다.

---

## 3) 적용한 수정

## 3-1. `polish_tts_text()` 도입

`tts_text` 전용 정규화 함수를 추가해 괄호 발화 마커 제거 및 발화형 보정을 수행했다.

```python
def polish_tts_text(text: str) -> str:
    out = polish_narration_math(text)
    out = _strip_parenthesis_markers(out)
    ...
    out = re.sub(r"(?<=[0-9A-Za-z가-힣])\s*-\s*(?=[0-9A-Za-z가-힣])", " 빼기 ", out)
    ...
    return out
```

핵심 효과:

- `괄호 열기/닫기` 제거
- 잔여 기호/변수 발화 보정
- split 이후에도 동일 보정 루틴 재사용 가능

---

## 3-2. split 이후 재보정 강제

split 함수의 반환 지점에서 `_ensure_tts_text()`를 다시 태우도록 변경했다.

```python
def split_script_transition_tails(script: VideoScript) -> VideoScript:
    ...
    split_script = script.model_copy(update={"segments": fixed})
    return _ensure_tts_text(split_script)
```

그리고 `_ensure_tts_text()`는 `polish_tts_text()`를 사용하도록 변경.

```python
if not tts:
    tts = polish_tts_text(s.narration)
else:
    tts = polish_tts_text(tts)
```

---

## 3-3. 정합성 규칙 추가

validator에 아래 룰을 추가했다.

1. **`E_TTS_SPOKEN_PARENTHESIS` (error)**
   - `tts_text`에 `괄호 열기/닫기` 류 토큰이 있으면 오류

2. **`W_NARRATION_OVERLY_PHONETIC` (warn)**
   - equation 계열에서 narration이 과도한 발화체면 경고

```python
if _contains_any(tts_text, _SPOKEN_PARENTHESIS_TOKENS):
    issues.append(
        ValidationIssue(
            severity="error",
            code="E_TTS_SPOKEN_PARENTHESIS",
            ...
        )
    )

if vt in _EQUATION_VISUAL_TYPES and _looks_overly_phonetic_math(narration):
    issues.append(
        ValidationIssue(
            severity="warn",
            code="W_NARRATION_OVERLY_PHONETIC",
            ...
        )
    )
```

---

## 3-4. scriptify 프롬프트 강화

프롬프트에 다음 정책을 명시했다.

- narration: teacher-style 설명 문장 + 수식 가독성 유지
- tts_text: 완전 발화형
- `괄호 열기/닫기` 발화 금지

```text
Parentheses: (x+1)² → "엑스 더하기 일의 제곱" (natural spoken form)
NEVER say spoken marker words such as "괄호 열기", "괄호 닫기", ...
```

---

## 3-5. 실행 환경/문서 정리

`README`를 `uv` 중심으로 통일했다.

```bash
uv sync --extra dev
uv run pytest
uv run python -m manim_video_gen "..."
```

또한 `python/pytest` 직접 실행 시 시스템 인터프리터를 탈 수 있음을 명시했다.

---

## 4) 테스트

신규/보강 테스트:

- `test_math_notation.py`
  - `polish_tts_text` 괄호 발화 제거
  - `(x+3)^2` 발화형 변환
- `test_consistency_validator.py`
  - `E_TTS_SPOKEN_PARENTHESIS`
  - `W_NARRATION_OVERLY_PHONETIC`
- `test_narration_scene_split.py`
  - split 이후 `tts_text` 재보정 적용

실행 결과:

```bash
uv run pytest -q
```

```text
183 passed in 0.63s
```

---

## 5) 배포/형상 이력

- commit: `5bc58ff`
- message: `fix: harden LLM JSON parsing and polish TTS script quality`
- push: `main -> origin/main`

---

## 6) Learning

1. **분리 파이프라인은 “후속 변환 단계”까지 포함해 검증해야 한다.**
   - 1차 보정 후 split이 값을 다시 만들면, split 뒤 재보정이 없으면 품질이 다시 깨진다.

2. **프롬프트가 허용한 나쁜 예시는 실제 산출물로 나온다.**
   - `괄호 열기/닫기` 같은 옵션은 결국 모델이 선택한다. 금지 규칙으로 바꿔야 한다.

3. **자막/음성 분리는 규칙 + 후처리 + validator 3중 방어가 필요하다.**
   - 어느 한 층만으로는 재발을 막기 어렵다.

4. **테스트 실행 경로를 통일하지 않으면 재현성이 무너진다.**
   - `uv run` + `.venv` 기준으로 도구 체인을 고정하는 것이 안전하다.
