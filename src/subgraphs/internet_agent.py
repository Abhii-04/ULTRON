import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.state import State
from src.tools.read_skill import read_skill
from src.tools.tavily import Internet_search

load_dotenv(override=True)


def handle_tool_error(error: Exception) -> str:
    """Return tool failures to the model instead of crashing the CLI."""
    return f"Tool call failed: {type(error).__name__}: {error}"


def llm():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("api_key not found")
    return ChatOpenAI(
        api_key=api_key,
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
    )


class InternetAgent:
    """Internet research workflow backed by Tavily search."""

    def __init__(self):
        self.internet_llm = None
        self.tools = None
        self.agent_id = None
        self.memory = None
        self.graph = None

    def setup(self):
        self.memory = InMemorySaver()

    async def setup_tools(self):
        self.tools = [Internet_search, read_skill]
        self.internet_llm = llm().bind_tools(self.tools)

    async def close(self):
        return None

    def internet_agent(self, state: State):
        system_message = f"""You are an internet research agent.

Your work area:
- Use the Internet_search tool for current, recent, external, or source-backed information.
- Search when facts may have changed or when the user asks for latest/current information.
- Summarize findings clearly and mention source names or URLs when the tool result provides them.
- If search results conflict, say so and prefer more authoritative or recent sources.

Boundaries:
- Do not claim to operate a browser or interact with websites beyond search results.
- Do not claim to run code or read local files.
- Do not handle Gmail or email tasks. Say that the Gmail workflow should handle them.
- Do not handle LinkedIn MCP tasks. Say that the LinkedIn workflow should handle them.
- If the task does not need internet research, answer briefly that it should be handled by the general assistant.
- If the available search results are insufficient, say what is missing instead of guessing.
- Do not describe tool calls or tool syntax in your response text. If you need a tool, use the bound tool-calling interface only.

Skills:
- You have access to read_skill, which reads local instructions from skills/<skill>/SKILL.md.
- When the user names a skill or the task clearly matches one, call read_skill before researching or answering and follow those instructions.
- If read_skill reports a missing, invalid, or empty skill, create a concise report in your response with: Error, Cause, Solution, and Next step.
- Do not invent skill instructions when the skill file cannot be read.

Loaded skill instructions:
{state.get("internet_skill", "")}

The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. """

        if state.get("feedback_on_work"):
            system_message += f"""
Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
Here is the feedback on why this was rejected:
{state["feedback_on_work"]}
With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""

        messages = state["messages"]
        for message in messages:
            if isinstance(message, SystemMessage):
                message.content = system_message
                break
        else:
            messages = [SystemMessage(content=system_message)] + messages

        response = self.internet_llm.invoke(messages)
        return {"messages": [response]}

    def load_internet_skill(self, _state: State):
        return {
            "internet_skill": read_skill.invoke({"skill": "internet_search"})
        }

    def internet_agent_router(self, state: State):
        if getattr(state["messages"][-1], "tool_calls", None):
            return "tools"
        return END

    async def build_graph(self):
        await self.setup_tools()
        graph_builder = StateGraph(State)
        graph_builder.add_node("load_internet_skill", self.load_internet_skill)
        graph_builder.add_node("internet_agent", self.internet_agent)
        graph_builder.add_node(
            "tools",
            ToolNode(self.tools, handle_tool_errors=handle_tool_error),
        )

        graph_builder.add_edge(START, "load_internet_skill")
        graph_builder.add_edge("load_internet_skill", "internet_agent")
        graph_builder.add_conditional_edges(
            "internet_agent",
            self.internet_agent_router,
            {
                "tools": "tools",
                END: END,
            },
        )
        graph_builder.add_edge("tools", "internet_agent")

        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, _history):
        config = {"configurable": {"thread_id": self.agent_id}}
        state = {"messages": [HumanMessage(content=message)]}
        result = await self.graph.ainvoke(state, config=config)
        print(result["messages"][-1].content)
        return result
