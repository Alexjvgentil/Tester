from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

from web_tester.exceptions import ConfigError


@dataclass
class Config:
    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    browser_headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    max_steps: int = 50
    test_runs_dir: str = "test_runs"

    def validate(self) -> None:
        if self.model_provider not in ("openai", "anthropic"):
            raise ConfigError(f"MODEL_PROVIDER must be 'openai' or 'anthropic', got '{self.model_provider}'")
        if self.model_provider == "openai" and not self.openai_api_key:
            raise ConfigError("OPENAI_API_KEY is required when MODEL_PROVIDER=openai")
        if self.model_provider == "anthropic" and not self.anthropic_api_key:
            raise ConfigError("ANTHROPIC_API_KEY is required when MODEL_PROVIDER=anthropic")


def load_config(env_file: str = ".env") -> Config:
    load_dotenv(env_file, override=False)

    def _bool(val: str) -> bool:
        return val.lower() in ("1", "true", "yes")

    return Config(
        model_provider=os.getenv("MODEL_PROVIDER", "openai").lower(),
        model_name=os.getenv("MODEL_NAME", "gpt-4o"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        browser_headless=_bool(os.getenv("BROWSER_HEADLESS", "true")),
        viewport_width=int(os.getenv("VIEWPORT_WIDTH", "1280")),
        viewport_height=int(os.getenv("VIEWPORT_HEIGHT", "720")),
        max_steps=int(os.getenv("MAX_STEPS", "50")),
        test_runs_dir=os.getenv("TEST_RUNS_DIR", "test_runs"),
    )
