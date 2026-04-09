"""Temporary workspace directories for a render job."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path


class SessionWorkspace:
    def __init__(self, root: Path | None = None) -> None:
        if root is None:
            # Windows에서 MiKTeX의 dvisvgm이 서로 다른 드라이브 간 DVI→SVG 변환에
            # 실패하는 버그가 있음. 시스템 TEMP(보통 C:\Users\...\AppData\Local\Temp)
            # 대신 프로젝트 루트의 .tmp 디렉토리를 사용해 같은 드라이브에 유지한다.
            _local_tmp = Path(__file__).resolve().parents[3] / ".tmp"
            _local_tmp.mkdir(exist_ok=True)
            self.root = Path(
                tempfile.mkdtemp(
                    prefix=f"manim_video_{uuid.uuid4().hex[:8]}_",
                    dir=_local_tmp,
                )
            )
        else:
            self.root = root
            self.root.mkdir(parents=True, exist_ok=True)

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    def cleanup(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
