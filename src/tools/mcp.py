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
    "get_company_employees",
    "search_posts",
}

LINKEDIN_MAX_JOBS = 20
LINKEDIN_JOB_TEXT_LIMIT = 80


def load_mcp_server_config(
    config_path: Path = MCP_CONFIG_PATH,
) -> dict[str, dict[str, Any]]:
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
                "stdio"
                if "command" in normalized_config
                else "http"
            )

        normalized_servers[server_name] = normalized_config

    return normalized_servers


async def load_mcp_tools(config_path: Path = MCP_CONFIG_PATH):
    server_config = load_mcp_server_config(config_path)

    if not server_config:
        return []

    client = MultiServerMCPClient(server_config)

    return await client.get_tools()


def truncate_linkedin_job_text(value: Any) -> str:
    """Limit each LinkedIn job summary before it reaches the LLM."""

    text = str(value or "")
    if len(text) <= LINKEDIN_JOB_TEXT_LIMIT:
        return text
    return text[:LINKEDIN_JOB_TEXT_LIMIT].rstrip()


def compact_linkedin_job(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        return {
            "job": truncate_linkedin_job_text(item),
        }

    title = item.get("text") or item.get("title") or ""
    url = item.get("url") or item.get("apply_link") or item.get("job_url") or ""
    summary = " | ".join(
        str(part)
        for part in (title, url)
        if part
    )

    return {
        "job": truncate_linkedin_job_text(summary),
    }


def trim_linkedin_search_output(result: Any) -> Any:
    """
    Reduce LinkedIn search output before it reaches the LLM.
    """

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            return truncate_linkedin_job_text(result)

    if isinstance(result, list):
        jobs = []
        for item in result:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    parsed_text = json.loads(item.get("text", ""))
                except json.JSONDecodeError:
                    jobs.append(compact_linkedin_job(item.get("text", "")))
                else:
                    trimmed_text = trim_linkedin_search_output(parsed_text)
                    if isinstance(trimmed_text, dict) and "jobs" in trimmed_text:
                        jobs.extend(trimmed_text["jobs"])
                    else:
                        jobs.append(compact_linkedin_job(trimmed_text))
            else:
                jobs.append(compact_linkedin_job(item))

            if len(jobs) >= LINKEDIN_MAX_JOBS:
                break

        return {"jobs": jobs}

    if not isinstance(result, dict):
        return result

    trimmed = {}

    if "job_ids" in result:
        trimmed["job_ids"] = result["job_ids"][:LINKEDIN_MAX_JOBS]

    direct_jobs = result.get("jobs")
    if isinstance(direct_jobs, list):
        trimmed["jobs"] = [
            compact_linkedin_job(item)
            for item in direct_jobs[:LINKEDIN_MAX_JOBS]
        ]
        return trimmed

    references = result.get("references", {})
    search_results = references.get("search_results", [])

    jobs = []

    for item in search_results:
        if item.get("kind") != "job":
            continue

        jobs.append(compact_linkedin_job(item))

        if len(jobs) >= LINKEDIN_MAX_JOBS:
            break

    if jobs:
        trimmed["jobs"] = jobs

    return trimmed


def wrap_mcp_tool(tool):
    """
    Wrap selected MCP tools so their output can be normalized.
    """

    if tool.name not in {"search_jobs", "get_saved_jobs"}:
        return tool

    async def wrapped_linkedin_jobs(**kwargs):
        result = await tool.ainvoke(kwargs)
        return trim_linkedin_search_output(result)

    return StructuredTool.from_function(
        coroutine=wrapped_linkedin_jobs,
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
    )


def filter_mcp_tools_for_ultron(tools):
    """Expose only the MCP tools ULTRON needs."""

    filtered_tools = [
        tool
        for tool in tools
        if getattr(tool, "name", None) in LINKEDIN_JOB_TOOL_NAMES
    ]

    return [
        wrap_mcp_tool(tool)
        for tool in filtered_tools
    ]

class MCPToolSessionManager:
    """Keep MCP stdio sessions open across tool calls."""

    def __init__(
        self,
        config_path: Path = MCP_CONFIG_PATH,
    ):
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

            tools.extend(
                filter_mcp_tools_for_ultron(server_tools)
            )

        self.tools = tools

        return self.tools

    async def close(self):
        await self.exit_stack.aclose()
