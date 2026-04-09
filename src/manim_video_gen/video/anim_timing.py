"""Animation duration caps: front-load motion, remainder is self.wait for TTS."""

from __future__ import annotations

# Maximum run_time for common plays (seconds)
ANIM_CAP_WRITE = 1.2
ANIM_CAP_TRANSFORM = 1.8
ANIM_CAP_CREATE = 0.5
ANIM_CAP_FADE = 0.4
ANIM_GAP = 0.25

ANIM_MIN_WRITE = 0.35
ANIM_MIN_TRANSFORM = 0.4


def split_write(duration: float) -> tuple[float, float]:
    """Single Write(...) then wait; caps long TTS so the equation appears quickly."""
    d = float(duration)
    t = min(ANIM_CAP_WRITE, max(ANIM_MIN_WRITE, d * 0.35))
    w = max(0.12, d - t)
    return t, w


def split_transform(duration: float) -> tuple[float, float]:
    """TransformMatchingTex / ReplacementTransform then wait."""
    d = float(duration)
    t = min(ANIM_CAP_TRANSFORM, max(ANIM_MIN_TRANSFORM, d * 0.35))
    w = max(0.12, d - t)
    return t, w


def split_transform_no_prev(duration: float) -> tuple[float, float, float, float]:
    """Write(from) + brief pause + TransformMatchingTex(to) + wait."""
    d = float(duration)
    t_intro = min(ANIM_CAP_WRITE, max(0.22, d * 0.14))
    t_mid = min(ANIM_GAP + 0.1, max(0.12, d * 0.08))
    t_tx = min(ANIM_CAP_TRANSFORM, max(0.35, d * 0.22))
    used = t_intro + t_mid + t_tx
    t_end = max(0.12, d - used)
    return t_intro, t_mid, t_tx, t_end


def split_n_writes(
    duration: float,
    n: int,
    *,
    fade_in: float = 0.0,
) -> tuple[float, float]:
    """Sequential Write for n mobjects; capped per line; returns (t_each, t_wait)."""
    d = float(duration)
    k = max(int(n), 1)
    budget = max(0.01, d - float(fade_in))
    t_each = min(
        ANIM_CAP_WRITE,
        max(0.22, budget / max(k + 0.5, 1.0)),
    )
    anim = float(fade_in) + t_each * k
    t_wait = max(0.12, d - anim)
    return t_each, t_wait


def split_create(duration: float, *, frac: float = 0.22) -> tuple[float, float]:
    """Create(...) e.g. SurroundingRectangle; capped."""
    d = float(duration)
    t = min(ANIM_CAP_CREATE, max(0.2, d * frac))
    w = max(0.12, d - t)
    return t, w


def split_axes_and_plot(
    duration: float,
    *,
    has_label_line: bool,
    fade_out: float,
) -> tuple[float, float, float]:
    """Axes create, graph create, final wait (before optional FadeOut)."""
    d = float(duration)
    label_cost = 0.4 if has_label_line else 0.0
    avail = max(0.15, d - fade_out - label_cost)
    t_axes = min(ANIM_CAP_CREATE, max(0.28, avail * 0.28))
    t_plot = min(ANIM_CAP_TRANSFORM, max(0.45, avail * 0.45))
    t_end = max(0.12, avail - t_axes - t_plot)
    return t_axes, t_plot, t_end


def split_highlight_box(
    duration: float,
) -> tuple[float, float, float, float]:
    """Write eq, Create box, hold, FadeOut box."""
    d = float(duration)
    t_in = min(ANIM_CAP_WRITE, max(0.3, d * 0.22))
    t_box = min(ANIM_CAP_CREATE, max(0.22, d * 0.18))
    t_hold = max(0.15, d * 0.35)
    t_out = max(0.1, d - t_in - t_box - t_hold)
    t_out = min(t_out, ANIM_CAP_FADE)
    return t_in, t_box, t_hold, t_out
