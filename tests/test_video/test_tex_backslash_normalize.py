"""normalize_llm_manim_tex_backslashes — LLM 이스케이프 보정."""

import ast

from manim_video_gen.video.code_validator import normalize_llm_manim_tex_backslashes


def _extract_first_mathtex_value(code: str) -> str:
    """코드를 파싱하여 첫 번째 MathTex/Tex 호출의 문자열 인자 값을 반환한다."""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name in ("MathTex", "Tex") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
    raise ValueError("MathTex/Tex string not found")


def test_collapses_double_backslash_before_latex_commands() -> None:
    src = r"eq = MathTex(r'x = \\\\frac{-b \\\\pm \\\\sqrt{b^2 - 4ac}}{2a}', font_size=48)"
    out = normalize_llm_manim_tex_backslashes(src)
    val = _extract_first_mathtex_value(out)
    assert val == r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}"


def test_quad_spacing_command() -> None:
    src = r"eq = MathTex(r'a = 1, \\quad b = 3', font_size=48)"
    out = normalize_llm_manim_tex_backslashes(src)
    val = _extract_first_mathtex_value(out)
    assert val == r"a = 1, \quad b = 3"


def test_idempotent_on_correct_code() -> None:
    src = r"eq = MathTex(r'x = \frac{a}{b}', font_size=48)"
    assert normalize_llm_manim_tex_backslashes(src) == src


def test_iterates_multiple_layers() -> None:
    src = r"MathTex(r'\\\\frac{a}{b}')"
    out = normalize_llm_manim_tex_backslashes(src)
    val = _extract_first_mathtex_value(out)
    assert val == r"\frac{a}{b}"


def test_non_raw_string_not_corrupted() -> None:
    """repr()로 생성된 non-raw string의 올바른 이스케이프가 손상되지 않아야 한다.

    템플릿이 repr(latex)로 생성한 코드에서 Python 문자열 값이
    이미 올바른 단일 백슬래시이면 변경하지 않는다.
    """
    src = "eq = MathTex('a = 1, \\\\quad b = 3, \\\\quad c = 9', font_size=48)"
    out = normalize_llm_manim_tex_backslashes(src)
    assert out == src


def test_non_raw_string_with_excess_backslashes() -> None:
    """non-raw string에서 값 레벨 이중 백슬래시(\\\\frac)는 단일로 수정한다."""
    src = "MathTex('\\\\\\\\frac{a}{b}')"
    out = normalize_llm_manim_tex_backslashes(src)
    val = _extract_first_mathtex_value(out)
    assert val == r"\frac{a}{b}"


def test_syntax_error_returns_original() -> None:
    """파싱 불가능한 코드는 원본을 그대로 반환한다."""
    src = "MathTex(r'\\\\frac{a}{b}'"
    assert normalize_llm_manim_tex_backslashes(src) == src


def test_non_tex_strings_untouched() -> None:
    """MathTex/Tex가 아닌 호출의 문자열은 건드리지 않는다."""
    src = r"print('\\\\hello')"
    assert normalize_llm_manim_tex_backslashes(src) == src
