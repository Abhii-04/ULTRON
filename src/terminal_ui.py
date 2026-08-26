from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text


@dataclass(frozen=True)
class RunSummary:
    route: str
    latency_seconds: float


class TerminalUI:
    def __init__(self) -> None:
        self.console = Console()

    def show_boot(self) -> None:
        self.console.clear()
        title = Text("ULTRON", style="bold cyan")
        title.append(" // TERMINAL INTELLIGENCE", style="dim cyan")
        subtitle = Text(
            "LinkedIn | Gmail | Internet | Files | Assistant",
            style="bright_black",
        )
        body = Table.grid(padding=(0, 2))
        body.add_column(justify="center")
        body.add_row(title)
        body.add_row(subtitle)
        body.add_row(Text("Type 'exit' or 'quit' to shutdown.", style="dim"))

        self.console.print(
            Panel(
                Align.center(body),
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def show_ready(self) -> None:
        modules = Table.grid(expand=True)
        modules.add_column(ratio=1)
        modules.add_column(ratio=1)
        modules.add_column(ratio=1)
        modules.add_column(ratio=1)
        modules.add_row(
            Text("CORE ONLINE", style="bold green"),
            Text("LINKEDIN MCP", style="cyan"),
            Text("GMAIL LINK", style="cyan"),
            Text("WEB SCAN", style="cyan"),
        )
        self.console.print(Panel(modules, border_style="green", padding=(0, 1)))
        self.console.print(Text("Awaiting command input.", style="dim"))

    def ask(self) -> str:
        return Prompt.ask("[bold cyan]COMMAND[/bold cyan]").strip()

    def thinking(self):
        return self.console.status(
            "[bold cyan]processing command through agent graph[/bold cyan]",
            spinner="dots",
        )

    def show_idle_line(self) -> None:
        self.console.print()

    def show_response(self, content: Any, summary: RunSummary) -> None:
        route_label = summary.route.upper() if summary.route else "DIRECT"
        header = Table.grid(expand=True)
        header.add_column(ratio=1)
        header.add_column(justify="right")
        header.add_row(
            Text(f"RESPONSE // {route_label}", style="bold cyan"),
            Text(f"{summary.latency_seconds:.2f}s", style="bright_black"),
        )

        self.console.print(Panel(header, border_style="cyan", padding=(0, 1)))
        self.console.print(
            Panel(
                Markdown(str(content)),
                border_style="bright_black",
                padding=(1, 2),
            )
        )

    def show_error(self, error: Exception) -> None:
        self.console.print(
            Panel(
                Text(f"{type(error).__name__}: {error}", style="bold red"),
                title="FAULT",
                border_style="red",
                padding=(1, 2),
            )
        )

    def show_shutdown(self) -> None:
        self.console.print(
            Panel(
                Align.center(Text("SESSION TERMINATED", style="bold cyan")),
                border_style="cyan",
                padding=(1, 2),
            )
        )

    async def run_agent_turn(self, agent: Any, command: str) -> None:
        started = perf_counter()
        with self.thinking():
            result = await agent.run_superstep(command, [], emit_output=False)

        final_message = result["messages"][-1]
        route = str(result.get("next") or "")
        elapsed = perf_counter() - started
        self.show_response(
            final_message.content,
            RunSummary(route=route, latency_seconds=elapsed),
        )
        self.show_idle_line()
