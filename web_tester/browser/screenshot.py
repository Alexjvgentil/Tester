from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image


class ScreenshotManager:
    """Saves screenshots to disk and converts them for model consumption."""

    def __init__(self, screenshots_dir: Path, max_width: int = 1280) -> None:
        self.screenshots_dir = screenshots_dir
        self.max_width = max_width
        screenshots_dir.mkdir(parents=True, exist_ok=True)

    def save(self, raw_bytes: bytes, step: int, label: str = "step") -> Path:
        """Save raw PNG bytes to disk. Returns the saved path."""
        safe_label = label.replace(" ", "_").replace("/", "_")[:30]
        ts = datetime.now().strftime("%H%M%S")
        filename = f"step_{step:03d}_{safe_label}_{ts}.png"
        path = self.screenshots_dir / filename

        img = self._resize_if_needed(raw_bytes)
        img.save(path, format="PNG", optimize=True)
        return path

    def to_pil(self, raw_bytes: bytes) -> Image.Image:
        """Return a PIL Image, resized if needed."""
        return self._resize_if_needed(raw_bytes)

    def to_base64(self, raw_bytes: bytes) -> str:
        """Return base64-encoded PNG string."""
        img = self._resize_if_needed(raw_bytes)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    def _resize_if_needed(self, raw_bytes: bytes) -> Image.Image:
        img = Image.open(BytesIO(raw_bytes))
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((self.max_width, new_height), Image.LANCZOS)
        return img
