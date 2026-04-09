# 002 — Manim LaTeX 백슬래시 손상 & 한국어 렌더링

## Context

수학 문제를 입력하면 Manim + TTS로 풀이 영상을 자동 생성하는 파이프라인(`manim-video-gen`)을 실행하는 중, `MathTex` LaTeX 컴파일 단계에서 연쇄적으로 에러가 발생했다.

파이프라인 흐름: LLM(풀이) → LLM(스크립트) → TTS(음성) → Template/LLM(Manim 씬 코드 생성) → Manim 렌더링 → FFmpeg 합성

---

## Roadblocks

### 1. `SyntaxWarning: invalid escape sequence '\q'` + LaTeX 컴파일 실패

**증상:** 생성된 씬 파일 `scene_00.py`에서 `MathTex('a = 1, \quad b = 3, \quad c = 9')` 코드가 Python 3.13 `SyntaxWarning`을 발생시키고, LaTeX 컴파일도 실패.

**원인:** `normalize_llm_manim_tex_backslashes()` 함수가 **코드 텍스트 전체**에 정규식 `\\\\([A-Za-z]+)`를 적용. 이 함수는 LLM이 `\\\\frac` 같은 과도한 이스케이프를 넣을 때 `\\frac`으로 줄이기 위한 것이었으나, 템플릿이 `repr()`로 올바르게 생성한 `'\\quad'`(Python에서 `\quad` 값)까지 `'\quad'`(잘못된 이스케이프)로 변환해버렸다.

```
템플릿 repr() 생성    →  '\\quad'  (정상: Python 값 = \quad)
normalize 정규식 적용  →  '\quad'   (손상: \q는 무효 이스케이프)
```

핵심 문제: 정규식이 raw string `r'\\frac'`과 non-raw string `'\\frac'`을 구분하지 못함. 둘 다 코드 텍스트에서 `\\frac`으로 보이지만, 의미가 다르다.

### 2. `LaTeX Error: File 'standalone.cls' not found`

**증상:** 백슬래시 문제 해결 후에도 LaTeX 컴파일 실패.

**원인:** macOS에 TeX Live **basic** 설치만 되어 있어서, Manim의 기본 TeX 템플릿이 요구하는 `standalone`, `preview` 등 패키지가 누락.

### 3. `\text{또는}` LaTeX 컴파일 실패

**증상:** 5개 세그먼트 중 4개는 성공, 마지막 세그먼트에서 실패. `\text{또는}` 같은 한국어 텍스트가 MathTex에 포함됨.

**원인:** 기본 `latex` 컴파일러(DVI 출력)는 CJK 문자를 처리할 수 없다. LLM이 풀이 결과에 `\text{또는}` 같은 한국어 레이블을 생성했는데, 이를 처리할 방법이 없었다.

---

## The Fix

### 1단계: AST 기반 백슬래시 정규화 (코드 텍스트 → 문자열 값)

정규식을 코드 전체에 적용하는 대신, **AST로 파싱하여 MathTex/Tex 호출의 문자열 인자 값**에서만 이중 백슬래시를 정규화하도록 재작성.

```python
# Before: 코드 텍스트 전체에 정규식 (raw/non-raw 구분 불가)
_LLM_DOUBLE_BACKSLASH_CMD.sub(r"\\\1", code)

# After: AST로 문자열 값만 추출하여 처리
for node in ast.walk(tree):
    if isinstance(node, ast.Call) and func_name in _TEX_CONSTRUCTORS:
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                arg.value = _collapse_double_backslash_tex(arg.value)
```

이 방식은 raw string이든 non-raw string이든 **Python이 해석한 실제 문자열 값**에서 동작하므로 안전하다.

### 2단계: TeX Live 패키지 설치

```bash
sudo tlmgr update --self
sudo tlmgr install standalone preview dvisvgm doublestroke setspace rsfs wasysym physics xcolor cancel mathabx fontaxes enumitem tcolorbox environ trimspaces xecjk
```

### 3단계: XeLaTeX + xeCJK로 한국어 렌더링 지원

한국어를 제거하는 대신, XeLaTeX + xeCJK를 사용하는 TeX 템플릿을 자동 주입하는 방식으로 전환.

`tex_template.py` 모듈을 생성하여:
- `has_cjk(text)` — LaTeX 문자열에 비ASCII 문자 감지
- `scene_imports(*latex_values)` — CJK 감지 시 XeLaTeX 설정 코드를 import 블록에 포함
- `inject_cjk_if_needed(code)` — LLM 생성 코드에 CJK 템플릿 자동 주입

```python
# 한국어가 감지되면 씬 파일에 자동 주입되는 코드:
from manim import TexTemplate, config
_cjk_tpl = TexTemplate()
_cjk_tpl.tex_compiler = "xelatex"
_cjk_tpl.output_format = ".xdv"
_cjk_tpl.add_to_preamble(r"\usepackage{xeCJK}")
_cjk_tpl.add_to_preamble(r"\setCJKmainfont{AppleGothic}")
config.tex_template = _cjk_tpl
```

순수 ASCII 수식만 있는 세그먼트는 기본 `latex` 컴파일러를 사용하여 속도를 유지한다.

---

## Learning

### Python 문자열 이스케이프 vs 코드 텍스트

- `'\\quad'`(non-raw) = 문자열 값 `\quad` (올바름)
- `r'\\quad'`(raw) = 문자열 값 `\\quad` (이중 백슬래시, LLM이 자주 생성)
- **코드 텍스트에서 둘 다 `\\quad`로 보이지만 의미가 다르다.**
- 생성된 Python 코드를 텍스트 정규식으로 수정하면 이런 구분이 불가능 → **AST 기반 처리가 안전.**

### Python 3.12+ 이스케이프 시퀀스 변경

- Python 3.12: 미인식 이스케이프(`\q` 등) → `DeprecationWarning`
- Python 3.13: → `SyntaxWarning`
- Python 3.14(예정): → `SyntaxError`

코드 생성기에서 LaTeX 백슬래시 명령어를 다룰 때 반드시 raw string(`r'...'`) 또는 올바르게 이스케이프된 non-raw string(`'\\...'`)을 사용해야 한다.

### TeX Live basic 설치의 한계

macOS `brew install --cask basictex`나 TeX Live basic 설치는 최소한의 패키지만 포함. Manim은 `standalone`, `preview`, `dvisvgm` 등 여러 패키지를 요구하므로 추가 설치가 필수.

### Manim에서 한국어(CJK) 렌더링

- 기본 `latex` 컴파일러 → CJK 불가
- `xelatex` + `xeCJK` 패키지 + 시스템 폰트(`AppleGothic` 등) → CJK 가능
- `config.tex_template`을 설정하면 해당 씬의 모든 MathTex에 전역 적용
- `Text` 클래스(Pango 기반)는 LaTeX 없이 한국어 지원하지만, 수식과 혼용이 어려움

### `ast.unparse()` 동작

- `ast.unparse()`는 항상 non-raw string을 생성 (`r'...'` → `'...'`)
- 수정이 없으면(`modified = False`) 원본 코드를 그대로 반환하여 포맷 유지
- 수정이 있으면 코드 포맷이 바뀔 수 있으나, 실행에는 영향 없음
