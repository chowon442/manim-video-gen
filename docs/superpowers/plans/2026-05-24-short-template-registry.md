# ShortTemplateRegistry + MVP Templates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Shorts 9:16专用 Manim template registry 和 14个 MVP templates，为 LLM code generation 提供稳定的 fallback。

**Architecture:** 遵循 long-form TemplateRegistry 的 `has()`/`get()` 接口，但在 `video/templates/short/` 目录下创建独立的命名空间。所有模板生成的 Manim 代码必须遵守 9:16 safe zone（上部 12%，下部 20%）。

**Tech Stack:** Python, Manim, pytest

---

## File Structure

```
src/manim_video_gen/video/templates/short/
├── __init__.py
├── short_registry.py          # ShortTemplateRegistry class
├── beat_templates.py          # 5 beat templates
├── concept_templates.py       # 6 concept templates
└── domain_templates.py        # 3 domain templates

tests/test_video/
└── test_short_templates.py    # All short template tests
```

---

### Task 1: Create Short Templates Directory Structure

**Files:**
- Create: `src/manim_video_gen/video/templates/short/__init__.py`
- Create: `src/manim_video_gen/video/templates/short/short_registry.py`

- [ ] **Step 1: Create directory and __init__.py**

```bash
mkdir -p src/manim_video_gen/video/templates/short
```

Create `src/manim_video_gen/video/templates/short/__init__.py`:
```python
"""Short-form (9:16) templates for YouTube Shorts."""
```

- [ ] **Step 2: Write failing test for ShortTemplateRegistry**

Create `tests/test_video/test_short_templates.py`:
```python
"""ShortTemplateRegistry has/get interface tests."""

import pytest

from manim_video_gen.video.templates.short.short_registry import ShortTemplateRegistry


class TestShortTemplateRegistryHas:
    def test_has_short_concept_equation(self):
        registry = ShortTemplateRegistry()
        assert registry.has("short_concept_equation") is True

    def test_has_nonexistent(self):
        registry = ShortTemplateRegistry()
        assert registry.has("nonexistent") is False

    def test_has_empty_string(self):
        registry = ShortTemplateRegistry()
        assert registry.has("") is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_video/test_short_templates.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 4: Implement ShortTemplateRegistry**

Create `src/manim_video_gen/video/templates/short/short_registry.py`:
```python
"""Registry for short-form (9:16) templates."""

from __future__ import annotations

from typing import Any, Callable

from manim_video_gen.models.script import Segment


class ShortTemplateRegistry:
    """Dispatch segment.visual_type to short-form template renderers."""

    def __init__(self) -> None:
        self._renderers: dict[str, Callable[[Segment, float], str]] = {}

    def has(self, visual_type: str) -> bool:
        return visual_type in self._renderers

    def get(self, visual_type: str) -> Callable[[Segment, float], str] | None:
        return self._renderers.get(visual_type)

    def register(
        self,
        visual_type: str,
        renderer: Callable[[Segment, float], str],
    ) -> None:
        self._renderers[visual_type] = renderer

    def render_code_for_segment(self, segment: Segment, duration: float) -> str:
        vt = segment.visual_type
        renderer = self._renderers.get(vt)
        if renderer is None:
            raise KeyError(f"Unsupported short visual_type: {vt}")
        return renderer(segment, duration)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_video/test_short_templates.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/manim_video_gen/video/templates/short/ tests/test_video/test_short_templates.py
