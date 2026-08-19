"""Use this as a tempalte to create subagents for a specific purpose which could be accomplished
without the use of any tool but it can not be done by orchestrator 
exp: Blog writing,
     preparing notes ,
     erc. """



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
from googleapiclient.errors import HttpError


#Tools import
import agent
from src.tools.tavily import Internet_search

from src.state import State
from src.tools.Gmail import gmail_tools

load_dotenv(override=True)


def llm ():
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise RuntimeError("api_key not found")
    return ChatOpenAI(
        api_key= api_key,
        base_url = 'https://api.deepseek.com',
        model = 'deepseek-v4-flash'
    )


def setup(self,name:str,prompt:str):
    self.agent=llm
    self.memory = InMemorySaver()
    self.prompt = prompt

def specialagent(self,state:State,prompt:str):
    system_message =prompt

    found_system_message = False
    messages = state["messages"]

    for message in messages:
        if isinstance(message,SystemMessage):
            message.content = system_message
            found_system_message = True
    if not found_system_message:
        messages = [SystemMessage(content=system_message)]+messages
    response = self.agent.llm.invoke(messages)
    return{
        "messages":[response]
    }

def specialagentrouter(self,state:State):
    last_message = state["messages"][-1].content
    if getattr (last_message,"tool_calls",None):
        return "tools"
    return END
