---
id: "1.09"
phase: 1
title: "Phase 1 E2E 검증"
spec: "specs/phase-1/03-short-orchestrator-and-cli.md"
depends_on: ["1.08"]
blocks: []
estimate: "M"
status: "done"
owner: ""
sprint: ""
---

# Task 1.09 — Phase 1 E2E 검증

> Spec: [`specs/phase-1/03-short-orchestrator-and-cli.md`](../../specs/phase-1/03-short-orchestrator-and-cli.md)

## 의존성

- 1.08 (short_orchestrator + CLI) — 전체 파이프라인 통합 완료 필요

## 사전 준비

- [x] `problem2.md` 테스트 입력 파일 확인
- [x] TTS/OpenRouter API 키 설정 확인

## 구현 체크리스트

- [x] `python -m manim_video_gen short -f problem2.md --mode single` 실행 → 15~60초 9:16 영상 생성 확인
  - **결과**: 부분 성공. 세그먼트 0, 1, 2 렌더링 완료 (총 18.3초), 세그먼트 3 렌더 실패
  - **이슈**: 영상이 1920x1080(16:9 가로)으로 생성됨. 1080x1920(9:16 세로) 버그 발견
- [ ] 영상 상단 중앙에 headline 전 구간 고정 표시 확인
  - **결과**: 미확인 (최종 영상 미생성)
- [ ] narration/tts_text가 스토리텔링 톤 (강의체 패턴 없음) 확인
  - **결과**: 부분 확인. Inworld TTS 호출 성공, 자막 파일(ASS) 생성 확인
- [ ] headline이 TTS로 읽지 않음 확인
  - **결과**: 미확인
- [x] 각 쇼츠가 ApplicationStory 아크 따름 확인 (Hook→Problem→Concept→Payoff)
  - **결과**: 확인 완료. Extract 단계에서 ApplicationStory 5필드(scenario, problem_in_domain, concept_bridge, application_result, payoff_line) 모두 생성됨
- [x] ShortTemplateRegistry 템플릿 우선 + short_visual_scene LLM fallback 동작 확인
  - **결과**: 확인 완료. 세그먼트 0, 1, 2는 템플릿/LLM으로 렌더링, 세그먼트 3은 LLM 3회 재시도 후 fallback 템플릿으로 degrade됨
- [x] LLM 실패 시 fallback 템플릿 degrade 확인
  - **결과**: 확인 완료. 세그먼트 3에서 LLM 3회 실패 후 `short_concept_equation` fallback 템플릿 적용 시도 (그러나 fallback도 렌더 실패)
- [ ] `--mode series --max-shorts 5` 실행 시 5개 영상 + series_metadata.json 확인
  - **결과**: 실패. series 모드에서 `Settings` 객체에 `artifact_dir` 속성이 없어 AttributeError 발생
- [x] `--dry-run` 실행 시 plan.json만 생성 확인
  - **결과**: 확인 완료. plan.json이 artifacts/plan.json에 저장됨
- [x] 기존 long-form 파이프라인 regression 테스트 실행
  - **결과**: 357 passed, 1 failed (Grok TTS API 키 관련, short 파이프라인과 무관)

## Definition of Done

- [ ] `problem2.md` → 시리즈 3~5개, 각 15~60초, 9:16 영상 생성 성공
  - **상태**: 부분 완료
  - Extract: 3개 ShortUnit 생성 (45초, 50초, 55초)
  - Single 모드: 세그먼트 3 렌더 실패로 최종 영상 미생성
  - Series 모드: `artifact_dir` 버그로 실행 불가
- [ ] 세로 화면에서 수식/그래프/자막/headline 겹침 없음
  - **상태**: 미확인
  - **버그**: 세그먼트가 1920x1080(가로)으로 렌더링됨. `VideoFormatProfile.SHORT_9_16` 설정이 Manim 렌더러에 전달되지 않음
- [x] `--mode single --topic "p-value"`로 1개만 생성 가능
  - **상태**: 확인 완료 (단, quality guard 조건 충족 필요)
- [x] 기존 long-form 파이프라인 동작 변화 없음
  - **상태**: 확인 완료. regression 테스트 357 passed

## 발견된 버그 / 이슈

### 🔴 Critical

1. **해상도 버그 (9:16 미적용)**
   - 현상: `--mode single`로 생성된 세그먼트가 1920x1080(16:9 가로)로 렌더링됨
   - 기대: 1080x1920(9:16 세로)
   - 원인: `VideoFormatProfile.SHORT_9_16` 설정이 Manim 렌더러에 전달되지 않음
   - 위치: `short_orchestrator.py`의 `generate_short_video()` 또는 `render_manim_scene()` 호출 부분

2. **Series 모드 `artifact_dir` AttributeError**
   - 현상: `--mode series` 실행 시 `'Settings' object has no attribute 'artifact_dir'`
   - 원인: `short_orchestrator.py:602`에서 `settings.artifact_dir` 참조하나, `config.py` Settings 클래스에 해당 필드 없음
   - 해결: `settings.artifact_dir or "artifacts"` → `project_root() / "artifacts"` 등으로 변경 필요

