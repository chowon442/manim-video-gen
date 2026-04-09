"""Manim Community Edition API hints injected into Manim code-generation prompts."""

MANIM_API_REFERENCE_TEXT = """
You MUST use Manim **Community Edition** (from manim import *). Do NOT use 3b1b legacy names.

## Legacy → CE renames
- ShowCreation  → Create
- TextMobject   → Text
- TexMobject    → Tex  (prefer MathTex for pure math)

## Scene classes
- Scene                           # basic scene
- MovingCameraScene               # camera panning/zooming

## Math / Text mobjects
- MathTex(r"...", font_size=48)              # display-math; use raw strings
- Tex(r"...", font_size=36)                  # mixed LaTeX+text
- Text("string", font_size=36, color=WHITE)  # plain text (no LaTeX)
- Integer(number)                            # integer display
- DecimalNumber(number, num_decimal_places=2)
- MathTex substrings: use {{token}} to enable TransformMatchingTex

## Geometry mobjects
- Dot(point=ORIGIN, color=WHITE, radius=0.08)
- Circle(radius=1.0, color=WHITE)
- Square(side_length=2.0, color=WHITE)
- Rectangle(width=4.0, height=2.0, color=WHITE)
- Line(start=LEFT, end=RIGHT, color=WHITE)
- DashedLine(start, end, dash_length=0.2, color=WHITE)
- Arrow(start, end, color=WHITE, buff=0.1)
- DoubleArrow(start, end, color=WHITE)
- Vector(direction, color=YELLOW)            # Arrow from ORIGIN
- Brace(mobject, direction=DOWN, color=WHITE)
- SurroundingRectangle(mobject, color=YELLOW, buff=0.1)
- Underline(mobject, color=YELLOW)
- Cross(mobject, stroke_color=RED)

## Grouping / layout
- VGroup(*mobjects)                          # vertical group
- HGroup(*mobjects)                          # horizontal group
- VGroup(...).arrange(DOWN, buff=0.5)        # stack vertically
- VGroup(...).arrange(RIGHT, buff=0.3)       # place side-by-side

## Graphs / plots
- Axes(x_range=[a, b, step], y_range=[c, d, step], x_length=6, y_length=4)
- axes.plot(lambda x: x**2, color=BLUE)
- axes.get_graph_label(graph, label=r"f(x)", x_val=1, direction=UR)
- axes.plot_parametric_curve(lambda t: [t, t**2, 0], t_range=[0, 2])
- NumberLine(x_range=[-3, 3, 1], length=6, include_numbers=True)
- NumberPlane(x_range=[-5, 5, 1], y_range=[-3, 3, 1])
- ParametricFunction(lambda t: np.array([np.cos(t), np.sin(t), 0]), t_range=[0, TAU])

## Matrix
- Matrix([[1, 2], [3, 4]])
- Matrix([[1, 2], [3, 4]], left_bracket="(", right_bracket=")")
- IntegerMatrix([[1, 2], [3, 4]])

## Dynamic / value tracking
- ValueTracker(initial_value)                # track a scalar
  - tracker.get_value()
  - tracker.set_value(new_val)
  - tracker.animate.set_value(new_val)       # animated change
- always_redraw(lambda: ...)                 # redraw on each frame

## Core animations
- Write(mobject)
- Create(mobject)                            # draw border
- FadeIn(mobject, shift=UP*0.2)
- FadeOut(mobject, shift=DOWN*0.2)
- Transform(m1, m2)                          # morphs in place
- ReplacementTransform(m1, m2)              # replaces m1 with m2
- TransformMatchingTex(m1, m2)              # smart LaTeX token matching
- FadeTransform(m1, m2)
- TransformFromCopy(m1, m2)
- GrowFromCenter(mobject)
- ShrinkToCenter(mobject)
- Rotate(mobject, angle=PI/2, about_point=ORIGIN)
- MoveAlongPath(mobject, path)
- Indicate(mobject, color=YELLOW, scale_factor=1.2)
- Circumscribe(mobject, color=YELLOW, fade_out=True)
- Flash(point, color=YELLOW, line_length=0.2)
- ShowPassingFlash(mobject, time_width=0.5)

## Composition / timing
- AnimationGroup(anim1, anim2, lag_ratio=0.0)   # simultaneous
- LaggedStart(anim1, anim2, lag_ratio=0.3)       # staggered
- Succession(anim1, anim2)                        # sequential
- self.play(anim, run_time=2.0)
- self.play(mob.animate.shift(UP), run_time=1.0)
- self.wait(0.5)

## .animate shorthand (chainable)
- mob.animate.shift(UP * 0.5)
- mob.animate.scale(1.5)
- mob.animate.set_color(BLUE)
- mob.animate.move_to(ORIGIN)
- mob.animate.next_to(other, DOWN, buff=0.3)
- mob.animate.to_edge(LEFT)
- mob.animate.set_opacity(0.5)

## Position helpers
- mob.shift(RIGHT * 2)
- mob.move_to(ORIGIN)
- mob.next_to(other, DOWN, buff=0.2)
- mob.to_edge(UP, buff=0.5)
- mob.to_corner(UL)
- mob.get_center()  → np.array
- mob.get_top() / .get_bottom() / .get_left() / .get_right()
- mob.get_corner(UL)

## Colors (selected)
WHITE, BLACK, GRAY, LIGHT_GRAY, DARK_GRAY
RED, GREEN, BLUE, YELLOW, ORANGE, PURPLE, TEAL, PINK
BLUE_A .. BLUE_E, RED_A .. RED_E, etc.

## Constants
UP=(0,1,0), DOWN=(0,-1,0), LEFT=(-1,0,0), RIGHT=(1,0,0)
UL, UR, DL, DR  (diagonals)
ORIGIN=(0,0,0)
PI ≈ 3.14159,  TAU = 2*PI,  DEGREES = PI/180

## Rules
- Class name MUST be: Segment
- Implement only construct(self)
- Avoid os / sys / subprocess / open / socket imports
- Keep total animation time close to the requested duration_seconds
- MathTex/Tex raw strings: LaTeX needs one backslash per command. Correct: MathTex(r'\\frac{a}{b}'); wrong: MathTex(r'\\\\frac{a}{b}') (double backslash before frac/sqrt/pm breaks latex).
- NEVER put Korean/CJK inside MathTex or Tex (e.g. no \\text{또는}); pdfLaTeX cannot typeset it. Use \\text{or} or \\quad only; Korean belongs in narration or separate Text().
"""
