from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from web_tester.config import Config


def _slugify(text: str, max_len: int = 40) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:max_len].strip("_")


@dataclass
class StepRecord:
    step: int
    timestamp: str
    tool_name: str
    tool_args: dict
    result_success: bool
    result_message: str
    screenshot_path: str
    url_at_step: str
    model_output: str = ""


class TestSession:
    """Manages a single test-run folder and its artifacts."""

    def __init__(self, name: str, config: Config) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slugify(name) or "test"
        folder_name = f"{ts}_{slug}"

        runs_dir = Path(config.test_runs_dir)
        self.root_dir = runs_dir / folder_name
        self.screenshots_dir = self.root_dir / "screenshots"
        self.log_file = self.root_dir / "execution.log"
        self.report_json = self.root_dir / "report.json"
        self.report_md = self.root_dir / "report.md"

        self.start_time = datetime.now()
        self._steps: list[StepRecord] = []
        self._log_handle = None

    def create(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(exist_ok=True)
        self._log_handle = open(self.log_file, "w", encoding="utf-8")
        self._log({"event": "session_start", "session": self.root_dir.name})

    def record_step(self, record: StepRecord) -> None:
        self._steps.append(record)
        self._log({
            "event": "step",
            "step": record.step,
            "tool": record.tool_name,
            "args": record.tool_args,
            "success": record.result_success,
            "message": record.result_message,
            "url": record.url_at_step,
        })

    def log_error(self, error: str) -> None:
        self._log({"event": "error", "error": error})

    def close(self, status: str, final_message: str) -> None:
        self._log({
            "event": "session_end",
            "status": status,
            "steps": len(self._steps),
            "final_message": final_message,
        })
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None

    def _log(self, data: dict) -> None:
        if self._log_handle:
            entry = {"ts": datetime.now().isoformat(), **data}
            self._log_handle.write(json.dumps(entry) + "\n")
            self._log_handle.flush()

    @property
    def steps(self) -> list[StepRecord]:
        return list(self._steps)

    @property
    def duration_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
