class WebTesterError(Exception):
    """Base exception for all web_tester errors."""


class BrowserError(WebTesterError):
    """Raised when a browser action fails unrecoverably."""


class ConfigError(WebTesterError):
    """Raised when required configuration is missing or invalid."""


class SessionError(WebTesterError):
    """Raised when the test session folder cannot be created or written."""
