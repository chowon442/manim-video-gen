"""Layout helpers for 9:16 short-form templates.

Provides safe zone constants and scaling utilities to prevent content
from being clipped in 1080×1920 portrait frames.
"""

from __future__ import annotations

# 9:16 frame dimensions in Manim units
# 1920px height → 19.20 units, 1080px width → 10.80 units
FRAME_HEIGHT = 19.20
FRAME_WIDTH = 10.80

# Safe zone ratios (percentage of frame height)
HEADLINE_ZONE_RATIO = 0.12   # top 12% reserved for headline
SUBTITLE_ZONE_RATIO = 0.20   # bottom 20% reserved for subtitle

# Derived safe zone boundaries in Manim units
HEADLINE_ZONE_TOP = FRAME_HEIGHT / 2  # +9.60
HEADLINE_ZONE_BOTTOM = FRAME_HEIGHT / 2 * (1 - HEADLINE_ZONE_RATIO)  # +8.448
CONTENT_ZONE_TOP = HEADLINE_ZONE_BOTTOM   # +8.448
CONTENT_ZONE_BOTTOM = -FRAME_HEIGHT / 2 * (1 - SUBTITLE_ZONE_RATIO)  # -7.68
CONTENT_CENTER_Y = (CONTENT_ZONE_TOP + CONTENT_ZONE_BOTTOM) / 2  # ~+0.384


def safe_zone_y_offset(has_headline: bool = False, has_subtitle: bool = True) -> float:
    """Return Y offset to center content in the safe zone.

    Args:
        has_headline: If True, avoid the top headline zone.
        has_subtitle: If True, avoid the bottom subtitle zone.

    Returns:
        Y coordinate for move_to() to place content in the safe center.
    """
    top = FRAME_HEIGHT / 2
    bottom = -FRAME_HEIGHT / 2

    if has_headline:
        top = CONTENT_ZONE_TOP
    if has_subtitle:
        bottom = CONTENT_ZONE_BOTTOM

    return (top + bottom) / 2


def scale_to_fit_frame(name: str, *, margin: float = 0.6, indent: int = 8) -> str:
    """Return code snippet that scales a mobject to fit within frame width.

    Args:
        name: Variable name of the mobject.
        margin: Horizontal margin on each side (default 0.6 = 0.6 units per side).
        indent: Number of spaces for indentation (default 8 for class method body).

    Returns:
        Python code string for conditional scaling, properly indented.
    """
    max_width = FRAME_WIDTH - 2 * margin
    pad = " " * indent
    return (
        f"{pad}if {name}.width > {max_width}:\n"
        f"{pad}    {name}.scale_to_fit_width({max_width})\n"
    )


def scale_to_fit_height(name: str, *, margin: float = 1.0, indent: int = 8) -> str:
    """Return code snippet that scales a mobject to fit within content zone height.

    Args:
        name: Variable name of the mobject.
        margin: Vertical margin (default 1.0 units per side).
        indent: Number of spaces for indentation (default 8 for class method body).

    Returns:
        Python code string for conditional scaling, properly indented.
    """
    max_height = (CONTENT_ZONE_TOP - CONTENT_ZONE_BOTTOM) - 2 * margin
    pad = " " * indent
    return (
        f"{pad}if {name}.height > {max_height}:\n"
        f"{pad}    {name}.scale_to_fit_height({max_height})\n"
    )
