from typing import Annotated, Any, Optional, TypedDict, List
from datetime import datetime, timedelta

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

from langchain_core.messages import AIMessage, HumanMessage
from src.tools.Gmail import _compact_search_gmail, _create_gmail_draft


def _latest_human_text(messages: List[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage) and isinstance(message.content, str):
            return message.content
    return ""


def _gmail_date_query(text: str, now: Optional[datetime] = None) -> Optional[str]:
    latest_text = text.lower()
    current_time = now or datetime.now().astimezone()

    if "last 24 hour" in latest_text or "past 24 hour" in latest_text:
        return "newer_than:1d"

    if "today" in latest_text:
        start = current_time.date()
        end = start + timedelta(days=1)
        return f"after:{start:%Y/%m/%d} before:{end:%Y/%m/%d}"

    return None


def _gmail_search_query_from_text(text: str, now: Optional[datetime] = None) -> str:
    date_query = _gmail_date_query(text, now=now)
    if date_query:
        return date_query

    latest_text = text.lower()
    query = text
    for marker in ("query:", "for messages", "for emails", "for email", "for mail", "for"):
        if marker in latest_text:
            marker_index = latest_text.rfind(marker)
            query = text[marker_index + len(marker):].strip()
            break

    return query or text


def _shorten_text(value: str, limit: int = 220) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _format_gmail_search_results(results: Any) -> str:
    if not isinstance(results, list):
        return str(results)

    if not results:
        return "No emails found for that Gmail search."

    lines = [f"Found {len(results)} email(s):"]
    for index, message in enumerate(results, start=1):
        if not isinstance(message, dict):
            lines.append(f"{index}. {message}")
            continue

        subject = message.get("subject") or "(no subject)"
        sender = message.get("sender") or "(unknown sender)"
        snippet = message.get("snippet") or ""
        message_id = message.get("id")

        lines.append(f"{index}. {subject}")
        lines.append(f"   From: {sender}")
        if snippet:
            lines.append(f"   Snippet: {_shorten_text(snippet)}")
        if message_id:
            lines.append(f"   ID: {message_id}")

    return "\n".join(lines)


class GmailState(TypedDict, total=False):
    messages: Annotated[List[Any], add_messages]
    task_instructions: str
    gmail_action: str
    query: str
    message: str
    to: List[str]
    subject: str
    cc: Optional[List[str]]
    bcc: Optional[List[str]]
    gmail_result: Any


class Gmail_agent:
    def __init__(self):
        self.memory = None
        self.graph = None
        self.agent_id = None

    async def setup(self, _state: Any = None):
        self.memory = InMemorySaver()

    def search_gmail_node(self, state: GmailState):
        if not state.get("query"):
            return {"messages": [AIMessage(content="Missing required Gmail workflow input: query")]}

        result = _compact_search_gmail(query=state["query"])
        return {
            "gmail_result": result,
            "messages": [AIMessage(content=_format_gmail_search_results(result))]
        }

    def prepare_gmail_state(self, state: GmailState):
        messages = state.get("messages", [])
        latest_message = state.get("task_instructions") or _latest_human_text(messages)
        if not latest_message and state.get("gmail_action") and state.get("query"):
            return {}

        latest_text = latest_message.lower() if isinstance(latest_message, str) else ""

        if "draft" in latest_text:
            return {"gmail_action": "draft_message"}

        if "gmail" in latest_text or "email" in latest_text or "mail" in latest_text:
            return {
                "gmail_action": "search_gmail",
                "query": _gmail_search_query_from_text(latest_message),
            }

        return {"gmail_action": None, "query": None}

    def draft_message_node(self, state: GmailState):
        for field in ("message", "to", "subject"):
            if not state.get(field):
                return {"messages": [AIMessage(content=f"Missing required Gmail workflow input: {field}")]}

        tool_input = {
            "message": state["message"],
            "to": state["to"],
            "subject": state["subject"],
        }
        if state.get("cc") is not None:
            tool_input["cc"] = state["cc"]
        if state.get("bcc") is not None:
            tool_input["bcc"] = state["bcc"]

        result = _create_gmail_draft(**tool_input)
        return {
            "gmail_result": result,
            "messages": [AIMessage(content=str(result))]
        }

    def gmail_router(self, state: GmailState):
        action = state.get("gmail_action")
        if action == "search_gmail":
            return "search_gmail"
        if action == "draft_message":
            return "draft_message"
        return END

    async def build_graph(self):
        if self.memory is None:
            self.memory = InMemorySaver()

        graph_builder = StateGraph(GmailState)

        graph_builder.add_node("prepare_gmail_state", self.prepare_gmail_state)
        graph_builder.add_node("search_gmail", self.search_gmail_node)
        graph_builder.add_node("draft_message", self.draft_message_node)

        graph_builder.add_edge(START, "prepare_gmail_state")
        graph_builder.add_conditional_edges(
            "prepare_gmail_state",
            self.gmail_router,
            {
                "search_gmail": "search_gmail",
                "draft_message": "draft_message",
                END: END
            },
        )
        graph_builder.add_edge("search_gmail", END)
        graph_builder.add_edge("draft_message", END)

        self.graph = graph_builder.compile(checkpointer=self.memory)

    async def run_superstep(self, message, _history):
        config = {"configurable": {"thread_id": self.agent_id}}
        state = {
            "messages": [HumanMessage(content=message)],
        }
        result = await self.graph.ainvoke(state, config=config)
        print(result["messages"][-1].content)
        return result
