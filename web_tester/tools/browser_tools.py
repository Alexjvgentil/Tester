from __future__ import annotations

from typing import Optional

from smolagents import Tool

from web_tester.browser.controller import BrowserController


def _fmt(result) -> str:
    status = "OK" if result.success else "FAILED"
    msg = f"[{status}] {result.message}"
    if result.error:
        msg += f" | Error: {result.error}"
    if result.current_url:
        msg += f" | URL: {result.current_url}"
    return msg


class NavigateTool(Tool):
    name = "navigate"
    description = (
        "Navigate the browser to a URL. Always use the full URL including the scheme "
        "(e.g. https://example.com). Waits for the page to finish loading."
    )
    inputs = {
        "url": {"type": "string", "description": "Full URL to navigate to, including https://"}
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, url: str) -> str:
        return _fmt(self.browser.navigate(url))


class ClickTool(Tool):
    name = "click"
    description = (
        "Click at a specific pixel position (x, y) on the current page. "
        "The origin (0, 0) is the top-left corner of the browser viewport. "
        "Use the screenshot to identify the coordinates of the element you want to click."
    )
    inputs = {
        "x": {"type": "integer", "description": "Horizontal pixel coordinate (distance from left edge)"},
        "y": {"type": "integer", "description": "Vertical pixel coordinate (distance from top edge)"},
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, x: int, y: int) -> str:
        return _fmt(self.browser.click(x, y))


class TypeTextTool(Tool):
    name = "type_text"
    description = (
        "Type text into the currently focused element, or into a specific element by CSS selector. "
        "If no selector is given, text is typed at the current cursor position. "
        "By default clears the field first."
    )
    inputs = {
        "text": {"type": "string", "description": "Text to type"},
        "selector": {
            "type": "string",
            "description": "Optional CSS selector of the input element to target",
            "nullable": True,
        },
        "clear_first": {
            "type": "boolean",
            "description": "Whether to clear the field before typing (default: true)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, text: str, selector: Optional[str] = None, clear_first: bool = True) -> str:
        return _fmt(self.browser.type_text(text, selector=selector, clear_first=clear_first))


class PressKeyTool(Tool):
    name = "press_key"
    description = (
        "Press a keyboard key. Common keys: Enter, Tab, Escape, Space, Backspace, "
        "ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Home, End, PageUp, PageDown."
    )
    inputs = {
        "key": {"type": "string", "description": "Key name (e.g. 'Enter', 'Tab', 'Escape', 'ArrowDown')"}
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, key: str) -> str:
        return _fmt(self.browser.press_key(key))


class ScrollTool(Tool):
    name = "scroll"
    description = (
        "Scroll the page at a given position. delta_y > 0 scrolls down, delta_y < 0 scrolls up. "
        "delta_x > 0 scrolls right, delta_x < 0 scrolls left. "
        "Position (x, y) determines where the scroll event is triggered."
    )
    inputs = {
        "x": {"type": "integer", "description": "X coordinate where the scroll event is triggered"},
        "y": {"type": "integer", "description": "Y coordinate where the scroll event is triggered"},
        "delta_x": {"type": "integer", "description": "Horizontal scroll amount in pixels"},
        "delta_y": {"type": "integer", "description": "Vertical scroll amount in pixels (positive = down)"},
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, x: int, y: int, delta_x: int, delta_y: int) -> str:
        return _fmt(self.browser.scroll(x, y, delta_x, delta_y))


class HoverTool(Tool):
    name = "hover"
    description = (
        "Move the mouse cursor to a specific pixel position to trigger hover effects "
        "such as dropdown menus, tooltips, or hover states."
    )
    inputs = {
        "x": {"type": "integer", "description": "Horizontal pixel coordinate"},
        "y": {"type": "integer", "description": "Vertical pixel coordinate"},
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, x: int, y: int) -> str:
        return _fmt(self.browser.hover(x, y))


class SelectOptionTool(Tool):
    name = "select_option"
    description = (
        "Select an option from a <select> dropdown element identified by a CSS selector. "
        "The value should match the option's value attribute or visible text."
    )
    inputs = {
        "selector": {"type": "string", "description": "CSS selector for the <select> element"},
        "value": {"type": "string", "description": "Value or label of the option to select"},
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, selector: str, value: str) -> str:
        return _fmt(self.browser.select_option(selector, value))


class WaitTool(Tool):
    name = "wait"
    description = (
        "Pause execution for a number of milliseconds. "
        "Use this to wait for animations, page transitions, or dynamic content to load."
    )
    inputs = {
        "milliseconds": {
            "type": "integer",
            "description": "Duration to wait in milliseconds (e.g. 1000 = 1 second)",
        }
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, milliseconds: int) -> str:
        return _fmt(self.browser.wait(milliseconds))


class WaitForSelectorTool(Tool):
    name = "wait_for_selector"
    description = (
        "Wait until a CSS selector becomes visible on the page. "
        "Useful after navigating or triggering actions that load dynamic content."
    )
    inputs = {
        "selector": {"type": "string", "description": "CSS selector to wait for"},
        "timeout_ms": {
            "type": "integer",
            "description": "Maximum time to wait in milliseconds (default: 10000)",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self, selector: str, timeout_ms: int = 10_000) -> str:
        return _fmt(self.browser.wait_for_selector(selector, timeout_ms))


class GoBackTool(Tool):
    name = "go_back"
    description = "Navigate the browser back to the previous page in history."
    inputs = {}
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self) -> str:
        return _fmt(self.browser.go_back())


class GoForwardTool(Tool):
    name = "go_forward"
    description = "Navigate the browser forward to the next page in history."
    inputs = {}
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self) -> str:
        return _fmt(self.browser.go_forward())


class ReloadTool(Tool):
    name = "reload"
    description = "Reload the current page."
    inputs = {}
    output_type = "string"

    def __init__(self, browser: BrowserController) -> None:
        self.browser = browser
        super().__init__()

    def forward(self) -> str:
        return _fmt(self.browser.reload())


def create_browser_tools(browser: BrowserController) -> list[Tool]:
    """Instantiate all browser tools bound to the given BrowserController."""
    return [
        NavigateTool(browser),
        ClickTool(browser),
        TypeTextTool(browser),
        PressKeyTool(browser),
        ScrollTool(browser),
        HoverTool(browser),
        SelectOptionTool(browser),
        WaitTool(browser),
        WaitForSelectorTool(browser),
        GoBackTool(browser),
        GoForwardTool(browser),
        ReloadTool(browser),
    ]
