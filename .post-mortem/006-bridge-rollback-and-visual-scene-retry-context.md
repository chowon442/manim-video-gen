# 006 — 브릿지 롤백(기본 OFF) 및 visual_scene 재시도 컨텍스트 강화

> 범위: 브릿지 품질 피드백 대응(“일단 그냥 넘어가게”) + visual_scene 재시도 실패 분석 및 프롬프트 개선까지의 정리

---

## 1) 배경

최근 변경으로 semantic bridge를 경계마다 삽입하도록 강화했지만, 실제 사용 영상에서 다음 피드백이 반복됐다.

1. 특정 구간 전환이 자연스럽지 않음
2. 브릿지가 장면 의미를 오히려 어색하게 연결함
3. 사용자 요구: 당분간 **브릿지 없이 그냥 넘어가는 방식**으로 되돌리기

동시에 별도 run에서 visual_scene 생성이 3회 재시도 후 실패하여 equation_write로 폴백되면서,
자막의 “그래프로 보면 …”과 화면의 텍스트-only 장면이 불일치하는 문제가 확인됐다.

---

## 2) 조사 결과

### A. 브릿지 품질 이슈는 기능 고장보다 “정책 미스매치”

- 로직상 브릿지는 정상 삽입/보정됐지만,
- 사용자 기대는 “안전하고 단순한 컷+짧은 crossfade”였고,
- 현재는 의미 기반 transform 삽입이 기본이라 체감 품질과 요구가 충돌했다.

즉, 버그보다 기본 정책(default)이 사용자 선호와 어긋난 케이스.

---

### B. visual_scene 3회 실패의 실제 원인

재시도 코드(`scene_05_try0/1/2.py`)를 재검증한 결과:

1) try0

```text
AttributeError: 'ThreeDCamera' object has no attribute 'animate'
```

실패 코드 패턴:

```python
self.play(
    FadeIn(desc_text, shift=LEFT),
    self.camera.animate.set_euler_angles(...),
    run_time=4.0,
)
```

2) try1, try2

```text
TypeError: Unexpected argument None passed to Scene.play().
```

실패 코드 패턴:

```python
self.play(
    FadeIn(desc_vgroup, shift=LEFT),
    self.move_camera(...),
    run_time=...,
)
```

`self.move_camera(...)`가 animation object가 아니라 `None` 경로로 들어가며 실패.

---

## 3) 적용한 변경

## 3-1. 전환 정책 기본값 롤백 (요구사항 반영)

사용자 합의: **브릿지 기능은 남기되 기본값 OFF**, 대신 **짧은 crossfade 기본값 사용**.

`src/manim_video_gen/config.py`

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

`.env.example` 동기화:

```dotenv
MANIM_VIDEO_GEN_CROSSFADE_DURATION=0.20
MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED=false
```

결과: out-of-the-box 동작이 “브릿지 없는 단순 전환 + 짧은 crossfade”로 바뀜.

---

## 3-2. 재시도 프롬프트에 이전 실패 원인 반영 강화

요구사항: 특정 에러 하드코딩이 아니라, **이전 실패 원인을 다음 시도에서 참고**하도록 일반화.

`src/manim_video_gen/llm/prompts/manim_gen.py`

```python
if prior_errors:
    prior += "\n\nPrevious errors (fix them):\n" + ...
    prior += (
        "\n\nRetry instruction:\n"
        "- Analyze the exact root causes in the previous errors above.\n"
        "- Rewrite the scene to avoid those failures.\n"
        "- Do not repeat the failing patterns from previous attempts.\n"
        "- Explain briefly in code comments where you changed the risky part."
    )
```

즉, 재시도 시 입력에

- 이전 에러 원문
- 이전 전체 코드 시도본
- 재발 금지/원인 분석 지시

를 함께 넣어 반복 실패를 줄이도록 개선.

---

## 4) 테스트

추가/수정:

1. `tests/test_config_defaults.py`
   - 전환 기본값이
     - `crossfade_duration == 0.2`
     - `scene_bridge_enabled is False`
     로 동작하는지 회귀 검증

2. `tests/test_llm/test_manim_prompt_retry_context.py`
   - 재시도 프롬프트에 이전 에러/코드/Retry instruction이 포함되는지 검증

실행 결과:

```text
186 passed in 0.55s
```

---

## 5) 운영 가이드

기본값은 브릿지 OFF지만 필요 시 즉시 켤 수 있다.

```dotenv
MANIM_VIDEO_GEN_SCENE_BRIDGE_ENABLED=true
```

crossfade 강도 조절:

```dotenv
MANIM_VIDEO_GEN_CROSSFADE_DURATION=0.20
```

---

## 6) 결론

이번 배치의 핵심은 “브릿지 품질 자체를 억지로 밀어붙이기”가 아니라,

1. 기본 UX를 사용자 선호(단순/안정)로 되돌리고,
2. visual_scene 재시도에서 이전 실패 맥락을 더 강하게 반영해
   같은 실패 패턴 반복을 줄인 점이다.

즉, 정책은 보수적으로, 재시도는 더 똑똑하게 조정한 변경이다.