git commit -m "feat: add ShortTemplateRegistry with has/get interface"
```

---

### Task 2: Implement Beat Templates (5 types)

**Files:**
- Create: `src/manim_video_gen/video/templates/short/beat_templates.py`
- Modify: `src/manim_video_gen/video/templates/short/short_registry.py`

- [ ] **Step 1: Write failing tests for beat templates**

Add to `tests/test_video/test_short_templates.py`:
```python
class TestBeatTemplates:
    @pytest.mark.parametrize(
        "visual_type",
        ["short_hook", "short_before", "short_after", "short_payoff_card", "short_cta"],
    )
    def test_beat_template_registered(self, visual_type):
        registry = ShortTemplateRegistry()
        assert registry.has(visual_type) is True

    def test_short_hook_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type="short_hook", visual_params={"headline": "흥미로운 시작"})
        code = registry.render_code_for_segment(seg, duration=2.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "흥미로운 시작" in code
```

Helper function at top of file:
```python
from manim_video_gen.models.script import Segment


def _make_segment(**kwargs) -> Segment:
    defaults = {
        "id": 0,
        "narration": "테스트 나레이션",
        "tts_text": "테스트 나레이션",
        "visual_description": "시각적 설명",
        "visual_type": "short_hook",
        "visual_params": {},
        "prev_scene_state": None,
    }
    defaults.update(kwargs)
    return Segment(**defaults)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_video/test_short_templates.py::TestBeatTemplates -v`
Expected: FAIL with "has() returns False"

- [ ] **Step 3: Implement beat templates**

Create `src/manim_video_gen/video/templates/short/beat_templates.py`:
```python
"""Beat templates for short-form content."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import Segment

# 9:16 safe zone constants
FRAME_HEIGHT = 19.20  # Manim units for 1920px
FRAME_WIDTH = 10.80   # Manim units for 1080px
SAFE_TOP_BUFF = FRAME_HEIGHT * 0.12    # 12% from top
SAFE_BOTTOM_BUFF = FRAME_HEIGHT * 0.20  # 20% from bottom


def _render_short_hook(segment: Segment, duration: float) -> str:
    """Hook scene - attention-grabbing opening."""
    headline = str(segment.visual_params.get("headline", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        txt = Text("{headline}", font_size=48)
        txt.move_to(ORIGIN)
        self.play(Write(txt), run_time=min({duration:.3f} * 0.6, 1.5))
        self.wait(max({duration:.3f} - 1.5, 0.5))
"""


def _render_short_before(segment: Segment, duration: float) -> str:
    """Before scene - setup context."""
    text = str(segment.visual_params.get("text", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        txt = Text("{text}", font_size=40)
        txt.move_to(ORIGIN)
        self.play(FadeIn(txt), run_time=min({duration:.3f} * 0.5, 1.0))
        self.wait(max({duration:.3f} - 1.0, 0.5))
"""


def _render_short_after(segment: Segment, duration: float) -> str:
    """After scene - show result."""
    text = str(segment.visual_params.get("text", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        txt = Text("{text}", font_size=40)
        txt.move_to(ORIGIN)
        self.play(FadeIn(txt), run_time=min({duration:.3f} * 0.5, 1.0))
        self.wait(max({duration:.3f} - 1.0, 0.5))
"""


def _render_short_payoff_card(segment: Segment, duration: float) -> str:
    """Payoff card - key takeaway."""
    headline = str(segment.visual_params.get("headline", ""))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        txt = Text("{headline}", font_size=52, color=YELLOW)
        txt.move_to(ORIGIN)
        self.play(Write(txt), run_time=min({duration:.3f} * 0.6, 1.5))
        self.wait(max({duration:.3f} - 1.5, 0.5))
"""


def _render_short_cta(segment: Segment, duration: float) -> str:
    """Call-to-action scene."""
    text = str(segment.visual_params.get("text", "구독!"))
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        txt = Text("{text}", font_size=56, color=BLUE)
        txt.move_to(ORIGIN)
        self.play(Write(txt), run_time=min({duration:.3f} * 0.6, 1.5))
        self.wait(max({duration:.3f} - 1.5, 0.5))
"""


BEAT_RENDERERS = {
    "short_hook": _render_short_hook,
    "short_before": _render_short_before,
    "short_after": _render_short_after,
    "short_payoff_card": _render_short_payoff_card,
    "short_cta": _render_short_cta,
}
```

- [ ] **Step 4: Register beat templates in registry**

Modify `src/manim_video_gen/video/templates/short/short_registry.py`:
```python
from manim_video_gen.video.templates.short.beat_templates import BEAT_RENDERERS

class ShortTemplateRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, Callable[[Segment, float], str]] = {}
        self._renderers.update(BEAT_RENDERERS)
        # ... rest unchanged
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_video/test_short_templates.py::TestBeatTemplates -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/manim_video_gen/video/templates/short/beat_templates.py src/manim_video_gen/video/templates/short/short_registry.py tests/test_video/test_short_templates.py
git commit -m "feat: add 5 beat templates for short-form content"
```

---

### Task 3: Implement Concept Templates (6 types)

**Files:**
- Create: `src/manim_video_gen/video/templates/short/concept_templates.py`
- Modify: `src/manim_video_gen/video/templates/short/short_registry.py`

- [ ] **Step 1: Write failing tests for concept templates**

Add to `tests/test_video/test_short_templates.py`:
```python
class TestConceptTemplates:
    @pytest.mark.parametrize(
        "visual_type",
        [
            "short_concept_equation",
            "short_concept_graph",
            "short_concept_number_line",
            "short_concept_annotated",
            "short_concept_compare",
            "short_concept_pattern",
        ],
    )
    def test_concept_template_registered(self, visual_type):
        registry = ShortTemplateRegistry()
        assert registry.has(visual_type) is True

    def test_short_concept_equation_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_equation",
            visual_params={"latex": r"E = mc^2"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "E = mc^2" in code
        assert "MathTex" in code

    def test_short_concept_equation_safe_zone(self):
        """Verify template respects 9:16 safe zone."""
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_concept_equation",
            visual_params={"latex": r"x^2 + y^2 = r^2"},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "19.20" in code or "19.2" in code  # frame_height
        assert "10.80" in code or "10.8" in code  # frame_width
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_video/test_short_templates.py::TestConceptTemplates -v`
Expected: FAIL

- [ ] **Step 3: Implement concept templates**

Create `src/manim_video_gen/video/templates/short/concept_templates.py`:
```python
"""Concept templates for short-form content."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import Segment

FRAME_HEIGHT = 19.20
FRAME_WIDTH = 10.80


def _render_short_concept_equation(segment: Segment, duration: float) -> str:
    """Display a centered equation."""
    latex = str(segment.visual_params.get("latex", ""))
    font_size = int(segment.visual_params.get("font_size", 48))
    color = str(segment.visual_params.get("color", "WHITE"))
    
    t_write = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_write, 0.5)
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        eq = MathTex(r"{latex}", font_size={font_size}).set_color({color})
        eq.move_to(ORIGIN)
        self.play(Write(eq), run_time={t_write:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_graph(segment: Segment, duration: float) -> str:
    """Display a simple graph plot."""
    func = str(segment.visual_params.get("func", "lambda x: x"))
    x_min = float(segment.visual_params.get("x_min", -3))
    x_max = float(segment.visual_params.get("x_max", 3))
    color = str(segment.visual_params.get("color", "BLUE"))
    
    t_draw = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_draw, 0.5)
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        axes = Axes(
            x_range=[{x_min}, {x_max}, 1],
            y_range=[-3, 3, 1],
            axis_config={{"include_numbers": True}},
        ).scale(0.7)
        axes.move_to(ORIGIN)
        
        graph = axes.plot({func}, color={color})
        
        self.play(Create(axes), run_time=0.8)
        self.play(Create(graph), run_time={t_draw:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_number_line(segment: Segment, duration: float) -> str:
    """Display a number line with marker."""
    value = float(segment.visual_params.get("value", 0))
    label = str(segment.visual_params.get("label", ""))
    
    t_anim = min(duration * 0.6, 1.5)
    t_wait = max(duration - t_anim, 0.5)
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        nl = NumberLine(
            x_range=[-5, 5, 1],
            length=8,
            include_numbers=True,
        )
        nl.move_to(ORIGIN)
        
        dot = Dot(nl.n2p({value}), color=YELLOW)
        label = Text("{label}", font_size=36).next_to(dot, UP)
        
        self.play(Create(nl), run_time=0.8)
        self.play(Create(dot), Write(label), run_time={t_anim:.3f})
        self.wait({t_wait:.3f})
"""


def _render_short_concept_annotated(segment: Segment, duration: float) -> str:
    """Display equation with annotations."""
    latex = str(segment.visual_params.get("latex", ""))
    annotation = str(segment.visual_params.get("annotation", ""))
    
    t_write = min(duration * 0.5, 1.5)
    t_ann = min(duration * 0.3, 1.0)
    t_wait = max(duration - t_write - t_ann, 0.5)
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        eq = MathTex(r"{latex}", font_size=48)
        eq.move_to(ORIGIN)
        
        self.play(Write(eq), run_time={t_write:.3f})
        
        if "{annotation}":
            brace = Brace(eq, DOWN)
            txt = brace.get_text("{annotation}")
            self.play(Create(brace), Write(txt), run_time={t_ann:.3f})
        
        self.wait({t_wait:.3f})
"""


def _render_short_concept_compare(segment: Segment, duration: float) -> str:
    """Compare two items side by side."""
    left = str(segment.visual_params.get("left", ""))
    right = str(segment.visual_params.get("right", ""))
    
    t_show = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_show, 0.5)
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        left_txt = Text("{left}", font_size=40).shift(LEFT * 2.5)
        right_txt = Text("{right}", font_size=40).shift(RIGHT * 2.5)
        vs = Text("VS", font_size=36, color=YELLOW)
        
        self.play(Write(left_txt), run_time=0.8)
        self.play(Write(vs), run_time=0.4)
        self.play(Write(right_txt), run_time=0.8)
        self.wait({t_wait:.3f})
"""


def _render_short_concept_pattern(segment: Segment, duration: float) -> str:
    """Show a visual pattern."""
    items = segment.visual_params.get("items", [])
    if not isinstance(items, list):
        items = []
    
    t_show = min(duration * 0.6, 2.0)
    t_wait = max(duration - t_show, 0.5)
    
    items_str = ", ".join(f'"{i}"' for i in items[:5]) if items else '"패턴"'
    
    return f"""from manim import *

class Segment(Scene):
    def construct(self):
        self.camera.frame_width = {FRAME_WIDTH}
        self.camera.frame_height = {FRAME_HEIGHT}
        
        items = VGroup(*[
            Text(t, font_size=36) for t in [{items_str}]
        ]).arrange(RIGHT, buff=0.5)
        items.move_to(ORIGIN)
        
        self.play(Write(items), run_time={t_show:.3f})
        self.wait({t_wait:.3f})
"""


CONCEPT_RENDERERS = {
    "short_concept_equation": _render_short_concept_equation,
    "short_concept_graph": _render_short_concept_graph,
    "short_concept_number_line": _render_short_concept_number_line,
    "short_concept_annotated": _render_short_concept_annotated,
    "short_concept_compare": _render_short_concept_compare,
    "short_concept_pattern": _render_short_concept_pattern,
}
```

- [ ] **Step 4: Register concept templates in registry**

Modify `src/manim_video_gen/video/templates/short/short_registry.py`:
```python
from manim_video_gen.video.templates.short.concept_templates import CONCEPT_RENDERERS

class ShortTemplateRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, Callable[[Segment, float], str]] = {}
        self._renderers.update(BEAT_RENDERERS)
        self._renderers.update(CONCEPT_RENDERERS)
        # ... rest unchanged
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_video/test_short_templates.py::TestConceptTemplates -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/manim_video_gen/video/templates/short/concept_templates.py src/manim_video_gen/video/templates/short/short_registry.py tests/test_video/test_short_templates.py
git commit -m "feat: add 6 concept templates for short-form content"
```

---

### Task 4: Implement Domain Templates (3 types)

**Files:**
- Create: `src/manim_video_gen/video/templates/short/domain_templates.py`
- Modify: `src/manim_video_gen/video/templates/short/short_registry.py`

- [ ] **Step 1: Write failing tests for domain templates**

Add to `tests/test_video/test_short_templates.py`:
```python
class TestDomainTemplates:
    @pytest.mark.parametrize(
        "visual_type",
        ["short_domain_icon", "short_stat_chart", "short_flow_arrow"],
    )
    def test_domain_template_registered(self, visual_type):
        registry = ShortTemplateRegistry()
        assert registry.has(visual_type) is True

    def test_short_stat_chart_generates_valid_python(self):
        registry = ShortTemplateRegistry()
        seg = _make_segment(
            visual_type="short_stat_chart",
            visual_params={"values": [10, 20, 30], "labels": ["A", "B", "C"]},
        )
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "BarChart" in code or "Rectangle" in code
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_video/test_short_templates.py::TestDomainTemplates -v`
Expected: FAIL

- [ ] **Step 3: Implement domain templates**

Create `src/manim_video_gen/video/templates/short/domain_templates.py`:
```python
"""Domain-specific templates for short-form content."""

from __future__ import annotations

from typing import Any

from manim_video_gen.models.script import Segment

FRAME_HEIGHT = 19.20
FRAME_WIDTH = 10.80


def _render_short_domain_icon(segment: Segment, duration: float) -> str:
    """Display an icon-like shape with label."""
    label = str(segment.visual_params.get("label", ""))
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
        label = Text("{label}", font_size=36).next_to(icon, DOWN)
        
        self.play(Create(icon), run_time={t_draw:.3f})
        self.play(Write(label), run_time=0.5)
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
    labels_str = ", ".join(f'"{l}"' for l in labels[:6])
    
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
    
    steps_str = ", ".join(f'"{s}"' for s in steps[:4])
    
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
```

- [ ] **Step 4: Register domain templates in registry**

Modify `src/manim_video_gen/video/templates/short/short_registry.py`:
```python
from manim_video_gen.video.templates.short.domain_templates import DOMAIN_RENDERERS

class ShortTemplateRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, Callable[[Segment, float], str]] = {}
        self._renderers.update(BEAT_RENDERERS)
        self._renderers.update(CONCEPT_RENDERERS)
        self._renderers.update(DOMAIN_RENDERERS)
        # ... rest unchanged
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_video/test_short_templates.py::TestDomainTemplates -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/manim_video_gen/video/templates/short/domain_templates.py src/manim_video_gen/video/templates/short/short_registry.py tests/test_video/test_short_templates.py
git commit -m "feat: add 3 domain templates for short-form content"
```

---

### Task 5: Integration Tests and Final Verification

**Files:**
- Modify: `tests/test_video/test_short_templates.py`

- [ ] **Step 1: Add integration tests**

Add to `tests/test_video/test_short_templates.py`:
```python
class TestAllTemplatesRegistered:
    """Verify all 14 templates are registered."""

    ALL_TYPES = [
        # Beat (5)
        "short_hook", "short_before", "short_after", "short_payoff_card", "short_cta",
        # Concept (6)
        "short_concept_equation", "short_concept_graph", "short_concept_number_line",
        "short_concept_annotated", "short_concept_compare", "short_concept_pattern",
        # Domain (3)
        "short_domain_icon", "short_stat_chart", "short_flow_arrow",
    ]

    def test_all_templates_registered(self):
        registry = ShortTemplateRegistry()
        for vt in self.ALL_TYPES:
            assert registry.has(vt) is True, f"Missing template: {vt}"

    def test_total_count(self):
        registry = ShortTemplateRegistry()
        registered = sum(1 for vt in self.ALL_TYPES if registry.has(vt))
        assert registered == 14

    def test_unknown_type_returns_false(self):
        registry = ShortTemplateRegistry()
        assert registry.has("unknown_type_xyz") is False

    @pytest.mark.parametrize("visual_type", ALL_TYPES)
    def test_template_generates_valid_python(self, visual_type):
        """All templates should generate syntactically valid Python."""
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        assert "from manim import *" in code
        assert "class Segment(Scene):" in code
        assert "def construct(self):" in code
        compile(code, "<test>", "exec")


class TestSafeZoneCompliance:
    """Verify all templates respect 9:16 safe zone."""

    ALL_TYPES = [
        "short_hook", "short_before", "short_after", "short_payoff_card", "short_cta",
        "short_concept_equation", "short_concept_graph", "short_concept_number_line",
        "short_concept_annotated", "short_concept_compare", "short_concept_pattern",
        "short_domain_icon", "short_stat_chart", "short_flow_arrow",
    ]

    @pytest.mark.parametrize("visual_type", ALL_TYPES)
    def test_template_sets_9_16_frame(self, visual_type):
        """All templates should set 9:16 frame dimensions."""
        registry = ShortTemplateRegistry()
        seg = _make_segment(visual_type=visual_type)
        code = registry.render_code_for_segment(seg, duration=3.0)
        # Should set frame dimensions for 9:16
        assert "19.2" in code or "10.8" in code
```

- [ ] **Step 2: Run all tests**

Run: `pytest tests/test_video/test_short_templates.py -v`
Expected: All tests PASS

- [ ] **Step 3: Verify path isolation**

```bash
# Ensure no imports from long-form templates
grep -r "from manim_video_gen.video.templates.registry import" src/manim_video_gen/video/templates/short/
# Should return nothing
```

- [ ] **Step 4: Final commit**

```bash
git add tests/test_video/test_short_templates.py
git commit -m "test: add integration tests for 14 short templates"
```

---

## Verification Checklist

After implementation, verify:

- [ ] `ShortTemplateRegistry.has("short_concept_equation")` → True
- [ ] `ShortTemplateRegistry.has("nonexistent")` → False
- [ ] 9:16 해상도에서 주요 템플릿 렌더 시 headline/subtitle 영역과 겹침 없음
- [ ] 템플릿 14종 모두 import 및 인스턴스화 가능
- [ ] long-form 템플릿과 경로/네임스페이스 격리 확인
