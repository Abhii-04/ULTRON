import subprocess
from langchain_core.tools import tool



class PlaywrightSessionManager:
    """Keep playwright stdio session open across tool calls."""

    def __init__(self, session="agent"):
        self.session = session

    def _cli(self, *args):
        result = subprocess.run(
            ["playwright-cli", f"-s={self.session}", *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        return result.stdout

    def open(self, url, persistent=True, headed=True, browser="chrome"):
        args = ["open", url]
        if browser:
            args.extend(["--browser", browser])
        if headed:
            args.append("--headed")
        if persistent:
            args.append("--persistent")
        return self._cli(*args)

    def snapshot(self):
        return self._cli("snapshot")

    def goto(self, url):
        return self._cli("goto", url)

    def click(self, ref):
        return self._cli("click", ref)

    def fill(self, ref, text):
        return self._cli("fill", ref, text)

    def press(self, key):
        return self._cli("press", key)

    def close(self):
        return self._cli("close")


playwright_session = PlaywrightSessionManager()


@tool
def browser_open(
    url: str,
    persistent: bool = True,
    headed: bool = True,
    browser: str = "chrome",
) -> str:
    """Open a visible browser session at the provided URL."""
    return playwright_session.open(
        url,
        persistent=persistent,
        headed=headed,
        browser=browser,
    )


@tool
def browser_snapshot() -> str:
    """Capture an accessibility snapshot of the current browser page."""
    return playwright_session.snapshot()


@tool
def browser_goto(url: str) -> str:
    """Navigate the active browser session to a URL."""
    return playwright_session.goto(url)


@tool
def browser_click(ref: str) -> str:
    """Click an element using a ref from browser_snapshot."""
    return playwright_session.click(ref)


@tool
def browser_fill(ref: str, text: str) -> str:
    """Fill an element using a ref from browser_snapshot."""
    return playwright_session.fill(ref, text)


@tool
def browser_press(key: str) -> str:
    """Press a keyboard key in the active browser session."""
    return playwright_session.press(key)


@tool
def browser_close() -> str:
    """Close the active browser session."""
    return playwright_session.close()


playwright_tools = [
    browser_open,
    browser_snapshot,
    browser_goto,
    browser_click,
    browser_fill,
    browser_press,
    browser_close,
]
