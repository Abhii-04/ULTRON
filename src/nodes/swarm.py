from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph_swarm import create_swarm

from src.subgraphs.assistant import Assistant
from src.subgraphs.gmail_agent import Gmail_agent
from src.subgraphs.internet_agent import InternetAgent
from src.subgraphs.linkedin_agent import LinkedinAgent


DEFAULT_ACTIVE_AGENT = "assistant"
ENABLED_AGENTS = ("assistant", "internet", "gmail", "linkedin")


async def _build_assistant_graph():
    assistant = Assistant()
    assistant.setup()
    await assistant.build_graph()
    assistant.graph.name = "assistant"
    return assistant.graph, assistant


async def _build_internet_graph():
    internet = InternetAgent()
    internet.setup()
    await internet.build_graph()
    internet.graph.name = "internet"
    return internet.graph, internet


async def _build_gmail_graph():
    gmail = Gmail_agent()
    await gmail.build_graph()
    gmail.graph.name = "gmail"
    return gmail.graph, gmail


async def _build_linkedin_graph():
    linkedin = LinkedinAgent()
    await linkedin.build_graph()
    linkedin.graph.name = "linkedin"
    return linkedin.graph, linkedin


async def build_swarm(
    *,
    checkpointer: Any | None = None,
    store: BaseStore | None = None,
    default_active_agent: str = DEFAULT_ACTIVE_AGENT,
    ):
    """Build a LangGraph swarm from this repo's existing agent subgraphs.

    The returned app routes each turn to the current ``active_agent`` in state.
    If no active agent is set, LangGraph Swarm starts with ``assistant``.
    """

    assistant_graph, assistant = await _build_assistant_graph()
    internet_graph, internet = await _build_internet_graph()
    gmail_graph, gmail = await _build_gmail_graph()
    linkedin_graph, linkedin = await _build_linkedin_graph()

    agents = [assistant_graph, internet_graph, gmail_graph, linkedin_graph]
    agent_names = {agent.name for agent in agents}
    if default_active_agent not in agent_names:
        raise ValueError(
            f"default_active_agent must be one of {sorted(agent_names)}, "
            f"got {default_active_agent!r}"
        )

    workflow = create_swarm(
        agents,
        default_active_agent=default_active_agent,
    )

    app = workflow.compile(
        checkpointer=checkpointer or InMemorySaver(),
        store=store or InMemoryStore(),
    )

    return {
        "app": app,
        "agents": {
            "assistant": assistant,
            "internet": internet,
            "gmail": gmail,
            "linkedin": linkedin,
        },
    }


async def close_swarm_agents(agents: dict[str, Any]) -> None:
    """Close swarm agents that own external sessions."""

    for agent in agents.values():
        close = getattr(agent, "close", None)
        if close is not None:
            await close()


#Usage example
# response = financial_swarm.invoke({"messages": [
   # HumanMessage(content="What are the latest NVIDIA news and developments, and what's their current stock price and market cap?")
#]}, config)
