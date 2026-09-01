import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from src.config.state import State

#Agents imports
from src.subgraphs.gmail_agent import Gmail_agent
from src.subgraphs.internet_agent import InternetAgent
from src.subgraphs.linkedin_agent import LinkedinAgent

#Tools imports
from src.tools.fileManagment import create_file, delete_file, read_file, write_file


#Nodes imports
from src.nodes.dynamic_prompt import prompt_modifier
from src.nodes.dynamic_agent_selection import dynamic_agent_selection
from src.nodes.context_trimming import context_trimming_node
from src.middlewares.context_handoff import create_task_instructions_handoff_tool
from src.middlewares.HITL import add_approval_to_risky_tools, ask_question, halt_on_risky_tools

from src.config.memory import memory

load_dotenv(override=True)

llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
)

DIRECT_CHAT_HISTORY_LIMIT = 6
MEMORY_TOP_K = 3
MAX_MEMORY_ITEM_CHARS = 180

FILE_ACTION_WORDS = {
    "read",
    "write",
    "create",
    "delete",
    "edit",
    "update",
    "save",
}

FILE_TARGET_WORDS = {
    "file",
    "folder",
    "directory",
    "path",
    ".txt",
    ".md",
    ".py",
    ".json",
}

SERVICE_INTENT_WORDS = {
    "gmail",
    "email",
    "inbox",
    "draft",
    "linkedin",
    "job",
    "profile",
    "web",
    "internet",
    "search",
    "latest",
    "current",
    "recent",
    "url",
    "http",
    "https",
    "browser",
    "open",
    "website",
    "webpage",
    "site",
    "navigate",
    "click",
    "inspect",
}

CASUAL_CHAT_WORDS = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "cool",
    "great",
}


def _message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    return content if isinstance(content, str) else str(content)


def _latest_human_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return _message_text(message)
    return _message_text(messages[-1]) if messages else ""


def _looks_like_tool_request(text: str) -> bool:
    lowered = text.lower()
    has_file_action = any(word in lowered for word in FILE_ACTION_WORDS)
    has_file_target = any(word in lowered for word in FILE_TARGET_WORDS)
    return (has_file_action and has_file_target) or any(word in lowered for word in SERVICE_INTENT_WORDS)


def _looks_casual(text: str) -> bool:
    lowered = text.strip().lower()
    return len(lowered.split()) <= 5 and any(word == lowered or word in lowered for word in CASUAL_CHAT_WORDS)


def _recent_chat_messages(messages: list[Any]) -> list[Any]:
    return messages[-DIRECT_CHAT_HISTORY_LIMIT:]


def _format_memory_context(memory_list: list[dict[str, Any]]) -> str:
    memory_lines = []
    for item in memory_list:
        memory_text = item.get("memory")
        if not memory_text:
            continue
        memory_lines.append(f"- {str(memory_text)[:MAX_MEMORY_ITEM_CHARS]}")
    return "\n".join(memory_lines)


def _load_memory_context(user_text: str, user_id: str) -> str:
    try:
        memories = memory.search(user_text, filters={"user_id": user_id}, top_k=MEMORY_TOP_K)
        return _format_memory_context(memories.get("results", []))
    except Exception as e:
        print(f"Error retrieving memory: {type(e).__name__}:{e}")
        return ""


def _save_memory(user_text: str, assistant_text: str, user_id: str) -> None:
    if _looks_casual(user_text):
        return

    try:
        interaction = [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]
        result = memory.add(interaction, user_id=user_id)
        print(f"memory saved:{len(result.get('results', []))} memories added")
    except Exception as e:
        print(f"Error saving memory: {type(e).__name__}:{e}")


def handle_file_tool_error(error: Exception) -> str:
    """Return file tool failures to the model instead of crashing the graph."""
    return f"File tool call failed: {type(error).__name__}: {error}"

