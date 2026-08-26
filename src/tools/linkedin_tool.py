from contextlib import AsyncExitStack

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools as load_session_mcp_tools
from langgraph.prebuilt import ToolNode


LINKEDIN_JOB_TOOL_NAMES = {
    "search_jobs",
    "get_job_details",
    "get_saved_jobs",
    "search_companies",
    "get_company_profile",
    "get_company_employees",
    "search_posts",
}
junk_phrases = [
    "Premium members are",
    "Get ahead with exclusive access",
    "millions of other members use Premium",
    "Get 50% Off Sales Nav",
    "Cancel anytime",
    "No hidden fees",
    "Looking for talent?",
    "Post a job",
]


LINKEDIN_MCP_SERVER_CONFIG = {
    "mcp-server-linkedin": {
        "command": "bash",
        "args": [
            "-lc",
            "Xvfb :99 -screen 0 1280x720x24 >/tmp/linkedin-mcp-xvfb.log 2>&1 & xvfb_pid=$!; trap 'kill \"$xvfb_pid\" 2>/dev/null' EXIT TERM INT; export DISPLAY=:99; uvx mcp-server-linkedin@latest --log-level ERROR --daemon 2>/tmp/linkedin-mcp-server.log",
        ],
        "env": {
            "FASTMCP_SHOW_SERVER_BANNER": "false",
            "UV_HTTP_TIMEOUT": "300",
        },
        "transport": "stdio",
    }
}


async def get_tools():
    client = MultiServerMCPClient(LINKEDIN_MCP_SERVER_CONFIG)
    tools = await client.get_tools()
    return tools


def filter_mcp_tools(tools):
    """expose only the mcp tools ultron need"""
    filtered_tools = [
        tool for tool in tools
        if tool.name in LINKEDIN_JOB_TOOL_NAMES
    ]
    wrapped_tools = ToolNode(filtered_tools)
    return wrapped_tools


def filter_linkedin_tools(tools):
    """return only the linkedin mcp tools ultron needs"""
    return [
        tool for tool in tools
        if getattr(tool, "name", None) in LINKEDIN_JOB_TOOL_NAMES
    ]


class LinkedinToolSessionManager:
    """Keep the linkedin mcp session open while tools are in use."""

    def __init__(self):
        self.client = MultiServerMCPClient(LINKEDIN_MCP_SERVER_CONFIG)
        self.exit_stack = AsyncExitStack()
        self.tools = []

    async def start(self):
        session = await self.exit_stack.enter_async_context(
            self.client.session("mcp-server-linkedin")
        )
        tools = await load_session_mcp_tools(
            session,
            server_name="mcp-server-linkedin",
        )
        self.tools = filter_linkedin_tools(tools)
        return self.tools

    async def close(self):
        await self.exit_stack.aclose()


def filter_tools_content(content: str):
    """filter the content recived from the tools """
    lines = content.splitlines()
    filtered_lines = [
        line for line in lines
        if not any(junk in line for junk in junk_phrases)
    ]

    return "\n".join(filtered_lines)
