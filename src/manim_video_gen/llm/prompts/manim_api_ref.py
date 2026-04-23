"""Manim Community Edition API hints injected into Manim code-generation prompts.

Portions distilled from https://github.com/adithya-s-k/manim_skill (MIT).
"""

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
- brace.get_tex(r"\\theta")                    # label from tex (ASCII)
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
- axes.get_area(graph, x_range=[a, b], color=BLUE, opacity=0.4)
- axes.get_riemann_rectangles(graph, x_range=[a,b], dx=0.2, color=BLUE)
- axes.get_vertical_line(x=x0, color=YELLOW)
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
- TracedPath(point_generator, stroke_color=YELLOW)   # path from moving point

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
- LaggedStart(*anims, lag_ratio=0.2)            # staggered list
- LaggedStartMap(Create, group, lag_ratio=0.1)
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

## Transform details
- Transform(A, B): A morphs into B's shape, but variable A still references the same mobject (B is NOT added to the scene).
- ReplacementTransform(A, B): A is removed and B is added — clearer variable semantics; usually preferred.
- TransformMatchingTex(A, B): smooth token-wise morph between MathTex; use {{token}} brace groups for best matching when from_latex/to_latex share subexpressions.
- TransformMatchingShapes(A, B): shape-based matching (e.g. Text); use when not using LaTeX.
- Transform(..., path_arc=PI/2): curved morph path; useful for equation→diagram transitions.

## Animation composition
- AnimationGroup(*anims, lag_ratio=0.0): simultaneous (0), staggered overlap (0.2–0.5), sequential (1.0).
- LaggedStart(*anims, lag_ratio=0.05): convenience wrapper; good for many objects appearing in sequence.
- LaggedStartMap(Create, vgroup, lag_ratio=0.1): apply one animation type to all children with stagger.
- Succession(*anims): play one after another; like multiple self.play() calls but one unit.
- Recommended lag_ratio for polish: 0.05–0.2 (higher feels slow).
- run_time on AnimationGroup applies to the whole group and is distributed across children.

## Timing / rate functions
- Common rate_func: smooth (default feel), linear (constant speed), rush_into / rush_from (accel/decel), there_and_back (emphasis pulse), ease_in_*, ease_out_*, ease_in_out_* (quad/cubic/expo/circ/sine/back/bounce).
- Prefer run_time 0.5–3s per major motion; split long explanations across multiple self.play() calls.
- Use self.wait(t) to pad to audio/TTS length; do not inflate run_time just to fill silence.

## LaTeX advanced
- Multi-part MathTex: MathTex("a", "^2", "+", "b", "^2", "=", "c", "^2") lets you index eq[0], eq[1], ... for per-part styling.
- {{token}} brace groups: key for TransformMatchingTex; e.g. "{{a}} x^2 + {{b}} x + {{c}} = 0".
- Coloring: eq.set_color_by_tex(r"\\pi", BLUE); MathTex(..., substrings_to_isolate=["x"]) then set_color_by_tex for repeated symbols; or eq[0][2].set_color(RED).
- MathTex for pure math; Tex(r"mixed $x^2$ text") when mixing prose and math.
- get_part_by_tex works reliably on parts created via {{token}} or substrings_to_isolate.

## Dynamic: ValueTracker / always_redraw
- ValueTracker(v): get_value(), set_value(), tracker.animate.set_value(new).
- Updaters: mob.add_updater(lambda m: m.set_value(tracker.get_value())) for DecimalNumber etc.
- always_redraw(lambda: ...): rebuild mobject each frame for complex following shapes.
- Call mob.clear_updaters() when done to avoid stray per-frame updates in later plays.
- Useful for counting numbers, parameter sweeps, and point-following visuals.

## Common pitfalls
- MathTex/Tex: always r"..." in Python; one backslash per LaTeX command (JSON escaping is separate).
- Keep Korean/CJK out of MathTex when possible; use Text() beside. If needed: xelatex + \\text{...}.
- After Transform(A, B), the Python name still points at A (now looking like B).
- TransformMatchingTex with no shared {{token}} parts may look like a crossfade; consider FadeTransform explicitly.
- axes.plot across a discontinuity (e.g. 1/x through 0) can break; split x_range or use discontinuities=[x0].
- Heavy add_updater(next_to/...) every frame: consider suspend_updating() during a play if needed.
- Never put slow I/O or heavy work inside self.play() — construct runs at import/render time.

## Rules
- Class name MUST be: Segment
- Implement only construct(self)
- Do NOT add `if __name__ == "__main__":` blocks, `Segment().render()`, `scene.render()`, or any code after the `class Segment` body. The CLI loads this file as a module; such extras are unnecessary and often cause IndentationError or import failures.
- End the file when the `Segment` class ends (imports + optional tiny helpers above the class are OK). No trailing executable lines below the class.
- Avoid os / sys / subprocess / open / socket imports
- Keep total animation time close to the requested duration_seconds
- MathTex/Tex raw strings: LaTeX needs one backslash per command. Correct: MathTex(r'\\frac{a}{b}'); wrong: MathTex(r'\\\\frac{a}{b}') (double backslash before frac/sqrt/pm breaks latex).
- Avoid Korean/CJK inside MathTex/Tex when possible; prefer separate Text() labels. If unavoidable, use xelatex+xeCJK template and wrap Korean phrase in \\text{...} so spaces are preserved.
"""
