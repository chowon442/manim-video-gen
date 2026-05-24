"""Domain-specific templates for short-form content."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import Segment

FRAME_HEIGHT = 19.20
FRAME_WIDTH = 10.80

_VALID_COLORS = frozenset({
    "WHITE", "BLACK", "GRAY", "LIGHT_GRAY", "DARK_GRAY",
    "RED", "GREEN", "BLUE", "YELLOW", "ORANGE", "PURPLE",
    "TEAL", "PINK", "GOLD", "MAROON",
})

def _safe_color(name: str, default: str = "WHITE") -> str:
    u = str(name).strip().upper()
    return u if u in _VALID_COLORS else default


def _render_short_domain_icon(segment: Segment, duration: float) -> str:
    """Display an icon-like shape with label."""
    label = repr(str(segment.visual_params.get("label", "")))
    shape = str(segment.visual_params.get("shape", "circle"))
    
    t_draw = min(duration * 0.6, 1.5)
    t_wait = max(duration - t_draw, 0.5)
    
    shape_code = {
        "circle": "Circle(radius=1, color=BLUE)",
        "square": "Square(side_length=2, color=GREEN)",
        "triangle": "Triangle().scale(1.5)",
    }.get(shape, "Circle(radius=1, color=BLUE)")
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        icon = {shape_code}
        lbl = Text({label}, font_size=36).next_to(icon, DOWN)
        
        self.play(Create(icon), run_time={t_draw:.3f})
        self.play(Write(lbl), run_time=0.5)
        self.wait({t_wait:.3f})
"""


def _render_short_stat_chart(segment: Segment, duration: float) -> str:
    """Display a simple bar chart."""
    values = segment.visual_params.get("values", [10, 20, 30])
    labels = segment.visual_params.get("labels", ["A", "B", "C"])
    
    if not isinstance(values, list):
        values = [10, 20, 30]
    if not isinstance(labels, list):
        labels = ["A", "B", "C"]
    
    t_draw = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_draw, 0.5)
    
    values_str = ", ".join(str(v) for v in values[:6])
    labels_str = ", ".join(repr(str(l)) for l in labels[:6])
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        values = [{values_str}]
        labels = [{labels_str}]
        
        bars = VGroup()
        max_val = max(values) if values else 1
        bar_width = 0.8
        
        for i, (val, lbl) in enumerate(zip(values, labels)):
            bar = Rectangle(
                width=bar_width,
                height=val / max_val * 4,
                fill_opacity=0.8,
                color=BLUE,
            )
            bar.move_to(LEFT * 2 + RIGHT * i * 1.2 + UP * val / max_val * 2)
            bars.add(bar)
        
        bars.move_to(ORIGIN)
        
        self.play(Create(bars), run_time={t_draw:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_flow_arrow(segment: Segment, duration: float) -> str:
    """Show a flow with arrows."""
    steps = segment.visual_params.get("steps", ["시작", "끝"])
    
    if not isinstance(steps, list):
        steps = ["시작", "끝"]
    
    t_draw = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_draw, 0.5)
    
    steps_str = ", ".join(repr(str(s)) for s in steps[:4])
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        steps = [{steps_str}]
        
        boxes = VGroup()
        arrows = VGroup()
        
        for i, step in enumerate(steps):
            box = SurroundingRectangle(
                Text(step, font_size=32),
                buff=0.3,
                color=BLUE,
            )
            boxes.add(box)
            
            if i > 0:
                arrow = Arrow(
                    boxes[i-1].get_right(),
                    box.get_left(),
                    buff=0.1,
                )
                arrows.add(arrow)
        
        flow = VGroup(boxes, arrows).arrange(RIGHT, buff=0.5)
        flow.move_to(ORIGIN)
        
        self.play(Create(flow), run_time={t_draw:.3f})
        self.wait({t_wait:.3f})
"""


DOMAIN_RENDERERS = {
    "short_domain_icon": _render_short_domain_icon,
    "short_stat_chart": _render_short_stat_chart,
    "short_flow_arrow": _render_short_flow_arrow,
}
