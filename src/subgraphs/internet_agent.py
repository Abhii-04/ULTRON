from email import message
import os 
from dotenv import load_dotenv
from typing import Literal,Annotated,Any,Optional, Dict, TypedDict,List
import asyncio
from datetime import datetime
import uuid
from langchain_core import messages
from langgraph.runtime import Runtime
from langgraph.types import Checkpointer
from pydantic import BaseModel, Field


#Langgraph imports
from langgraph import graph
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver


#Langchain imports
import langchain
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic.v1 import tools


#Tools import
from src.tools.tavily import Internet_search

from src.state import State

load_dotenv(override=True)


def handle_tool_error(error: Exception) -> str:
    """Return tool failures to the model instead of crashing the CLI."""
    return f"Tool call failed: {type(error).__name__}: {error}"

def llm():
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise RuntimeError("api_key not found")
    return ChatOpenAI(
        api_key=api_key,
        model='deepseek-v4-flash',
        base_url='https://api.deepseek.com'
)



class InternetAgent:
    """
    Use for:
    - Internet search
    - Web research
    - Current or recent information
    - Source-backed answers

    Do NOT use for:
    - Gmail or email tasks
    - LinkedIn MCP tasks
    - Browser interaction
    - File editing
    - Shell commands
    
    """
    def __init__(self):
        self.internet_llm=None
        self.tools=None
        self.agent_id=None
        self.memory = None
        self.graph=None


    def setup(self):
        self.tools = [
            Internet_search,
            ]
        self.memory=InMemorySaver()

    async def setup_tools(self):
        self.tools = [
            Internet_search,
        ]
        internet_llm = llm()
        self.internet_llm = internet_llm.bind_tools(self.tools)

    async def close(self):
        return None

    def internet_agent(self,state:State):
        system_message =f"""You are an internet research agent.

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

The current date and time is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. """

        if state.get("feedback_on_work"):
            system_message += f"""
    Previously you thought you completed the assignment, but your reply was rejected because the success criteria was not met.
    Here is the feedback on why this was rejected:
    {state["feedback_on_work"]}
    With this feedback, please continue the assignment, ensuring that you meet the success criteria or have a question for the user."""

        found_system_message = False
        messages = state["messages"]

        for message in messages:
            
            if isinstance(message,SystemMessage):
                message.content = system_message
                found_system_message=True

        if not found_system_message:
            messages = [SystemMessage(content=system_message)]+messages

        response = self.internet_llm.invoke(messages)
        return{
            "messages":[response]
        }

    def internet_agent_router(self,state:State):
        last_message=state["messages"][-1]

        if getattr(last_message,"tool_calls",None):
            return "tools"
        return END
    
    def format_conversation(self,messages:List[Any])->str:
        conversation = "Conversation history: \n\n"
        
        for message in messages:
            
            if isinstance(message,HumanMessage):
                conversation += f"User: {message.content}\n"
            elif isinstance(message,AIMessage):
                text  = message.content or "[Tools use]"
                conversation += f"Assistant: {text}\n"
        return conversation
    
    
    # def stoponloop(self, state: State):
    #     LOOP_TOOLS = ["snapshot"]

    #     tool_messages = [
    #         m for m in state.get("messages", [])
    #         if isinstance(m, ToolMessage)
    #     ]

    #     if not tool_messages:
    #         return {"stop": False}

    #     current_tool = tool_messages[-1].name

    #     # Only monitor tools in LOOP_TOOLS
    #     if current_tool not in LOOP_TOOLS:
    #         return {"stop": False}

    #     # Check whether this tool appeared previously
    #     previous_tools = [m.name for m in tool_messages[:-1]]

    #     if current_tool in previous_tools:
    #         return {
    #             "stop": True,
    #             "messages": [
    #                 ToolMessage(
    #                     content="Blocked repetitive tool call",
    #                     name=current_tool,
    #                     tool_call_id=tool_messages[-1].tool_call_id,
    #                 )
    #             ],
    #         }

    #     return {"stop": False}
    
    async def build_graph(self):
        await self.setup_tools()
        graph_builder = StateGraph(State)

        # Nodes
        graph_builder.add_node("internet_agent", self.internet_agent)
        graph_builder.add_node("tools", ToolNode(self.tools, handle_tool_errors=handle_tool_error))
        # graph_builder.add_node("stoponloop", self.stoponloop)

        # Edges
        graph_builder.add_edge(START, "internet_agent")

        graph_builder.add_conditional_edges(
            "internet_agent",
            self.internet_agent_router,
            {
                "tools": "tools",
                END: END,
            },
        )
        graph_builder.add_edge("tools", "internet_agent")

        self.graph = graph_builder.compile(
            checkpointer=self.memory
        )
    async def run_superstep(self,message,history):
        config = {"configurable":{"thread_id":self.agent_id}}

        state = {
            "messages":[HumanMessage(content=message)],

        }
        result = await self.graph.ainvoke(state, config=config)

        print(result["messages"][-1].content)
        return result
