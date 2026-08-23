import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.state import State
from src.tools.mcp import MCPToolSessionManager
from src.tools.read_skill import read_skill

load_dotenv(override=True)


def handle_tool_error(error: Exception) -> str:
    """Return LinkedIn MCP tool failures to the model instead of crashing."""
    return f"LinkedIn MCP tool call failed: {type(error).__name__}: {error}"


def llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("api_key not found")
    return ChatOpenAI(
        api_key=api_key,
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
    )


class LinkedinAgent:
    """
    Use for:
    - LinkedIn job search
    - LinkedIn job details
    - Saved LinkedIn jobs
    - LinkedIn company search and company profiles
    - LinkedIn hiring post searches

    Do NOT use for:
    - General web research
    - Gmail or email tasks
    - Browser interaction
    - File editing
    - Shell commands
    """

    def __init__(self):
        self.linkedin_llm = None
        self.tools = []
        self.agent_id = None
        self.memory = None
        self.graph = None
        self.mcp_manager = None

    async def setup(self, _state: Any = None):
        self.memory = InMemorySaver()
        self.mcp_manager = MCPToolSessionManager()
        self.tools = await self.mcp_manager.start()
        self.tools.append(read_skill)
        self.linkedin_llm = llm().bind_tools(self.tools)

    async def close(self):
        if self.mcp_manager is not None:
            await self.mcp_manager.close()

    def linkedin_agent(self, state: State):
        system_message = f"""You are a LinkedIn job research agent.

Your work area:
- Use configured LinkedIn MCP tools for job hunting and company research.
- Search LinkedIn jobs using the MCP tool schemas directly.
- Use job IDs from search results when the user asks for job details.
- Search companies and company profiles when the user asks about employers.
- Search LinkedIn posts for hiring posts or informal opportunities.
- For every job search result, include the apply link or LinkedIn job URL when the tool result provides one.
- For every job search result, include the basic fields users need to act: title, company, location, job ID, apply/job link, posting date, work type, and experience level when available.
- If a search result does not include an apply link or job URL, say that the link was not provided instead of inventing one.
- Summarize results clearly and keep job search results easy to scan.

Boundaries:
- Do not use general internet search.
- Do not handle Gmail or email tasks.
- Do not claim to operate a browser beyond the configured LinkedIn MCP tools.
- Do not message recruiters, connect with people, apply to jobs, save jobs, or perform social/account-changing actions unless explicit tools for those actions are added later.
- If the user asks for something outside LinkedIn job/company/post research, say which workflow should handle it.
- Do not describe tool calls or tool syntax in your response text. If you need a tool, use the bound tool-calling interface only.
- If a LinkedIn MCP tool fails, explain the failure briefly and ask for any missing required input.

Skills:
- You have access to read_skill, which reads local instructions from skills/<skill>/SKILL.md.
- When the user names a skill or the task clearly matches one, call read_skill before using LinkedIn tools or answering and follow those instructions.
- If read_skill reports a missing, invalid, or empty skill, create a concise report in your response with: Error, Cause, Solution, and Next step.
- Do not invent skill instructions when the skill file cannot be read.

The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
"""

        messages = state["messages"]
        found_system_message = False

        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                found_system_message = True

        if not found_system_message:
            messages = [SystemMessage(content=system_message)] + messages

        response = self.linkedin_llm.invoke(messages)
        return {
            "messages": [response]
        }

    def linkedin_agent_router(self, state: State):
        last_message = state["messages"][-1]

        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    async def build_graph(self):
        if self.memory is None or self.linkedin_llm is None:
            await self.setup()

        graph_builder = StateGraph(State)

        graph_builder.add_node("linkedin_agent", self.linkedin_agent)
        graph_builder.add_node(
            "tools",
            ToolNode(self.tools, handle_tool_errors=handle_tool_error),
        )

        graph_builder.add_edge(START, "linkedin_agent")
        graph_builder.add_conditional_edges(
            "linkedin_agent",
            self.linkedin_agent_router,
            {
                "tools": "tools",
                END: END,
            },
        )
        graph_builder.add_edge("tools", "linkedin_agent")

        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, _history):
        config = {"configurable": {"thread_id": self.agent_id}}
        state = {
            "messages": [HumanMessage(content=message)],
        }
        result = await self.graph.ainvoke(state, config=config)
        print(result["messages"][-1].content)
        return result
