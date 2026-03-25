from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
)

from web_tester.config import Config


@dataclass
class ActionResult:
    success: bool
    message: str
    error: Optional[str] = None
    current_url: Optional[str] = None


class BrowserController:
    """
    Thread-safe Playwright wrapper.

    Playwright's async API runs in a dedicated background thread with its own
    event loop. All public methods submit coroutines to that loop via
    ``asyncio.run_coroutine_threadsafe``, so they can be called safely from
    any thread or greenlet (including smolagents CodeAgent's execution context).
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch the browser in a background thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._run(self._async_start())

    def stop(self) -> None:
        """Close the browser and stop the background loop."""
        try:
            if self._loop and self._loop.is_running():
                self._run(self._async_stop())
                self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run(self, coro, timeout: float = 20.0):
        """Submit a coroutine to the browser loop and block until done.
        Default 20s keeps us under smolagents' 30s per-step execution limit."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    async def _async_start(self) -> None:
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._config.browser_headless,
        )
        self._page = await self._browser.new_page(
            viewport={
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            }
        )

    async def _async_stop(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ok(self, message: str, url: str = "") -> ActionResult:
        return ActionResult(success=True, message=message, current_url=url or self._safe_url())

    def _fail(self, message: str, error: str) -> ActionResult:
        return ActionResult(success=False, message=message, error=error, current_url=self._safe_url())

    def _safe_url(self) -> str:
        try:
            return self._run(self._async_url(), timeout=5.0)
        except Exception:
            return ""

    async def _async_url(self) -> str:
        return self._page.url if self._page else ""

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, url: str) -> ActionResult:
        async def _go():
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            return self._page.url
        try:
            final_url = self._run(_go(), timeout=35.0)
            return self._ok(f"Navigated to {final_url}", final_url)
        except (PlaywrightTimeoutError, PlaywrightError, Exception) as e:
            return self._fail(f"Error navigating to {url}", str(e))

    def go_back(self) -> ActionResult:
        async def _back():
            await self._page.go_back(wait_until="domcontentloaded", timeout=15_000)
            return self._page.url
        try:
            url = self._run(_back())
            return self._ok(f"Went back to {url}", url)
        except Exception as e:
            return self._fail("Failed to go back", str(e))

    def go_forward(self) -> ActionResult:
        async def _fwd():
            await self._page.go_forward(wait_until="domcontentloaded", timeout=15_000)
            return self._page.url
        try:
            url = self._run(_fwd())
            return self._ok(f"Went forward to {url}", url)
        except Exception as e:
            return self._fail("Failed to go forward", str(e))

    def reload(self) -> ActionResult:
        async def _reload():
            await self._page.reload(wait_until="domcontentloaded", timeout=15_000)
            return self._page.url
        try:
            url = self._run(_reload())
            return self._ok(f"Reloaded {url}", url)
        except Exception as e:
            return self._fail("Failed to reload", str(e))

    # ------------------------------------------------------------------
    # Mouse / Keyboard
    # ------------------------------------------------------------------

    def click(self, x: int, y: int) -> ActionResult:
        async def _click():
            await self._page.mouse.click(x, y)
            await asyncio.sleep(0.3)
        try:
            self._run(_click())
            return self._ok(f"Clicked at ({x}, {y})")
        except Exception as e:
            return self._fail(f"Failed to click at ({x}, {y})", str(e))

    def type_text(self, text: str, selector: Optional[str] = None, clear_first: bool = True) -> ActionResult:
        async def _type():
            if selector:
                # Try to click the selector to focus it.
                # If it fails (e.g. wrong tag like input vs textarea), we fall
                # through and type into whatever is already focused.
                try:
                    loc = self._page.locator(selector).first
                    await loc.click(timeout=4_000)
                    await asyncio.sleep(0.2)
                except Exception:
                    pass  # element not found or not clickable — type into focused element
                if clear_first:
                    await self._page.keyboard.press("Control+a")
                    await asyncio.sleep(0.05)
                    await self._page.keyboard.press("Delete")
                    await asyncio.sleep(0.05)
            await self._page.keyboard.type(text, delay=40)
        try:
            self._run(_type(), timeout=18.0)
            target = f"selector '{selector}'" if selector else "focused element"
            return self._ok(f"Typed '{text}' into {target}")
        except Exception as e:
            return self._fail("Failed to type text", str(e))

    def press_key(self, key: str) -> ActionResult:
        async def _press():
            await self._page.keyboard.press(key)
            await asyncio.sleep(0.2)
        try:
            self._run(_press())
            return self._ok(f"Pressed key '{key}'")
        except Exception as e:
            return self._fail(f"Failed to press key '{key}'", str(e))

    def scroll(self, x: int, y: int, delta_x: int, delta_y: int) -> ActionResult:
        async def _scroll():
            await self._page.mouse.move(x, y)
            await self._page.mouse.wheel(delta_x, delta_y)
        try:
            self._run(_scroll())
            return self._ok(f"Scrolled ({delta_x}, {delta_y}) at ({x}, {y})")
        except Exception as e:
            return self._fail("Failed to scroll", str(e))

    def hover(self, x: int, y: int) -> ActionResult:
        async def _hover():
            await self._page.mouse.move(x, y)
            await asyncio.sleep(0.3)
        try:
            self._run(_hover())
            return self._ok(f"Hovered at ({x}, {y})")
        except Exception as e:
            return self._fail(f"Failed to hover at ({x}, {y})", str(e))

    def select_option(self, selector: str, value: str) -> ActionResult:
        async def _select():
            await self._page.select_option(selector, value, timeout=10_000)
        try:
            self._run(_select())
            return self._ok(f"Selected option '{value}' in '{selector}'")
        except Exception as e:
            return self._fail(f"Failed to select option in '{selector}'", str(e))

    def wait(self, milliseconds: int) -> ActionResult:
        time.sleep(milliseconds / 1000)
        return self._ok(f"Waited {milliseconds}ms")

    def wait_for_selector(self, selector: str, timeout_ms: int = 10_000) -> ActionResult:
        async def _wait():
            await self._page.wait_for_selector(selector, timeout=timeout_ms)
        try:
            self._run(_wait(), timeout=timeout_ms / 1000 + 5)
            return self._ok(f"Selector '{selector}' is visible")
        except Exception as e:
            return self._fail(f"Selector '{selector}' not found within {timeout_ms}ms", str(e))

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    def take_screenshot(self) -> bytes:
        async def _shot():
            # Wait briefly for any in-progress navigation/animations to settle
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=5_000)
            except Exception:
                pass
            return await self._page.screenshot(type="png", full_page=False)
        return self._run(_shot(), timeout=15.0)

    def current_url(self) -> str:
        return self._safe_url()

    def page_title(self) -> str:
        async def _title():
            return await self._page.title()
        try:
            return self._run(_title(), timeout=5.0)
        except Exception:
            return ""
