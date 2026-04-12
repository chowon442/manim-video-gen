from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from manim_video_gen.tools.verify_render_regressions import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli())