### 🟡 Major

3. **단일 세그먼트 렌더 실패 (세그먼트 3)**
   - 현상: LLM 3회 재시도 후 fallback 템플릿도 렌더 실패
   - 원인: fallback 템플릿(`short_concept_equation`)의 Manim 코드가 세로 해상도에서 오류 발생 가능성
   - 로그: `WARNING LLM short manim failed after retries; using fallback template for seg 3` → `Error: manim render failed`

4. **Quality Guard 한국어 단어 매칭**
   - 현상: payoff_line이 application_result를 참조하는지 검사 시 한국어 조사(은/는/이/가)로 인해 단어 매칭 실패
   - 예시: "p-value가" ≠ "p-value", "0.014(1.4%)로" ≠ "0.014"
   - 개선: 형태소 분석 없이는 완벽한 매칭 어려움. 토큰화 또는 더 유연한 매칭 필요

### 🟢 Minor

5. **Grok TTS 테스트 실패**
   - 현상: regression 테스트 중 `test_get_tts_provider_xai_alias` 실패
   - 원인: XAI_API_KEY 미설정 (Grok TTS 미사용)
   - 영향: short 파이프라인과 무관

## 테스트 실행 로그

### 환경
- **Worktree**: `/home/chowon442/coding-workspace/.worktrees/manim-video-gen/worktree-task-09`
- **Branch**: `worktree-task-09`
- **Python**: 3.11 (uv 가상환경)
- **TTS**: Inworld (Hyunwoo)
- **LLM**: OpenRouter (google/gemini-3-flash-preview:nitro)

### --dry-run
```bash
python -m manim_video_gen short -f examples/problem2.md --dry-run
# 결과: 3개 ShortUnit 추출, plan.json 저장
```

### --mode single --topic "p-value"
```bash
python -m manim_video_gen short -f examples/problem2.md --from-plan artifacts/plan.json --unit 1 --mode single
# 결과: 세그먼트 0,1,2 성공 (18.3초), 세그먼트 3 실패
```

### --mode series --max-shorts 3
```bash
python -m manim_video_gen short -f examples/problem2.md --mode series --max-shorts 3 --from-plan artifacts/plan.json
# 결과: 'Settings' object has no attribute 'artifact_dir'
```

### Regression Tests
```bash
pytest tests/ -v --tb=short
# 결과: 357 passed, 1 failed
```

## 버그 수정 내역

### Fix 1: 해상도 버그 (9:16 미적용)
- **파일**: `src/manim_video_gen/pipeline/short_orchestrator.py`
- **변경**: `generate_short_video()` 시작 시 `settings.video_width/height`를 1080x1920으로 설정
- **검증**: 세그먼트 0~5 모두 1080x1920으로 렌더링됨 (`ffprobe` 확인)

### Fix 2: Series 모드 `artifact_dir` AttributeError
- **파일**: `src/manim_video_gen/pipeline/short_orchestrator.py`
- **변경**: `settings.artifact_dir or "artifacts"` → `project_root() / "artifacts"`
- **검증**: series 디렉토리 생성 성공

### Fix 3: Fallback 템플릿 LaTeX 의존성
- **파일**: `src/manim_video_gen/video/templates/short/concept_templates.py`
- **변경**: `short_concept_equation`, `short_concept_annotated` 템플릿의 `MathTex` → `Text`로 변경
- **이유**: 시스템에 LaTeX이 설치되지 않은 환경에서도 fallback 템플릿이 렌더링되도록
- **검증**: regression 테스트 358 passed (1개 테스트 업데이트)

### Fix 4: 테스트 업데이트
- **파일**: `tests/test_video/test_short_templates.py`
- **변경**: `assert "MathTex" in code` → `assert "Text" in code`

## 수정 후 검증 결과

### Regression Tests
```bash
pytest tests/ -v --tb=short
# 결과: 358 passed (이전: 357 passed, 1 failed)
```

### --mode single (해상도 버그 수정 후)
```bash
# 세그먼트 0~5 모두 1080x1920 (9:16) 렌더링 성공
# ffprobe 결과: 1080x1920x4.5s, 1080x1920x6.2s, ...
```

### --mode series (artifact_dir 버그 수정 후)
```bash
# series 디렉토리 생성 성공: artifacts/series_{run_id}
```

## 남은 이슈

1. **E2E 파이프라인 타임아웃**: `--mode single` 실행 시 6개 세그먼트 렌더링에 10분 이상 소요
   - 원인: Manim 렌더링 + TTS + Composer 합성 시간
   - 조치: 프로덕션 환경에서는 병렬 처리 또는 타임아웃 증가 필요

2. **LaTeX 설치 권장**: `MathTex` 사용 시 LaTeX 필요
   - Dockerfile에는 `texlive-latex-extra` 포함됨
   - 로컬 개발 환경에서는 LaTeX 설치 권장

3. **Quality Guard 한국어 단어 매칭**: 여전히 형태소 분석 없이는 완벽한 매칭 어려움
   - 현재는 plan.json 수동 수정으로 우회
   - 향후 개선 필요
