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
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic.v1 import tools


#Tools imports
from agent import State
from src.tools.tavily import Internet_search
from src.tools.bash import bash
from src.tools.playwright import open_browser,click,Press,run_headed_browser,Snapshot,goforward,reload,scroll,save_storage_state,type


load_dotenv(override=True)

def llm():
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise RuntimeError("api_key not found")
    return ChatOpenAI(
        api_key=api_key,
        model='deekseek-v4-flash',
        base_url='https://api.deepseek.com'
    )

class SubgraphState(TypedDict):
    messages : Annotated[List[Any],add_messages]
    user_input_needed:bool
    next:str

class BrowserAgent:
    """
    Use for:
    - Opening websites
    - Clicking buttons and links
    - Filling forms
    - Browser navigation
    - Playwright automation

    Do NOT use for:
    - Internet research
    - Code generation
    - File editing
    """
    def __init__(self):
        self.browser_llm=None
        self.tools=None
        self.agent_id=None
        self.memory = None
        self.graph=None


    def setup(self,state:State):
        self.tools = [Internet_search,open_browser,click, Press,run_headed_browser,Snapshot,goforward,reload,scroll,save_storage_state,type,]
        browser_llm = llm()
        self.browser_llm = browser_llm.bind_tools(self.tools)
        self.memory=InMemorySaver()

    def browser_agent(self,state:State):
        system_message =f"""You are a Browser Agent responsible for interacting with websites using browser tools.

Your responsibilities:
- Open and navigate websites.
- Click buttons, links, and UI elements.
- Type into input fields.
- Scroll pages when content is not visible.
- Reload pages if needed.
- Save browser state when requested.
- Take snapshots when visual inspection is needed.

Rules:
- Use browser tools instead of describing what should be done.
- Open a page before interacting with it.
- If an element is not visible, scroll before trying again.
- If a page fails to load, try reloading once.
- If navigation changes the page, continue working on the new page.
- Take a snapshot whenever you need to inspect the current page.
- Do not guess element names—use snapshots or the page state to identify them.
- If a required action cannot be completed after reasonable attempts, explain the blocker instead of looping forever.
- Stop only when:
  - the requested browser task is complete, or
  - you require clarification from the user, or
  - progress is impossible.

Available tools:
- open_browser(url)
- click(button_name)
- type(text)
- scroll(dx, dy)
- Press(key)
- reload()
- goforward()
- snapshot(filename)
- save_storage_state(filename)
- run_headed_browser(url) """

        found_system_message = False
        messages = state["messages"]

        for message in messages:
            if isinstance(message,SystemMessage):
                message.content = system_message
                found_system_message=True
            if not found_system_message:
                message = [SystemMessage(content=system_message)]+messages

        response = self.browser_llm.invoke(messages)
        return{
            "messages":[response]
        }

    def browser_agent_router(self,state:State):
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
    
    
    async def build_graph(self):
        graph_builder = StateGraph(SubgraphState)

        graph_builder.add_node("browser_llm",self.browser_llm)
        graph_builder.add_node("tools",self.tools)


        #Edges
        graph_builder.add_edge(START,"browser_llm")
        graph_builder.add_conditional_edges(
            "browser_llm",
            self.browser_agent_router,
            {
                "tools":"tools",
                END : END
            }
        ) 
        graph_builder.add_edge("tools", "browser_llm")

        self.graph = graph_builder.compile(checkpointer= self.memory)

    async def run_superstep(self,message,history):
        config = {"configurable":{"thread_id":self.agent_id}}

        state = {
            "messages":[HumanMessage(content=message)],

        }
        result = await self.graph.ainvoke(state, config=config)

        print(result["messages"][-1].content)
        return result