class Agent:
    def __init__(self):
        self.internet_graph = None
        self.gmail_graph = None
        self.linkedin_graph = None
        self.graph = None
        self.agent_id = None
        self.checkpointer = None
        self.store = None
        self.internet_agent = None
        self.gmail_agent = None
        self.linkedin_agent = None
        self.orchestrator_agent = None
        self.file_tools = []
        self.handoff_tools = []

    async def setup(self):
        file_tools = [create_file, read_file, write_file, delete_file, ask_question]
        self.file_tools = add_approval_to_risky_tools(file_tools)
        self.handoff_tools = [
            create_task_instructions_handoff_tool(
                agent_name="gmail",
                description="Transfer Gmail, email, inbox search, or draft tasks to the Gmail agent.",
            ),
            create_task_instructions_handoff_tool(
                agent_name="linkedin",
                description="Transfer LinkedIn job, company, profile, saved job, or hiring post tasks to the LinkedIn agent.",
            ),
            create_task_instructions_handoff_tool(
                agent_name="internet",
                description="Transfer current, recent, web search, URL, website browsing, browser navigation, or source-backed research tasks to the Internet agent.",
            ),
        ]
        self.orchestrator_agent = llm.bind_tools(self.file_tools + self.handoff_tools)
        internet = InternetAgent()
        internet.setup()
        await internet.build_graph()
        self.internet_graph = internet.graph
        self.internet_agent = internet

        gmail = Gmail_agent()
        await gmail.build_graph()
        self.gmail_graph = gmail.graph
        self.gmail_agent = gmail

        linkedin = LinkedinAgent()
        await linkedin.build_graph()
        self.linkedin_graph = linkedin.graph
        self.linkedin_agent = linkedin

        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()
        await self.build_graph()

    def orchestrator(self, state: State, store: BaseStore) -> dict[str, Any]:
        messages = state["messages"]
        user_id = state["user_id"]
        user_text = _latest_human_text(messages)
        last_message = messages[-1]
        use_tools = isinstance(last_message, (AIMessage, ToolMessage)) or _looks_like_tool_request(user_text)
        use_memory = not _looks_casual(user_text)
        memory_context = _load_memory_context(user_text, user_id) if use_memory else ""

        if not use_tools:
            system_prompt = "You are ULTRON. Answer directly and keep casual replies concise."
            if memory_context:
                system_prompt = f"{system_prompt}\n\nRelevant long term user memories:\n{memory_context}"
            system_message = SystemMessage(
                content=system_prompt
            )
            response = llm.invoke([system_message, *_recent_chat_messages(messages)])
            _save_memory(user_text, response.content, user_id)
            return {"messages": [response]}

        system_prompt = prompt_modifier(state)
        if memory_context:
            system_prompt = f"{system_prompt}\n\nRelevant long term user memories:\n{memory_context}"

        system_message = SystemMessage(content=system_prompt)

        response = self.orchestrator_agent.invoke([system_message, *messages])

        if getattr(response, "tool_calls", None):
            return {"messages": [response], "next": "orchestrator_tools"}

        if isinstance(messages[-1], ToolMessage):
            return {"messages": [response], "next": END}

        _save_memory(user_text, response.content, user_id)
        return {"messages":[response]}

    def orchestrator_router(self, state: State):
        route = state.get("next")
        if route == "orchestrator_tools":
            return route
        if route in {"gmail", "linkedin", "internet"}:
            return route
        return END

    async def build_graph(self):
        graph_builder = StateGraph(State)
        graph_builder.add_node("agent", self.orchestrator)
        graph_builder.add_node("context_trim_after_agent", context_trimming_node)
        graph_builder.add_node("context_trim_after_tools", context_trimming_node)
        graph_builder.add_node("toolcall", halt_on_risky_tools)
        graph_builder.add_node(
            "orchestrator_tools",
            ToolNode(self.file_tools + self.handoff_tools, handle_tool_errors=handle_file_tool_error),
        )
        graph_builder.add_node("internet", self.internet_graph)
        graph_builder.add_node("gmail", self.gmail_graph)
        graph_builder.add_node("linkedin", self.linkedin_graph)

        graph_builder.add_conditional_edges(
            START,
            dynamic_agent_selection,
            {
                "linkedin": "linkedin",
                "internet": "internet",
                "orchestrator": "agent",
            }
        )
        graph_builder.add_conditional_edges(
            "context_trim_after_agent",
            self.orchestrator_router,
            {
                "gmail": "gmail",
                "linkedin": "linkedin",
                "internet": "internet",
                "orchestrator_tools": "toolcall",
                END: END,
            },
        )
        graph_builder.add_edge("agent", "context_trim_after_agent")
        graph_builder.add_conditional_edges(
            "toolcall",
            lambda state: "orchestrator_tools" if state.get("hitl_decision") == "approved" else END,
            {
                "orchestrator_tools": "orchestrator_tools",
                END: END,
            },
        )
        graph_builder.add_edge("orchestrator_tools", "context_trim_after_tools")
        graph_builder.add_edge("context_trim_after_tools", "agent")
        graph_builder.add_edge("internet", END)
        graph_builder.add_edge("gmail", END)
        graph_builder.add_edge("linkedin", END)

        self.graph = graph_builder.compile(
            checkpointer=self.checkpointer,
            store=self.store,
        )

    async def close(self):
        if self.internet_agent is not None:
            await self.internet_agent.close()
        if self.linkedin_agent is not None:
            await self.linkedin_agent.close()

    async def run_superstep(self, message, history, user_id: str = "default", emit_output: bool = True):
        config = {"configurable": {"thread_id": self.agent_id}}
        if isinstance(message, Command):
            state = message
        else:
            state = {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "task_instructions": "",
            }

        result = await self.graph.ainvoke(state, config=config)

        if "__interrupt__" in result:
            if emit_output:
                print(result["__interrupt__"][-1].value)
            return result

        if emit_output:
            print(result["messages"][-1].content)
        return result
