"""Validate Manim python source and optionally run a low-quality render."""

from __future__ import annotations

import ast
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from manim_video_gen.config import Settings

logger = logging.getLogger(__name__)

_DOUBLE_BACKSLASH_TEX_CMD = re.compile(r"\\\\([A-Za-z]+)")

_TEX_CONSTRUCTORS = frozenset({
    "MathTex", "Tex", "SingleStringMathTex", "TexMobject",
})

_TEX_TEXT_CMD = re.compile(
    r"\\(?:text|mathrm|textrm|textit|textbf|mbox)\{([^}]*)\}"
)


def sanitize_latex_for_compilation(latex: str) -> str:
    r"""LaTeX 문자열에서 기본 latex(pdfLaTeX)가 처리할 수 없는 비ASCII를 제거한다.

    ``\text{또는}`` 등 비ASCII가 들어간 ``\text``/``\mathrm``/… 인자는 ``\quad`` 로 바꾸고,
    그래도 남는 한글·기호(노출된 비ASCII)는 통째로 제거한다.
    """
    latex = _collapse_double_backslash_tex(latex)

    def _replace(m: re.Match[str]) -> str:
        content = m.group(1)
        if any(ord(c) > 127 for c in content):
            return r"\quad"
        return m.group(0)

    prev = None
    while prev != latex:
        prev = latex
        latex = _TEX_TEXT_CMD.sub(_replace, latex)

    return "".join(c for c in latex if ord(c) < 128)


def _collapse_double_backslash_tex(value: str) -> str:
    """문자열 *값* 안의 ``\\\\frac`` → ``\\frac`` 등 이중 백슬래시를 단일로 축소."""
    for _ in range(10):
        new_val = _DOUBLE_BACKSLASH_TEX_CMD.sub(r"\\\1", value)
        if new_val == value:
            return value
        value = new_val
    return value


def _fix_tex_string_value(value: str) -> str:
    """MathTex/Tex 문자열 값에 이중 백슬래시를 정규화한다."""
    return _collapse_double_backslash_tex(value)


def normalize_llm_manim_tex_backslashes(code: str) -> str:
    """MathTex/Tex 호출의 문자열 인자 *값*에서 이중 백슬래시를 정규화한다.

    AST 기반으로 동작하여 raw/non-raw string 구분 없이 안전하게 처리한다.
    변경이 필요 없으면 원본 코드를 그대로 반환하므로 포맷이 유지된다.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    modified = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name: str | None = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name not in _TEX_CONSTRUCTORS:
            continue

        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                new_val = _fix_tex_string_value(arg.value)
                if new_val != arg.value:
                    arg.value = new_val
                    modified = True

    if not modified:
        return code

    try:
        return ast.unparse(tree)
    except Exception:
        return code


def validate_python_syntax(code: str) -> tuple[bool, str]:
    try:
        compile(code, "<manim_segment>", "exec")
        return True, ""
    except SyntaxError as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


def run_manim_render(
    *,
    code: str,
    scene_path: Path,
    quality: str,
    timeout_seconds: float,
    media_dir: Path | None = None,
) -> tuple[bool, str]:
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(code, encoding="utf-8")
    cmd = [
        "manim",
        "render",
        f"-q{quality}",
        str(scene_path),
        "Segment",
    ]
    if media_dir is not None:
        media_dir.mkdir(parents=True, exist_ok=True)
        cmd.extend(["--media_dir", str(media_dir)])
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return False, "manim CLI not found on PATH"
    except subprocess.TimeoutExpired:
        return False, f"manim render timed out after {timeout_seconds}s"

    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-4000:]
        return False, tail

    return True, ""


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
    )
    return ok2, err2


def render_smoke_test(code: str, settings: Settings) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="manim_smoke_") as tmp:
        return validate_and_test_render(
            code=code,
            workspace=Path(tmp),
            settings=settings,
            stem="smoke",
        )
