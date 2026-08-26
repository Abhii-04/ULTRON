import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from src.state import State

#Agents imports 
from src.subgraphs.assistant import Assistant
from src.subgraphs.gmail_agent import Gmail_agent
from src.subgraphs.internet_agent import InternetAgent
from src.subgraphs.linkedin_agent import LinkedinAgent

#Tools imports
from src.tools.fileManagment import create_file, delete_file, read_file, write_file


#Nodes imports 
from src.nodes.dynamic_prompt import prompt_modifier
from src.nodes.dynamic_agent_selection import dynamic_agent_selection
from src.nodes.context_handoff import create_task_instructions_handoff_tool
from src.nodes.HITL import add_approval_to_risky_tools, ask_question, halt_on_risky_tools

load_dotenv(override=True)

llm = ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
)

def handle_file_tool_error(error: Exception) -> str:
    """Return file tool failures to the model instead of crashing the graph."""
    return f"File tool call failed: {type(error).__name__}: {error}"

class Agent:
    def __init__(self):
        self.internet_graph = None
        self.assistant_graph = None
        self.gmail_graph = None
        self.linkedin_graph = None
        self.graph = None
        self.agent_id = None
        self.checkpointer = None
        self.store = None
        self.internet_agent = None
        self.assistant_agent = None
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
                description="Transfer current, recent, web search, URL, or source-backed research tasks to the internet agent.",
            ),
            create_task_instructions_handoff_tool(
                agent_name="assistant",
                description="Transfer general reasoning, writing, planning, explanation, or summarization tasks to the assistant agent.",
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

        assistant = Assistant()
        assistant.setup()
        await assistant.build_graph()
        self.assistant_graph = assistant.graph
        self.assistant_agent = assistant

        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()
        await self.build_graph()

    def get_user_profile(self, store: BaseStore, user_id: str) -> dict[str, Any]:
        memory = store.get(("user", user_id), "profile")
        return memory.value if memory else {}

    def update_user_profile(self, user_id: str, profile: dict[str, Any]) -> None:
        if self.store is None:
            raise RuntimeError("Memory store has not been initialized. Call setup() first.")

        self.store.put(("user", user_id), "profile", profile)

    def orchestrator(self, state: State, store: BaseStore) -> dict[str, Any]:
        user_id = state.get("user_id", "default")
        profile = self.get_user_profile(store, user_id)
        #system_message
        system_message = SystemMessage(
            content= prompt_modifier(state)
        )
        response = self.orchestrator_agent.invoke([system_message] + state["messages"])

        if getattr(response, "tool_calls", None):
            return {"messages": [response], "next": "orchestrator_tools"}

        if isinstance(state["messages"][-1], ToolMessage):
            return {"messages": [response], "next": END}

        route = response.content.strip().lower()

        if route not in ("gmail", "linkedin", "internet", "assistant"):
            route = "assistant"

        return {"next": route}

    def orchestrator_router(self, state: State):
        route = state.get("next")
        if route == "orchestrator_tools":
            return route
        if route in {"gmail", "linkedin", "internet", "assistant"}:
            return route
        return END

    def sanitize_final_content(self, content: Any) -> Any:
        if isinstance(content, str) and "DSML" in content and "tool_calls" in content:
            return (
                "The model produced raw tool-call markup instead of a structured "
                "tool call, so no tool was executed. Re-run the request; if it "
                "keeps happening, the model/provider is not returning tool calls "
                "through the expected structured interface."
            )

        return content

    async def build_graph(self):
        missing_graphs = [
            name
            for name, graph in (
                ("Internet", self.internet_graph),
                ("Assistant", self.assistant_graph),
                ("Gmail", self.gmail_graph),
                ("LinkedIn", self.linkedin_graph),
            )
            if graph is None
        ]
        if missing_graphs:
            raise RuntimeError(
                f"{', '.join(missing_graphs)} graph has not been initialized. "
                "Call setup() before build_graph()."
            )

        graph_builder = StateGraph(State)
        # graph_builder.add_node("dynamic_agent_selection", dynamic_agent_selection)
        graph_builder.add_node("agent", self.orchestrator)
        graph_builder.add_node("toolcall", halt_on_risky_tools)
        graph_builder.add_node(
            "orchestrator_tools",
            ToolNode(self.file_tools + self.handoff_tools, handle_tool_errors=handle_file_tool_error),
        )
        graph_builder.add_node("internet", self.internet_graph)
        graph_builder.add_node("gmail", self.gmail_graph)
        graph_builder.add_node("linkedin", self.linkedin_graph)
        graph_builder.add_node("assistant", self.assistant_graph)


        graph_builder.add_conditional_edges(
            START,
            dynamic_agent_selection,
            {
                "linkedin": "linkedin",
                "internet": "internet",
                "orchestrator": "agent",
            }
        )
        # graph_builder.add_edge("dynamic_agent_selection", "agent")
        graph_builder.add_conditional_edges(
            "agent",
            self.orchestrator_router,
            {
                "gmail": "gmail",
                "linkedin": "linkedin",
                "internet": "internet",
                "assistant": "assistant",
                "orchestrator_tools": "toolcall",
                END: END,
            },
        )
        graph_builder.add_conditional_edges(
            "toolcall",
            lambda state: "orchestrator_tools" if state.get("hitl_decision") == "approved" else END,
            {
                "orchestrator_tools": "orchestrator_tools",
                END: END,
            },
        )
        graph_builder.add_edge("orchestrator_tools", "agent")
        graph_builder.add_edge("internet", END)
        graph_builder.add_edge("gmail", END)
        graph_builder.add_edge("linkedin", END)
        graph_builder.add_edge("assistant", END)

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

        final_message = result["messages"][-1]
        final_message.content = self.sanitize_final_content(final_message.content)

        if emit_output:
            print(final_message.content)
        return result
