# 007 — xelatex CJK 폴백 템플릿 크래시

> 목적: 동일 장애를 다시 겪지 않기 위한 사후 정리. (manim-video-gen, 2026)

---

## context: 무엇을 만들려 했는가?

- **명령어:** `uv run python -m manim_video_gen short -f short.md --from-plan artifacts/plan.json --unit 1`
- **흐름:** LLM이 각 세그먼트의 Manim 코드를 생성 → 3회 실패 시 폴백 템플릿 사용 → Manim 렌더
- **세그먼트 구성:** 5개 세그먼트 (0~4), 각각 TTS 오디오 + Manim 영상 → FFmpeg 합성

---

## roadblocks: 어떤 에러가 발목을 잡았는가?

### 1) xelatex 미설치

| 증상 | 원인 |
|------|------|
| `FileNotFoundError: [Errno 2] No such file or directory: 'xelatex'` | 폴백 템플릿이 CJK(한글) 템플릿을 주입하면서 `xelatex`를 요구했으나 시스템에 미설치 |

**전체 흐름:**
- 세그먼트 3의 LLM 코드 생성이 3회 실패
- `resolve_short_fallback_template()` → `short_concept_equation` 템플릿 선택
- 템플릿이 `MathTex('수식', ...)` (한글 플레이스홀더) 생성
- `inject_cjk_if_needed()`가 한글 감지 → xelatex 기반 CJK TexTemplate 주입
- Manim이 xelatex 호출 → **미설치로 크래시**

### 2) xeCJK.sty 미설치

| 증상 | 원인 |
|------|------|
| `! LaTeX Error: File 'xeCJK.sty' not found.` | `texlive-xetex`는 설치했지만 한글 CJK 패키지(`texlive-lang-korean`)가 빠짐 |

xelatex를 설치한 후 재시도했으나, xeCJK LaTeX 패키지가 없어서 동일하게 실패.

### 3) 에러 디테일 유실

| 증상 | 원인 |
|------|------|
| 로그에 `"Error: manim render failed"`만 출력, 실제 stderr 미표시 | `__main__.py:115`에서 `print(f"Error: {exc}")` — `RenderError.detail` 속성 무시 |

`RenderError`는 `detail` 필드에 manim stderr를 저장하지만, `str(exc)`는 메시지만 반환. CLI의 `except Exception` 핸들러가 detail을 버림.

---

## why: 왜 이런 일이 벌어졌는가?

1. **폴백 템플릿의 CJK 주입이 환경 의존적** — `inject_cjk_if_needed()`는 한글이 있으면 무조건 xelatex를 주입하지만, xelatex + xeCJK 설치 여부를 검증하지 않음
2. **`MathTex('수식', ...)` 같은 의미없는 한글 플레이스홀더** — 폴백 템플릿이 실제 수식 대신 한글 텍스트를 MathTex에 넣어서 불필요한 CJK 의존성 발생
3. **에러 핸들링에서 detail 유실** — `PipelineError.detail`이 `str()`에 포함되지 않아 근본 원인 파악이 어려움
4. **세그먼트 0~1은 `Text()` 사용** — `Text()`는 Pango 렌더러 사용하므로 CJK 템플릿 주입과 무관하게 동작. 세그먼트 2는 순수 수식(`MathTex`에 한글 없음)이라 CJK 미주입. **세그먼트 3만 MathTex+한글 조합**이라 크래시.

---

## fix: 어떻게 해결했는가?

### 즉시 해결
```bash
sudo apt install texlive-xetex texlive-lang-korean
```

### 근본 해결 (권장)
1. **폴백 템플릿의 `MathTex('수식', ...)` 수정** — 한글 플레이스홀더 대신 순수 수식 사용 (예: `MathTex('f(x)', ...)`)
2. **에러 로그에 detail 표시** — `__main__.py`에서 `RenderError.detail` 출력 추가
3. **xelatex/CJK 가용성 사전 검증** — `inject_cjk_if_needed()`에서 xelatex + xeCJK 설치 여부 확인 후 미설치 시 폴백 로직 적용

---

## lessons: 무엇을 배웠는가?

1. **환경 의존성은 사전 검증해야 함** — 외부 바이너리(xelatex)나 LaTeX 패키지(xeCJK)를 사용하기 전에 설치 여부 확인 필요
2. **에러 메시지에 detail을 포함해야 함** — `"manim render failed"`만으로는 근본 원인 파악 불가. stderr/stdout을 로그에 포함
3. **Text vs MathTex의 렌더링 경로 차이** — `Text()`는 Pango, `MathTex()`는 LaTeX. CJK 템플릿은后者에만 영향. 이 차이를 이해하고 템플릿 설계해야 함
4. **폴백 템플릿도 테스트해야 함** — LLM 실패 시 사용되는 폴백 코드가 실제 환경에서 동작하는지 검증 필요

---

## references

- 관련 파일: `src/manim_video_gen/pipeline/short_orchestrator.py` (폴백 로직), `src/manim_video_gen/video/manim_renderer.py` (렌더링), `src/manim_video_gen/__main__.py` (에러 핸들링)
- 관련 파일: `src/manim_video_gen/video/templates/short/concept_templates.py` (템플릿 렌더러)
- 관련 파일: `src/manim_video_gen/llm/prompts/short_manim_gen.py` (폴백 매핑)
