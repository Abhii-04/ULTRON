import json
from contextlib import AsyncExitStack
from copy import deepcopy
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools as load_session_mcp_tools


MCP_CONFIG_PATH = Path(__file__).resolve().parents[2] / "mcp_config.json"

LINKEDIN_JOB_TOOL_NAMES = {
    "search_jobs",
    "get_job_details",
    "get_saved_jobs",
    "search_companies",
    "get_company_profile",
    "search_posts",
}


def load_mcp_server_config(config_path: Path = MCP_CONFIG_PATH) -> dict[str, dict[str, Any]]:
    """Load MCP config and normalize it for LangChain."""
    if not config_path.exists():
        return {}

    raw_config = json.loads(config_path.read_text())
    servers = raw_config.get("mcpServers", raw_config)

    normalized_servers = {}
    for server_name, server_config in servers.items():
        normalized_config = deepcopy(server_config)

        if "transport" not in normalized_config:
            normalized_config["transport"] = (
                "stdio" if "command" in normalized_config else "http"
            )

        normalized_servers[server_name] = normalized_config

    return normalized_servers


async def load_mcp_tools(config_path: Path = MCP_CONFIG_PATH):
    server_config = load_mcp_server_config(config_path)
    if not server_config:
        return []

    client = MultiServerMCPClient(server_config)
    return await client.get_tools()


def filter_mcp_tools_for_ultron(tools):
    """Expose only the MCP tools ULTRON needs for the current workflow."""
    return [
        tool
        for tool in tools
        if getattr(tool, "name", None) in LINKEDIN_JOB_TOOL_NAMES
    ]

class MCPToolSessionManager:
    """Keep MCP stdio sessions open so browser-backed tools do not relaunch."""

    def __init__(self, config_path: Path = MCP_CONFIG_PATH):
        self.config_path = config_path
        self.client = None
        self.exit_stack = AsyncExitStack()
        self.tools = []

    async def start(self):
        server_config = load_mcp_server_config(self.config_path)
        if not server_config:
            self.tools = []
            return self.tools

        self.client = MultiServerMCPClient(server_config)
        tools = []

        for server_name in server_config:
            session = await self.exit_stack.enter_async_context(
                self.client.session(server_name)
            )
            server_tools = await load_session_mcp_tools(
                session,
                server_name=server_name,
            )
            tools.extend(filter_mcp_tools_for_ultron(server_tools))

        self.tools = tools
        return self.tools

    async def close(self):
        await self.exit_stack.aclose()
