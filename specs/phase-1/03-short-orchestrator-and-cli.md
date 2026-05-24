# Short Orchestrator + CLI + Single/Series Pipeline

## Purpose
쇼츠 전체 파이프라인을 조율하는 `short_orchestrator.py`와 CLI `short` subcommand, single/series 모드, dry-run/plan.json 지원을 구현한다.

## Requirements
- `pipeline/short_orchestrator.py` — Extract→StoryScriptify→TTS→Manim render→Compose 파이프라인 조율. long-form `orchestrator.py`의 TTS/Manim/composer만 공유하고, 쇼츠 전용 `_build_short_manim_code_for_segment` 로직 사용. plan.json 캐시로 재렌더 시 Extract/StoryScriptify 생략 가능
- CLI `short` subcommand — `python -m manim_video_gen short -f doc.md --mode single --topic "p-value"` 형식. `--mode single`(기본 #1 또는 `--topic` fuzzy match) / `--mode series`(topological sort + `--max-shorts` cap) / `--dry-run`(Extract까지만) / `--plan-only`(plan.json만 생성) / `--from-plan plan.json --unit N`(특정 unit 재렌더)
- single 모드 — Extract 실행 후 plan.json 저장, topic match 또는 기본 #1 unit 선택, StoryScriptify→TTS→Manim→Compose E2E. 출력: `artifacts/short_<id>/final.mp4` + metadata(hashtags 3~5, 1줄 description)
- series 모드 — topological sort 기반 순서 결정, `--max-shorts` cap 적용. 출력: `artifacts/series_<run_id>/short_01.mp4 ... short_N.mp4` + `series_metadata.json`
- short_quality 가드 — ApplicationStory 5필드 non-empty, Concept segment 앞 Problem 존재, Payoff에 application_result 포함, hook이 개념명 아닌 시나리오/질문으로 시작 검사

## Approach
기존 `orchestrator.py`의 `_build_manim_code_for_segment` 패턴(Registry → LLM → fallback)을 미러하되, ShortTemplateRegistry와 short_manim_gen으로 교체한다. TTS factory, OpenRouter client, composer, diagnostics는 그대로 재사용하고, CLI는 `__main__.py`에 subparser를 추가하여 기존 long-form 경로를 건드리지 않는다. series 모드의 topological sort는 `graphlib.TopologicalSorter`를 사용하고, cycle 감지 시 LLM 순서 fallback을 적용한다.

## Verification
- `python -m manim_video_gen short -f problem2.md --mode single`로 15~60초 9:16 영상 생성
- `--dry-run` 실행 시 Extract까지만 진행, plan.json 파일 생성 확인
- `--mode series --max-shorts 3` 실행 시 3개 영상 + series_metadata.json 생성
- `--from-plan plan.json --unit 2`로 특정 unit만 재렌더 (Extract/StoryScriptify 생략)
- short_quality 가드 실패 시 적절한 에러 메시지 출력
