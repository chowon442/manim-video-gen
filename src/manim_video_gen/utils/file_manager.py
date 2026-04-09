"""Temporary workspace directories for a render job."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path


class SessionWorkspace:
    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            self.root = Path(tempfile.mkdtemp(prefix=f"manim_video_{uuid.uuid4().hex[:8]}_"))
        else:
            self.root = root
            self.root.mkdir(parents=True, exist_ok=True)

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    def cleanup(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
