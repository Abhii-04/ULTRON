import os
import asyncio
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import tool
from solari_browser import Solari
from solari_desktop import DesktopClient
from solari_sandbox import SandboxClient

load_dotenv(override=True)


def _solari_api_key() -> str:
    api_key = os.getenv("SOLARI_API_KEY")
    if not api_key:
        raise RuntimeError("SOLARI_API_KEY not found")
    return api_key


@tool
async def solari_open_headed_browser(
    url: str = "https://example.com",
    browser_app: str = "google-chrome",
    resolution: str = "1280x720",
    timeout_minutes: int = 10,
) -> dict[str, Any]:
    """Open a visible browser inside Solari Desktop and return the live stream URL."""
    timeout_minutes = max(1, min(timeout_minutes, 60))
    desktop = None

    async with DesktopClient(
        api_key=_solari_api_key(),
        base_url="https://api.getsolari.com",
    ) as client:
        desktop = await client.create(
            template="default",
            resolution=resolution,
            timeout_ms=timeout_minutes * 60_000,
        )
        try:
            await desktop.connect()

            ready = False
            for _ in range(30):
                health = await desktop.health()
                if getattr(health, "ready", False):
                    ready = True
                    break
                await asyncio.sleep(1)

            if not ready:
                raise RuntimeError("Solari desktop did not become ready")

            pid = await desktop.open(browser_app, args=[url])
            await desktop.close()

            return {
                "status": "visible_desktop_browser_opened",
                "headless": False,
                "session_id": desktop.sessionId,
                "stream_url": desktop.streamUrl,
                "browser_app": browser_app,
                "url": url,
                "pid": pid,
                "timeout_minutes": timeout_minutes,
                "message": "Open stream_url to watch and interact with the headed browser.",
            }
        except Exception:
            if desktop is not None:
                await client.destroy(desktop.sessionId)
            raise


@tool
async def solari_open_page(url: str) -> dict[str, Any]:
    """Open a URL in a headless Solari cloud browser and return page metadata."""
    async with Solari(api_key=_solari_api_key()) as solari:
        async with await solari.launch(
            stealth=False,
            # proxy="us",
            recording=False,
        ) as browser:
            page = await browser.new_page()
            await page.goto(url)
            return {
                "url": url,
                "title": await page.title(),
                "headless": True,
            }


@tool
async def solari_run_sandbox_command(
    command: str,
    command_args: list[str] | None = None,
) -> dict[str, Any]:
    """Run a command in a disposable Solari sandbox and return the command result."""
    async with SandboxClient(
        api_key=_solari_api_key(),
        base_url="https://api.getsolari.com",
    ) as client:
        sbx = await client.create(template="base")
        try:
            await sbx.connect()
            result = await sbx.commands.run(command, args=command_args or [])
            return {
                "command": command,
                "args": command_args or [],
                "stdout": getattr(result, "stdout", ""),
                "stderr": getattr(result, "stderr", ""),
                "exit_code": getattr(result, "exit_code", None),
            }
        finally:
            await sbx.kill()


solari_tools = [
    solari_open_headed_browser,
    solari_open_page,
    solari_run_sandbox_command,
]
