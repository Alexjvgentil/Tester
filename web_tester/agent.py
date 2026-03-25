from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image
from smolagents import CodeAgent, OpenAIServerModel, LiteLLMModel

from web_tester.browser.controller import BrowserController
from web_tester.browser.screenshot import ScreenshotManager
from web_tester.config import Config, load_config
from web_tester.storage.reporter import Reporter
from web_tester.storage.session import StepRecord, TestSession
from web_tester.tools.browser_tools import create_browser_tools


@dataclass
class TestResult:
    status: str           # "pass" | "fail" | "error" | "incomplete"
    final_message: str
    session_dir: Path
    steps_taken: int
    report_json: Path
    report_md: Path
    duration_seconds: float


def _create_model(config: Config):
    if config.model_provider == "openai":
        return OpenAIServerModel(
            model_id=config.model_name,
            api_key=config.openai_api_key,
        )
    else:
        # Anthropic via LiteLLM — model_id format: "anthropic/claude-..."
        model_id = config.model_name
        if not model_id.startswith("anthropic/"):
            model_id = f"anthropic/{model_id}"
        return LiteLLMModel(
            model_id=model_id,
            api_key=config.anthropic_api_key,
        )


def _build_task_prompt(url: str, instructions: str, viewport_w: int, viewport_h: int) -> str:
    return f"""You are an AI web testing agent. Your job is to test a web application by \
observing screenshots and interacting with the browser using the provided tools.

== STARTING URL ==
{url}

== VIEWPORT ==
{viewport_w}x{viewport_h} pixels. Coordinate origin (0,0) is the top-left corner.
Use these coordinates when calling click() or hover().

== INSTRUCTIONS ==
{instructions}

== HOW TO WORK ==
- A screenshot of the current browser state is provided at each step.
- Call ONE browser tool per step to interact with the page.
- After each action a new screenshot is automatically captured and shown to you.
- When all instructions have been completed successfully, call:
    final_answer("PASS: <brief summary of what was verified>")
- If you encounter an unrecoverable error or cannot complete the task, call:
    final_answer("FAIL: <description of what went wrong>")
- Do NOT stop without calling final_answer().
"""


class WebTestAgent:
    """High-level agent that wires CodeAgent + Playwright + storage together."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self.config.validate()

    def run(
        self,
        url: str,
        instructions: str,
        test_name: Optional[str] = None,
        verbose: bool = False,
    ) -> TestResult:
        name = test_name or instructions[:50]
        session = TestSession(name=name, config=self.config)
        session.create()

        screenshot_mgr = ScreenshotManager(session.screenshots_dir)
        browser = BrowserController(self.config)

        try:
            browser.start()
            browser.navigate(url)

            # Capture the initial state before the agent loop starts
            initial_raw = browser.take_screenshot()
            initial_path = screenshot_mgr.save(initial_raw, step=0, label="initial")
            session.record_step(StepRecord(
                step=0,
                timestamp=datetime.now().isoformat(),
                tool_name="navigate",
                tool_args={"url": url},
                result_success=True,
                result_message=f"Navigated to {url}",
                screenshot_path=str(initial_path.relative_to(session.root_dir)),
                url_at_step=browser.current_url(),
            ))

            initial_image = screenshot_mgr.to_pil(initial_raw)

            # Build the screenshot callback that injects images after each step
            step_counter = [0]

            def screenshot_callback(step_log, agent: CodeAgent) -> None:
                step_counter[0] += 1
                step_num = step_counter[0]

                # Determine which tool was just called
                tool_name = "step"
                tool_args: dict = {}
                if hasattr(step_log, "tool_calls") and step_log.tool_calls:
                    tc = step_log.tool_calls[0]
                    tool_name = getattr(tc, "name", "step") or "step"
                    tool_args = getattr(tc, "arguments", {}) or {}

                result_msg = ""
                result_success = True
                if hasattr(step_log, "observations") and step_log.observations:
                    obs = step_log.observations
                    result_msg = obs if isinstance(obs, str) else str(obs)
                    result_success = not result_msg.startswith("[FAILED]")

                # Take screenshot (retry once if page is mid-navigation)
                try:
                    raw = browser.take_screenshot()
                except Exception:
                    time.sleep(1.5)
                    raw = browser.take_screenshot()
                path = screenshot_mgr.save(raw, step=step_num, label=tool_name)
                pil_img = screenshot_mgr.to_pil(raw)
                step_log.observations_images = [pil_img]

                model_output = ""
                if hasattr(step_log, "model_output") and step_log.model_output:
                    model_output = str(step_log.model_output)[:500]

                record = StepRecord(
                    step=step_num,
                    timestamp=datetime.now().isoformat(),
                    tool_name=tool_name,
                    tool_args=tool_args,
                    result_success=result_success,
                    result_message=result_msg,
                    screenshot_path=str(path.relative_to(session.root_dir)),
                    url_at_step=browser.current_url(),
                    model_output=model_output,
                )
                session.record_step(record)

                if verbose:
                    status = "OK" if result_success else "FAIL"
                    print(f"  Step {step_num:02d} [{status}] [{tool_name}] {result_msg[:80]}")

            tools = create_browser_tools(browser)
            model = _create_model(self.config)
            task_prompt = _build_task_prompt(
                url, instructions,
                self.config.viewport_width,
                self.config.viewport_height,
            )

            agent = CodeAgent(
                tools=tools,
                model=model,
                max_steps=self.config.max_steps,
                step_callbacks=[screenshot_callback],
                verbosity_level=2 if verbose else 0,
            )

            raw_result = agent.run(task_prompt, images=[initial_image])

            # Parse status from final_answer result
            result_str = str(raw_result) if raw_result is not None else ""
            if result_str.upper().startswith("PASS"):
                status = "pass"
            elif result_str.upper().startswith("FAIL"):
                status = "fail"
            else:
                status = "incomplete"

        except Exception as exc:
            status = "error"
            result_str = f"Unexpected error: {exc}"
            session.log_error(traceback.format_exc())
        finally:
            browser.stop()

        session.close(status=status, final_message=result_str)

        reporter = Reporter(session)
        reporter.generate(
            status=status,
            final_message=result_str,
            url=url,
            instructions=instructions,
            model_provider=self.config.model_provider,
            model_name=self.config.model_name,
        )

        return TestResult(
            status=status,
            final_message=result_str,
            session_dir=session.root_dir,
            steps_taken=len(session.steps),
            report_json=session.report_json,
            report_md=session.report_md,
            duration_seconds=session.duration_seconds,
        )
