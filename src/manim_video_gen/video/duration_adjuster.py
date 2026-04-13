"""Adjust Manim scene duration by appending self.wait(...) at end of construct()."""

from __future__ import annotations

import ast
import logging
import re

logger = logging.getLogger(__name__)


def _as_float(node: ast.expr | None) -> float | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    return None


def estimate_construct_duration_seconds(code: str) -> float:
    """Best-effort estimate from self.play(run_time=...) and self.wait(...)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0.0

    total = 0.0

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            nonlocal total
            if isinstance(node.func, ast.Attribute) and isinstance(
                node.func.value, ast.Name
            ):
                if node.func.value.id == "self":
                    if node.func.attr == "wait":
                        v = _as_float(node.args[0]) if node.args else None
                        if v is not None:
                            total += v
                    elif node.func.attr == "play":
                        rt = 1.0
                        for kw in node.keywords:
                            if kw.arg == "run_time":
                                v = _as_float(kw.value)
                                if v is not None:
                                    rt = v
                        total += rt
            self.generic_visit(node)

    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            for item in n.body:
                if isinstance(item, ast.FunctionDef) and item.name == "construct":
                    V().visit(item)

    return total


def adjust_duration(code: str, target_duration: float) -> str:
    """Append a final self.wait(...) inside construct() if estimated time is short."""
    estimated = estimate_construct_duration_seconds(code)
    diff = float(target_duration) - float(estimated)
    # Templates already end with self.wait; avoid appending a second padding wait.
    if diff <= 0.15:
        if diff < -0.5:
            logger.warning(
                "Estimated animation time %.3fs exceeds target %.3fs by %.3fs",
                estimated,
                target_duration,
                -diff,
            )
        return code

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    construct_fn: ast.FunctionDef | None = None
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and n.name == "Segment":
            for item in n.body:
                if isinstance(item, ast.FunctionDef) and item.name == "construct":
                    construct_fn = item
                    break
    if construct_fn is None:
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                for item in n.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "construct":
                        construct_fn = item
                        break

    if construct_fn is None:
        logger.warning("Could not find construct() to adjust duration")
        return code

    wait_call = ast.Expr(
        value=ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="self", ctx=ast.Load()),
                attr="wait",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=round(diff, 3))],
            keywords=[],
        )
    )
    construct_fn.body.append(wait_call)
    return ast.unparse(tree)  # type: ignore[attr-defined]


def adjust_duration_safe(code: str, target_duration: float) -> str:
    """Like adjust_duration but falls back to original code if unparsing fails."""
    try:
        return adjust_duration(code, target_duration)
    except Exception as exc:  # noqa: BLE001
        logger.warning("duration adjust failed: %s", exc)
        return code


def ensure_scene_cleanup(code: str, *, enabled: bool = True) -> str:
    """Ensure Segment.construct ends with cleanup (FadeOut + clear).

    This prevents lingering mobjects when rendered clips are stitched.
    If cleanup already exists, the code is returned unchanged.
    """
    if not enabled:
        return code

    has_clear = "self.clear()" in code
    has_fadeout = bool(
        re.search(
            r"FadeOut\(m\)\s+for\s+m\s+in\s+(?:self\.mobjects|list\(self\.mobjects\))",
            code,
        )
    )
    if has_clear and has_fadeout:
        return code

    marker = "def construct(self):"
    idx = code.find(marker)
    if idx < 0:
        return code

    # Find block indentation from next non-empty line
    rest = code[idx + len(marker) :]
    lines = rest.splitlines(keepends=True)
    indent = "        "
    for ln in lines:
        if ln.strip():
            leading = ln[: len(ln) - len(ln.lstrip(" "))]
            if leading:
                indent = leading
            break

    cleanup_parts: list[str] = []
    if not has_fadeout:
        cleanup_parts.append(
            f"{indent}if len(self.mobjects) > 0:\n"
            f"{indent}    self.play(*[FadeOut(m) for m in list(self.mobjects)], run_time=0.25)\n"
        )
    if not has_clear:
        cleanup_parts.append(f"{indent}self.clear()\n")

    if not cleanup_parts:
        return code

    cleanup = "".join(cleanup_parts)

    # Append cleanup at file end (safe for current generated templates where construct is final block)
    if code.endswith("\n"):
        return code + cleanup
    return code + "\n" + cleanup
