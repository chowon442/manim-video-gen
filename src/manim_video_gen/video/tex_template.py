"""CJK (Korean) TeX template support for Manim scenes.

한국어가 포함된 LaTeX 문자열이 있으면, XeLaTeX + xeCJK를 사용하는
TeX 템플릿 설정 코드를 생성된 씬 파일에 주입한다.
"""

from __future__ import annotations

import os
import platform
import re

def _default_cjk_font() -> str:
    """OS별 기본 CJK 폰트를 반환한다. 환경변수로 오버라이드 가능."""
    if env_font := os.environ.get("MANIM_VIDEO_GEN_CJK_FONT", "").strip():
        return env_font
    system = platform.system()
    if system == "Windows":
        return "Malgun Gothic"   # 맑은 고딕 - Windows 기본 한글 폰트
    if system == "Darwin":
        return "AppleGothic"     # macOS 기본 한글 폰트
    return "Noto Sans CJK KR"   # Linux (Noto CJK 설치 필요)


CJK_FONT_DEFAULT: str = _default_cjk_font()

_NON_ASCII_RE = re.compile(r"[^\x00-\x7f]")

_CJK_SETUP_TEMPLATE = """\
from manim import TexTemplate as _TexTemplate, config as _manim_config
_cjk_tpl = _TexTemplate()
_cjk_tpl.tex_compiler = "xelatex"
_cjk_tpl.output_format = ".xdv"
_cjk_tpl.add_to_preamble(r"\\usepackage{{xeCJK}}")
_cjk_tpl.add_to_preamble(r"\\setCJKmainfont{{{font}}}")
_manim_config.tex_template = _cjk_tpl
"""


def has_cjk(text: str) -> bool:
    """문자열에 비ASCII(한국어 등) 문자가 포함되어 있는지 검사한다."""
    return bool(_NON_ASCII_RE.search(text))


def cjk_setup_code(font: str = CJK_FONT_DEFAULT) -> str:
    """씬 파일에 삽입할 CJK TeX 템플릿 설정 Python 코드를 반환한다."""
    return _CJK_SETUP_TEMPLATE.format(font=font)


def scene_imports(*latex_values: str, font: str = CJK_FONT_DEFAULT) -> str:
    """씬 파일의 import 블록을 생성한다. CJK 문자가 있으면 XeLaTeX 설정을 포함."""
    base = "from manim import *"
    if any(has_cjk(v) for v in latex_values):
        return base + "\n" + cjk_setup_code(font)
    return base


def inject_cjk_if_needed(code: str, font: str = CJK_FONT_DEFAULT) -> str:
    """생성된 씬 코드에 CJK 문자가 있으면, XeLaTeX 템플릿 설정을 주입한다.

    이미 CJK 설정이 있거나 비ASCII가 없으면 원본을 그대로 반환한다.
    """
    if not has_cjk(code):
        return code
    if "_cjk_tpl" in code:
        return code

    setup = cjk_setup_code(font)

    lines = code.split("\n")
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("from manim", "from manim import", "import manim")):
            insert_idx = i + 1

    lines.insert(insert_idx, setup)
    return "\n".join(lines)
