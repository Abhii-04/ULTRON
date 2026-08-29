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
from src.subgraphs.gmail_agent import Gmail_agent
from src.subgraphs.internet_agent import InternetAgent
from src.subgraphs.linkedin_agent import LinkedinAgent

#Tools imports
from src.tools.fileManagment import create_file, delete_file, read_file, write_file


#Nodes imports
from src.nodes.dynamic_prompt import prompt_modifier
from src.nodes.dynamic_agent_selection import dynamic_agent_selection
from src.middlewares.context_handoff import create_task_instructions_handoff_tool
from src.middlewares.HITL import add_approval_to_risky_tools, ask_question, halt_on_risky_tools

from src.memory import memory

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
                description="Transfer current, recent, web search, URL, or source-backed research tasks to the internet agent.",
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
        user_text = messages[-1].content

        try:
            #retrieve relevant memories
            memories = memory.search(user_text , filters = {"user_id":user_id},top_k=5)

            #handle dict response format
            memory_list = memories.get("results",[])
        except Exception as e:
            print(f"Error retrieving memory: {type(e).__name__}:{e}")
            memory_list=[]

        memory_context = "\n".join(
            f"-{item['memory']}"
            for item in memory_list
            if item.get("memory")
        )
        system_message = SystemMessage(
            content = (
                f"{prompt_modifier(state)}\n\n"
                f"Relevant long term user memories: \n{memory_context}"
            )
        )

        response = self.orchestrator_agent.invoke([system_message, *messages])

        if getattr(response, "tool_calls", None):
            return {"messages": [response], "next": "orchestrator_tools"}

        if isinstance(messages[-1], ToolMessage):
            return {"messages": [response], "next": END}

        try:
            interaction=[
                {"role":"user","content":user_text},
                {"role":"assistant","content":response.content},
            ]

            result = memory.add(interaction,user_id = user_id)
            print(f"memory saved:{len(result.get('results',[]))} memories added")
        except Exception as e:
            print(f"Error saving memory: {type(e).__name__}:{e}")
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
            "agent",
            self.orchestrator_router,
            {
                "gmail": "gmail",
                "linkedin": "linkedin",
                "internet": "internet",
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
